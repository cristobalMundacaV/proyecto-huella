from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import (ActividadOperacional, EventoMaterial, FactorAmbiental,
                     FuenteDatos, MaterialOperacional, Obra, Observacion,
                     Organizacion, VersionFactorAmbiental)
from .services.calculation_v2 import calculate_activity
from .services.methodology_selector import select_methodology
from .services.system_environmental_catalog import (MATERIAL_METHODOLOGY_CODE,
                                                     ensure_system_environmental_catalog)
from .views_calculation_v2 import _serialize_selection


class MaterialCalculationCatalogTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.org = Organizacion.objects.create(nombre="Material calc")
        self.work = Obra.objects.create(organizacion=self.org, nombre="Obra", fecha_inicio=date(2026, 1, 1))
        self.source = FuenteDatos.objects.create(organizacion=self.org, nombre="Guia", tipo="manual")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="MAT-CEM", nombre="Cemento Portland", categoria="cemento", unidad_base="kg")
        self.at = timezone.make_aware(datetime(2026, 9, 11, 10))
        self.sequence = 0

    def event(self, kind="recepcion", amount="10000", unit="kg"):
        self.sequence += 1
        activity = ActividadOperacional.objects.create(organizacion=self.org, obra=self.work, codigo=f"MAT-{self.sequence}", nombre=kind, tipo="movimiento_material", timestamp_inicio=self.at)
        observation = Observacion.objects.create(organizacion=self.org, actividad=activity, fuente=self.source, concepto="cantidad_material", valor_numerico=Decimal(amount), unidad=unit, timestamp_observacion=self.at, estado=Observacion.Estado.VALIDADA)
        EventoMaterial.objects.create(organizacion=self.org, material=self.material, actividad=activity, obra=self.work, tipo=kind, fecha_hora=self.at, observacion_cantidad=observation, fuente=self.source)
        return activity

    def factor(self, *, organization=None, code="cement-exact", unit="kg", context=None, value="0.2"):
        factor = FactorAmbiental.objects.create(organizacion=organization, codigo=code, nombre=code, categoria="materiales", unidad_entrada=unit, unidad_resultado="kgCO2e", contexto=context or {"material_codigo": self.material.codigo, "especificidad": "producto"})
        return VersionFactorAmbiental.objects.create(factor=factor, version=1, valor=Decimal(value), fuente="Fixture gobernado", referencia="Solo test", estado="activo", vigencia_desde=date(2026, 1, 1), contexto=factor.contexto)

    def test_recepcion_exacta_calcula_y_snapshot_es_trazable(self):
        version = self.factor(organization=self.org)
        activity = self.event()
        calculation, selection = calculate_activity(activity)
        self.assertEqual(selection["seleccion"]["version_metodologia"].metodologia.codigo, MATERIAL_METHODOLOGY_CODE)
        self.assertEqual(calculation.resultado, Decimal("2000"))
        self.assertEqual(calculation.version_factor, version)
        snapshot = calculation.snapshot_tecnico
        self.assertEqual(snapshot["evento_material"]["tipo"], "recepcion")
        self.assertEqual(snapshot["material"]["codigo"], "MAT-CEM")
        self.assertEqual(snapshot["especificidad_factor"], "producto")
        self.assertEqual(snapshot["inputs"][0]["valor_original"], "10000.000000")

    def test_unidad_convertible_y_tenant_prevalece_sobre_global(self):
        self.factor(organization=None, code="global-cement", unit="kg", value="0.1")
        tenant = self.factor(organization=self.org, unit="kg", value="0.2")
        calculation, _ = calculate_activity(self.event(amount="10", unit="t"))
        self.assertEqual(calculation.version_factor, tenant)
        self.assertEqual(calculation.resultado, Decimal("2000"))
        self.assertEqual(calculation.snapshot_tecnico["inputs"][0]["unidad"], "kg")

    def test_sin_factor_o_factor_incompatible_no_es_calculable(self):
        activity = self.event()
        self.assertIsNone(select_methodology(activity)["seleccion"])
        self.factor(organization=self.org, unit="m3")
        selection = select_methodology(activity)
        self.assertIsNone(selection["seleccion"])
        self.assertIn("No existe un factor ambiental gobernado", " ".join(selection["candidata"]["motivos"]))

    def test_uso_no_es_punto_contable_y_no_suma_recepcion_mas_uso(self):
        self.factor(organization=self.org)
        reception = self.event("recepcion", "10000")
        usage = self.event("uso", "2500")
        calculation, _ = calculate_activity(reception)
        usage_selection = select_methodology(usage)
        self.assertEqual(calculation.resultado, Decimal("2000"))
        self.assertIsNone(usage_selection["seleccion"])
        self.assertEqual(usage_selection["estado"], "no_aplicable")
        material_candidate = next(item for item in usage_selection["candidatos"] if item["version_metodologia"].metodologia.codigo == MATERIAL_METHODOLOGY_CODE)
        self.assertIn("no es un punto contable", " ".join(material_candidate["motivos"]))

    def test_movimientos_no_contables_preservan_no_aplicable(self):
        for kind in ("uso", "consumo", "reutilizacion"):
            selection = select_methodology(self.event(kind, "1"))
            self.assertEqual(selection["estado"], "no_aplicable")
            self.assertIsNone(selection["seleccion"])
            payload = _serialize_selection(selection)
            self.assertEqual(payload["estado"], "no_aplicable")
            self.assertIn("no es un punto contable", payload["motivos"][0])
