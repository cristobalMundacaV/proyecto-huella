from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import (ActividadOperacional, EventoMaterial, FactorAmbiental,
                     FuenteDatos, MaterialOperacional, Obra, Observacion,
                     Organizacion, UsuarioOrganizacion, VersionFactorAmbiental)
from .services.material_factor_mapping import (approve_material_mapping,
                                                propose_material_mapping)
from .services.material_inventory import (material_coverage_detail,
                                           material_environmental_coverage,
                                           reception_coverage)

User = get_user_model()


class MaterialInventoryTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Cobertura material")
        self.other_org = Organizacion.objects.create(nombre="Cobertura otro tenant")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="manual")
        self.user = User.objects.create_superuser("cobertura-admin", "cobertura-admin@example.com", "password")
        self.sequence = 0

    def material(self, categoria="cemento", unidad_base="kg"):
        self.sequence += 1
        return MaterialOperacional.objects.create(
            organizacion=self.org, codigo=f"MAT-{self.sequence}", nombre=f"Material {self.sequence}",
            categoria=categoria, unidad_base=unidad_base,
        )

    def event(self, material, *, tipo="recepcion", amount=None, unit="kg", when=None):
        self.sequence += 1
        when = when or timezone.make_aware(datetime(2026, 6, 1, 10))
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo=f"ACT-{self.sequence}",
            nombre=tipo, tipo="movimiento_material", timestamp_inicio=when,
        )
        observation = None
        if amount is not None:
            observation = Observacion.objects.create(
                organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
                valor_numerico=Decimal(amount), unidad=unit, timestamp_observacion=when,
                estado=Observacion.Estado.VALIDADA,
            )
        return EventoMaterial.objects.create(
            organizacion=self.org, material=material, actividad=activity, obra=self.work,
            tipo=tipo, fecha_hora=when, observacion_cantidad=observation, fuente=self.source,
        )

    def factor(self, *, unit="kg", value="0.2", estado=VersionFactorAmbiental.Estado.ACTIVO, vigencia_desde=date(2026, 1, 1), vigencia_hasta=None, organization=None):
        self.sequence += 1
        factor = FactorAmbiental.objects.create(
            organizacion=organization, codigo=f"factor-{self.sequence}", nombre=f"Factor {self.sequence}",
            categoria="materiales", unidad_entrada=unit, unidad_resultado="kgCO2e",
        )
        return VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal(value), fuente="Fixture", estado=estado,
            vigencia_desde=vigencia_desde, vigencia_hasta=vigencia_hasta,
        )

    def approved_mapping(self, material, factor, vigencia_desde=date(2026, 1, 1), vigencia_hasta=None):
        mapping = propose_material_mapping(self.org, material, factor, vigencia_desde, vigencia_hasta, self.user)
        return approve_material_mapping(mapping.pk, self.org, self.user)

    def test_reception_without_observation_is_observacion_faltante(self):
        material = self.material()
        event = self.event(material, amount=None)
        diag = reception_coverage(event)
        self.assertFalse(diag["observacion_presente"])
        self.assertEqual(diag["razones"], ["observacion_faltante"])
        self.assertFalse(diag["calculable"])

    def test_reception_without_mapping_is_sin_mapping(self):
        material = self.material()
        event = self.event(material, amount="10")
        diag = reception_coverage(event)
        self.assertFalse(diag["mapeado"])
        self.assertIn("sin_mapping", diag["razones"])
        self.assertFalse(diag["calculable"])

    def test_mapping_proposed_not_approved_is_mapping_no_aprobado(self):
        material = self.material()
        factor_version = self.factor()
        propose_material_mapping(self.org, material, factor_version.factor, date(2026, 1, 1), None, self.user)
        event = self.event(material, amount="10")
        diag = reception_coverage(event)
        self.assertTrue(diag["mapeado"])
        self.assertFalse(diag["mapping_aprobado_vigente"])
        self.assertIn("mapping_no_aprobado", diag["razones"])

    def test_mapping_approved_outside_validity_is_mapping_fuera_vigencia(self):
        material = self.material()
        factor_version = self.factor()
        self.approved_mapping(material, factor_version.factor, date(2025, 1, 1), date(2025, 12, 31))
        event = self.event(material, amount="10")
        diag = reception_coverage(event)
        self.assertIn("mapping_fuera_vigencia", diag["razones"])

    def test_factor_only_draft_is_sin_version_factor_activa(self):
        material = self.material()
        factor_version = self.factor(estado=VersionFactorAmbiental.Estado.BORRADOR)
        self.approved_mapping(material, factor_version.factor)
        event = self.event(material, amount="10")
        diag = reception_coverage(event)
        self.assertTrue(diag["mapping_aprobado_vigente"])
        self.assertFalse(diag["factor_activo"])
        self.assertIn("sin_version_factor_activa", diag["razones"])

    def test_factor_active_but_expired_is_factor_fuera_vigencia(self):
        material = self.material()
        factor_version = self.factor(vigencia_desde=date(2020, 1, 1), vigencia_hasta=date(2020, 12, 31))
        self.approved_mapping(material, factor_version.factor)
        event = self.event(material, amount="10")
        diag = reception_coverage(event)
        self.assertIn("factor_fuera_vigencia", diag["razones"])

    def test_unit_incompatible(self):
        material = self.material()
        factor_version = self.factor(unit="m3")
        self.approved_mapping(material, factor_version.factor)
        event = self.event(material, amount="10", unit="kg")
        diag = reception_coverage(event)
        self.assertTrue(diag["factor_activo"])
        self.assertFalse(diag["unidad_compatible"])
        self.assertIn("unidad_incompatible", diag["razones"])

    def test_fully_calculable_reception(self):
        material = self.material()
        factor_version = self.factor()
        self.approved_mapping(material, factor_version.factor)
        event = self.event(material, amount="10")
        diag = reception_coverage(event)
        self.assertTrue(diag["calculable"])
        self.assertEqual(diag["razones"], [])
        self.assertFalse(diag["calculado"])

    def test_calculated_reception_flagged(self):
        from .services.calculation_v2 import calculate_activity
        from .services.system_environmental_catalog import ensure_system_environmental_catalog

        ensure_system_environmental_catalog()
        material = self.material()
        factor_version = self.factor(organization=self.org)
        self.approved_mapping(material, factor_version.factor)
        event = self.event(material, amount="10")
        calculate_activity(event.actividad)
        diag = reception_coverage(event)
        self.assertTrue(diag["calculado"])
        self.assertTrue(diag["calculable"])

    def test_non_reception_events_not_included_in_summary(self):
        material = self.material()
        factor_version = self.factor()
        self.approved_mapping(material, factor_version.factor)
        self.event(material, tipo="recepcion", amount="10")
        self.event(material, tipo="uso", amount="5")
        summary = material_environmental_coverage(self.org)
        self.assertEqual(summary["recepciones_totales"], 1)

    def test_mass_only_coverage_combines_kg_and_t(self):
        material = self.material()
        factor_version = self.factor()
        self.approved_mapping(material, factor_version.factor)
        self.event(material, amount="10", unit="kg")
        self.event(material, amount="1", unit="t")
        summary = material_environmental_coverage(self.org)
        self.assertEqual(summary["cantidades_por_dimension"]["masa"]["total"], Decimal("1010"))
        self.assertEqual(summary["cantidades_por_dimension"]["masa"]["unidad"], "kg")
        self.assertEqual(summary["cantidades_por_dimension"]["masa"]["recepciones"], 2)
        self.assertNotIn("volumen", summary["cantidades_por_dimension"])

    def test_volume_only_coverage(self):
        material = self.material(unidad_base="m3")
        factor_version = self.factor(unit="m3")
        self.approved_mapping(material, factor_version.factor)
        self.event(material, amount="3", unit="m3")
        summary = material_environmental_coverage(self.org)
        self.assertEqual(summary["cantidades_por_dimension"]["volumen"]["total"], Decimal("3"))
        self.assertNotIn("masa", summary["cantidades_por_dimension"])

    def test_mixed_units_never_summed_across_dimensions(self):
        material_kg = self.material()
        material_m3 = self.material(unidad_base="m3")
        factor_kg = self.factor()
        factor_m3 = self.factor(unit="m3")
        self.approved_mapping(material_kg, factor_kg.factor)
        self.approved_mapping(material_m3, factor_m3.factor)
        self.event(material_kg, amount="100", unit="kg")
        self.event(material_m3, amount="5", unit="m3")
        summary = material_environmental_coverage(self.org)
        self.assertEqual(summary["cantidades_por_dimension"]["masa"]["total"], Decimal("100"))
        self.assertEqual(summary["cantidades_por_dimension"]["volumen"]["total"], Decimal("5"))
        total_keys = set(summary["cantidades_por_dimension"])
        self.assertEqual(total_keys, {"masa", "volumen"})

    def test_unmapped_and_mapped_materials_counted_separately(self):
        mapped_material = self.material()
        unmapped_material = self.material()
        factor_version = self.factor()
        self.approved_mapping(mapped_material, factor_version.factor)
        self.event(mapped_material, amount="10")
        self.event(unmapped_material, amount="10")
        summary = material_environmental_coverage(self.org)
        self.assertEqual(summary["materiales_totales"], 2)
        self.assertEqual(summary["materiales_mapeados"], 1)
        self.assertEqual(summary["materiales_sin_mapping"], 1)

    def test_calculable_and_no_calculable_counts_and_reasons(self):
        calculable_material = self.material()
        blocked_material = self.material()
        factor_version = self.factor()
        self.approved_mapping(calculable_material, factor_version.factor)
        self.event(calculable_material, amount="10")
        self.event(blocked_material, amount="10")
        summary = material_environmental_coverage(self.org)
        self.assertEqual(summary["recepciones_calculables"], 1)
        self.assertEqual(summary["recepciones_no_calculables"], 1)
        self.assertEqual(summary["razones_no_calculable"], {"sin_mapping": 1})

    def test_filters_by_work_and_date(self):
        material = self.material()
        factor_version = self.factor()
        self.approved_mapping(material, factor_version.factor)
        early = self.event(material, amount="10", when=timezone.make_aware(datetime(2026, 1, 15, 10)))
        late = self.event(material, amount="10", when=timezone.make_aware(datetime(2026, 8, 15, 10)))
        summary = material_environmental_coverage(self.org, start=date(2026, 6, 1))
        self.assertEqual(summary["recepciones_totales"], 1)

    def test_material_coverage_detail_lists_receptions(self):
        material = self.material()
        factor_version = self.factor()
        self.approved_mapping(material, factor_version.factor)
        self.event(material, amount="10")
        self.event(material, amount="5")
        detail = material_coverage_detail(self.org, material)
        self.assertEqual(len(detail["recepciones"]), 2)

    def test_cross_tenant_material_not_visible(self):
        other_material = MaterialOperacional.objects.create(
            organizacion=self.other_org, codigo="MAT-OTHER", nombre="Otro", categoria="otro", unidad_base="kg",
        )
        detail = material_coverage_detail(self.org, other_material)
        self.assertEqual(detail["recepciones"], [])


class MaterialInventoryApiTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="API cobertura")
        self.other_org = Organizacion.objects.create(nombre="API otro tenant cobertura")
        self.user = User.objects.create_user("cobertura-api-user", password="test-pass")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org)
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="manual")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-API", nombre="Material API", categoria="cemento", unidad_base="kg",
        )
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"

    def test_coverage_summary_endpoint(self):
        response = self.client.get(f"{self.base}/materiales-operacionales/cobertura-ambiental/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("materiales_totales", response.json())

    def test_material_coverage_endpoint(self):
        response = self.client.get(f"{self.base}/materiales-operacionales/{self.material.id}/cobertura-ambiental/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["material_id"], self.material.id)

    def test_material_coverage_endpoint_cross_tenant_404(self):
        other_org = Organizacion.objects.create(nombre="Cobertura API cruzada")
        other_user = User.objects.create_user("cobertura-api-other", password="test-pass")
        UsuarioOrganizacion.objects.create(user=other_user, organizacion=other_org)
        self.client.force_login(other_user)
        other_base = f"/api/organizaciones/{other_org.organizacion_id}"
        response = self.client.get(f"{other_base}/materiales-operacionales/{self.material.id}/cobertura-ambiental/")
        self.assertEqual(response.status_code, 404)

    def test_reception_coverage_endpoint(self):
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo="ACT-COV", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=timezone.now(),
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal("10"), unidad="kg", timestamp_observacion=timezone.now(),
            estado=Observacion.Estado.VALIDADA,
        )
        event = EventoMaterial.objects.create(
            organizacion=self.org, material=self.material, actividad=activity, obra=self.work,
            tipo="recepcion", fecha_hora=timezone.now(), observacion_cantidad=observation, fuente=self.source,
        )
        response = self.client.get(f"{self.base}/eventos-materiales/{event.id}/cobertura-ambiental/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["evento_id"], event.id)
