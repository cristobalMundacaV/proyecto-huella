"""`repair_legacy_onboarding_state` — structural onboarding repair for
tenants with real obras but no AreaOperacional/CapacidadOrganizacion rows
(e.g. a legacy/demo tenant seeded without the onboarding wizard)."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.analytics.models import Obra, Organizacion
from apps.analytics.models.legacy import AreaOperacional, CapacidadOrganizacion
from apps.analytics.services.onboarding import FLOW_CATALOG


def run_repair(**options):
    out = StringIO()
    call_command("repair_legacy_onboarding_state", stdout=out, **options)
    return out.getvalue()


class RepairLegacyOnboardingStateTests(TestCase):
    def test_a_tenant_with_zero_obras_is_left_untouched(self):
        empty = Organizacion.objects.create(nombre="Tenant nuevo", preset="construccion")
        run_repair()
        self.assertFalse(empty.areas_operacionales.exists())
        self.assertFalse(empty.capacidades_ambientales.exists())

    def test_a_tenant_with_obras_but_no_structure_gets_repaired(self):
        org = Organizacion.objects.create(nombre="Constructora legacy", preset="construccion", onboarding_completado=True, onboarding_step=4)
        Obra.objects.create(organizacion=org, nombre="Obra 1", fecha_inicio=date(2026, 1, 1))

        self.assertFalse(org.areas_operacionales.exists())
        self.assertFalse(org.capacidades_ambientales.exists())

        run_repair()
        org.refresh_from_db()

        self.assertTrue(org.areas_operacionales.filter(activa=True).exists())
        self.assertTrue(org.capacidades_ambientales.exists())
        # every catalog flow key must now have a row, and none of them was
        # guessed as "aplica" — only a human decision (or real detected
        # activity in a future iteration) should set that.
        self.assertEqual(
            set(org.capacidades_ambientales.values_list("capacidad__clave", flat=True)),
            set(FLOW_CATALOG),
        )
        self.assertTrue(
            org.capacidades_ambientales.exclude(estado=CapacidadOrganizacion.Estado.PENDIENTE_DIAGNOSTICO).count() == 0
        )
        self.assertIn("reparacion_legacy", org.onboarding_data)
        # the wizard flag is never touched by this repair
        self.assertTrue(org.onboarding_completado)
        self.assertEqual(org.onboarding_step, 4)

    def test_a_tenant_already_fully_structured_is_not_modified(self):
        org = Organizacion.objects.create(nombre="Constructora completa", preset="construccion")
        Obra.objects.create(organizacion=org, nombre="Obra 1", fecha_inicio=date(2026, 1, 1))
        AreaOperacional.objects.create(organizacion=org, nombre="Bodega", tipo="bodega", activa=True)
        catalog_key = next(iter(FLOW_CATALOG))
        from apps.analytics.services.onboarding import ensure_flow_catalog
        capacidad = ensure_flow_catalog()[catalog_key]
        CapacidadOrganizacion.objects.create(organizacion=org, capacidad=capacidad, estado=CapacidadOrganizacion.Estado.APLICA)

        run_repair()
        org.refresh_from_db()

        self.assertEqual(org.areas_operacionales.count(), 1)
        self.assertEqual(org.capacidades_ambientales.count(), 1)
        self.assertEqual(org.capacidades_ambientales.first().estado, CapacidadOrganizacion.Estado.APLICA)
        self.assertNotIn("reparacion_legacy", org.onboarding_data or {})

    def test_is_idempotent(self):
        org = Organizacion.objects.create(nombre="Constructora idempotente", preset="construccion")
        Obra.objects.create(organizacion=org, nombre="Obra 1", fecha_inicio=date(2026, 1, 1))

        run_repair()
        first_areas = set(org.areas_operacionales.values_list("id", flat=True))
        first_capacidades = set(org.capacidades_ambientales.values_list("id", flat=True))

        run_repair()
        org.refresh_from_db()
        second_areas = set(org.areas_operacionales.values_list("id", flat=True))
        second_capacidades = set(org.capacidades_ambientales.values_list("id", flat=True))

        self.assertEqual(first_areas, second_areas)
        self.assertEqual(first_capacidades, second_capacidades)

    def test_organizacion_id_filter_targets_only_that_tenant(self):
        org_a = Organizacion.objects.create(nombre="Tenant A", preset="construccion")
        org_b = Organizacion.objects.create(nombre="Tenant B", preset="construccion")
        Obra.objects.create(organizacion=org_a, nombre="Obra A", fecha_inicio=date(2026, 1, 1))
        Obra.objects.create(organizacion=org_b, nombre="Obra B", fecha_inicio=date(2026, 1, 1))

        run_repair(organizacion_id=org_a.organizacion_id)

        self.assertTrue(org_a.capacidades_ambientales.exists())
        self.assertFalse(org_b.capacidades_ambientales.exists())

    def test_dry_run_never_persists_changes(self):
        org = Organizacion.objects.create(nombre="Constructora dry-run", preset="construccion")
        Obra.objects.create(organizacion=org, nombre="Obra 1", fecha_inicio=date(2026, 1, 1))

        output = run_repair(dry_run=True)

        self.assertFalse(org.areas_operacionales.exists())
        self.assertFalse(org.capacidades_ambientales.exists())
        self.assertIn("dry-run", output)
