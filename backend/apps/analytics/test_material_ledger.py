from datetime import date, datetime
from decimal import Decimal
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.knowledge import test_okobaudat_detail as detail_tests

from .models import (ActividadOperacional, EventoMaterial, FactorAmbiental,
                     FuenteDatos, MaterialOperacional, Obra, Observacion,
                     Organizacion, UsuarioOrganizacion, VersionFactorAmbiental)
from .services.calculation_v2 import calculate_activity, recalculate
from .services.material_factor_mapping import (approve_material_mapping,
                                                propose_material_mapping)
from .services.material_ledger import (current_calculation_for_activity,
                                       ledger_entries, ledger_entry_provenance,
                                       material_ledger_totals)
from .services.system_environmental_catalog import ensure_system_environmental_catalog

User = get_user_model()


class MaterialLedgerTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.org = Organizacion.objects.create(nombre="Ledger material")
        self.other_org = Organizacion.objects.create(nombre="Ledger otro tenant")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="manual")
        self.user = User.objects.create_superuser("ledger-admin", "ledger-admin@example.com", "password")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-LEDGER", nombre="Cemento Ledger", categoria="cemento", unidad_base="kg",
        )
        self.at = timezone.make_aware(datetime(2026, 9, 11, 10))
        self.sequence = 0

    def factor(self, *, value="0.847351015163189", unit="kg"):
        self.sequence += 1
        factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo=f"factor-ledger-{self.sequence}", nombre="Factor",
            categoria="materiales", unidad_entrada=unit, unidad_resultado="kgCO2e",
        )
        return VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal(value), fuente="Fixture",
            estado=VersionFactorAmbiental.Estado.ACTIVO, vigencia_desde=date(2026, 1, 1),
        )

    def map_material(self, factor_version, material=None):
        mapping = propose_material_mapping(
            self.org, material or self.material, factor_version.factor, date(2026, 1, 1), None, self.user,
        )
        return approve_material_mapping(mapping.pk, self.org, self.user)

    def reception(self, *, amount="10000", unit="kg", material=None, when=None):
        self.sequence += 1
        material = material or self.material
        when = when or self.at
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo=f"ACT-LEDGER-{self.sequence}",
            nombre="recepcion", tipo="movimiento_material", timestamp_inicio=when,
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal(amount), unidad=unit, timestamp_observacion=when,
            estado=Observacion.Estado.VALIDADA,
        )
        return EventoMaterial.objects.create(
            organizacion=self.org, material=material, actividad=activity, obra=self.work,
            tipo="recepcion", fecha_hora=when, observacion_cantidad=observation, fuente=self.source,
        )

    def test_single_reception_ledger_total(self):
        factor_version = self.factor()
        self.map_material(factor_version)
        event = self.reception()
        calculation, _ = calculate_activity(event.actividad)
        persisted = calculation.__class__.objects.get(pk=calculation.pk)
        totals = material_ledger_totals(self.org)
        self.assertEqual(totals["entradas_totales"], 1)
        self.assertEqual(totals["totales_por_unidad"]["kgCO2e"]["total"], persisted.resultado)

    def test_multiple_receptions_sum_correctly(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        for _ in range(3):
            calculate_activity(self.reception(amount="1000").actividad)
        totals = material_ledger_totals(self.org)
        self.assertEqual(totals["entradas_totales"], 3)
        self.assertEqual(totals["totales_por_unidad"]["kgCO2e"]["total"], Decimal("600"))

    def test_recalculation_does_not_double_count(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        event = self.reception(amount="1000")
        calculation, _ = calculate_activity(event.actividad)
        recalculated = recalculate(calculation, "correccion de cantidad")[0]
        totals = material_ledger_totals(self.org)
        self.assertEqual(totals["entradas_totales"], 1)
        self.assertEqual(totals["totales_por_unidad"]["kgCO2e"]["total"], Decimal("200"))
        current = current_calculation_for_activity(event.actividad)
        self.assertEqual(current.pk, recalculated.pk)

    def test_superseded_calculation_excluded_from_totals_but_visible_in_history(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        event = self.reception(amount="1000")
        original, _ = calculate_activity(event.actividad)
        recalculate(original, "correccion")
        entries_current = list(ledger_entries(self.org))
        entries_all = list(ledger_entries(self.org, include_superseded=True))
        self.assertEqual(len(entries_current), 1)
        self.assertEqual(len(entries_all), 2)
        self.assertNotIn(original.pk, [e.pk for e in entries_current])
        self.assertIn(original.pk, [e.pk for e in entries_all])

    def test_idempotent_totals_computation(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        calculate_activity(self.reception(amount="1000").actividad)
        first = material_ledger_totals(self.org)
        second = material_ledger_totals(self.org)
        self.assertEqual(first, second)

    def test_negative_factor_preserves_sign_in_ledger(self):
        factor_version = self.factor(value="-647.4201396839651", unit="m3")
        self.map_material(factor_version)
        event = self.reception(amount="2", unit="m3")
        calculation, _ = calculate_activity(event.actividad)
        persisted = calculation.__class__.objects.get(pk=calculation.pk)
        self.assertLess(persisted.resultado, 0)
        totals = material_ledger_totals(self.org)
        total = totals["totales_por_unidad"]["kgCO2e"]["total"]
        self.assertLess(total, 0)
        self.assertEqual(total, persisted.resultado)

    def test_tenant_isolation_of_ledger(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        calculate_activity(self.reception(amount="1000").actividad)
        other_totals = material_ledger_totals(self.other_org)
        self.assertEqual(other_totals["entradas_totales"], 0)

    def test_historical_mapping_and_factor_version_are_reconstructible(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        event = self.reception(amount="1000")
        calculation, _ = calculate_activity(event.actividad)
        provenance = ledger_entry_provenance(calculation)
        self.assertEqual(provenance["version_factor_id"], factor_version.id)
        self.assertIsNotNone(provenance["mapping"])
        self.assertEqual(provenance["resultado"], calculation.resultado)
        self.assertIn("quality", provenance)

    def test_aggregation_by_obra_and_categoria(self):
        factor_version = self.factor(value="0.2")
        self.map_material(factor_version)
        calculate_activity(self.reception(amount="1000").actividad)
        totals_by_work = material_ledger_totals(self.org, group_by="obra")
        self.assertIn(self.work.id, totals_by_work["por_grupo"])
        totals_by_category = material_ledger_totals(self.org, group_by="categoria")
        self.assertIn("cemento", totals_by_category["por_grupo"])


class MaterialLedgerConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        ensure_system_environmental_catalog()
        self.org = Organizacion.objects.create(nombre="Ledger concurrencia")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="manual")
        self.user = User.objects.create_superuser("ledger-conc-admin", "ledger-conc-admin@example.com", "password")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-CONC-LEDGER", nombre="Concreto", categoria="concreto", unidad_base="kg",
        )
        factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-conc-ledger", nombre="Factor", categoria="materiales",
            unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.factor_version = VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal("0.2"), fuente="Fixture",
            estado=VersionFactorAmbiental.Estado.ACTIVO, vigencia_desde=date(2026, 1, 1),
        )
        mapping = propose_material_mapping(self.org, self.material, factor, date(2026, 1, 1), None, self.user)
        approve_material_mapping(mapping.pk, self.org, self.user)
        at = timezone.make_aware(datetime(2026, 9, 11, 10))
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo="ACT-CONC-LEDGER", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal("1000"), unidad="kg", timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        self.event = EventoMaterial.objects.create(
            organizacion=self.org, material=self.material, actividad=activity, obra=self.work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=self.source,
        )
        self.calculation, _ = calculate_activity(activity)

    def test_concurrent_recalculation_leaves_exactly_one_current_entry(self):
        barrier = Barrier(2)
        results, errors = [], []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.append(recalculate(self.calculation, "concurrente")[0].pk)
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual(len(results), 1, (results, errors))
        self.assertEqual(len(errors), 1, (results, errors))
        self.assertIsInstance(errors[0], ValidationError)
        current = current_calculation_for_activity(self.event.actividad)
        self.assertEqual(current.pk, results[0])
        totals = material_ledger_totals(self.org)
        self.assertEqual(totals["entradas_totales"], 1)


class MaterialLedgerApiTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.org = Organizacion.objects.create(nombre="Ledger API")
        self.user = User.objects.create_user("ledger-api-user", password="test-pass")
        UsuarioOrganizacion.objects.create(
            user=self.user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="manual")
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-LEDGER-API", nombre="Material", categoria="cemento", unidad_base="kg",
        )
        factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-ledger-api", nombre="Factor", categoria="materiales",
            unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        self.factor_version = VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal("0.2"), fuente="Fixture",
            estado=VersionFactorAmbiental.Estado.ACTIVO, vigencia_desde=date(2026, 1, 1),
        )
        mapping = propose_material_mapping(self.org, self.material, factor, date(2026, 1, 1), None, self.user)
        approve_material_mapping(mapping.pk, self.org, self.user)
        at = timezone.now()
        activity = ActividadOperacional.objects.create(
            organizacion=self.org, obra=self.work, codigo="ACT-LEDGER-API", nombre="recepcion",
            tipo="movimiento_material", timestamp_inicio=at,
        )
        observation = Observacion.objects.create(
            organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material",
            valor_numerico=Decimal("500"), unidad="kg", timestamp_observacion=at,
            estado=Observacion.Estado.VALIDADA,
        )
        EventoMaterial.objects.create(
            organizacion=self.org, material=self.material, actividad=activity, obra=self.work,
            tipo="recepcion", fecha_hora=at, observacion_cantidad=observation, fuente=self.source,
        )
        self.calculation, _ = calculate_activity(activity)
        self.client.force_login(self.user)
        self.base = f"/api/organizaciones/{self.org.organizacion_id}"

    def test_ledger_totals_endpoint(self):
        response = self.client.get(f"{self.base}/materiales-operacionales/ledger-a1a3/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entradas_totales"], 1)

    def test_ledger_entries_endpoint(self):
        response = self.client.get(f"{self.base}/materiales-operacionales/ledger-a1a3/entradas/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_ledger_entry_detail_endpoint(self):
        response = self.client.get(f"{self.base}/materiales-operacionales/ledger-a1a3/{self.calculation.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["calculo_id"], self.calculation.pk)

    def test_ledger_cross_tenant_entry_404(self):
        other_org = Organizacion.objects.create(nombre="Ledger API otro tenant")
        other_user = User.objects.create_user("ledger-api-other", password="test-pass")
        UsuarioOrganizacion.objects.create(user=other_user, organizacion=other_org)
        self.client.force_login(other_user)
        other_base = f"/api/organizaciones/{other_org.organizacion_id}"
        response = self.client.get(f"{other_base}/materiales-operacionales/ledger-a1a3/{self.calculation.pk}/")
        self.assertEqual(response.status_code, 404)
