from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .management.commands.bootstrap_calculation_v2 import (
    ENERGY_FACTOR_CODE,
    ENERGY_METHODOLOGY_CODE,
)
from .models import (
    ActividadOperacional,
    CalculoAmbiental,
    FactorAmbiental,
    FuenteDatos,
    ImpactoAmbiental,
    MetodologiaAmbiental,
    Obra,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    ValorIndicador,
    VersionFactorAmbiental,
    EvaluacionCalidadDato,
)
from .services.calculation_v2 import calculate_activity
from .services.methodology_selector import select_methodology


class EnergyCalculationBootstrapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("bootstrap_calculation_v2", stdout=StringIO())

    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Construccion energia E2E")
        self.work = Obra.objects.create(
            organizacion=self.organization,
            nombre="Edificio Parque Norte",
            fecha_inicio=date(2026, 1, 1),
        )
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Lectura manual de medidor electrico",
            tipo=FuenteDatos.Tipo.MANUAL,
        )
        self.timestamp = timezone.make_aware(datetime(2026, 9, 11, 10, 0))

    def energy_activity(
        self,
        *,
        code="energy-grid",
        value="1000",
        unit="kWh",
        flow=RegistroFlujoAmbiental.Flujo.ENERGIA,
        resource="red_electrica",
        activity_type=ActividadOperacional.Tipo.CONSUMO_ENERGIA,
    ):
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            obra=self.work,
            codigo=code,
            nombre=code,
            tipo=activity_type,
            timestamp_inicio=self.timestamp,
        )
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            obra=self.work,
            flujo=flow,
            granularidad=RegistroFlujoAmbiental.Granularidad.OBRA,
            periodo_inicio=self.timestamp,
            tipo_recurso=resource,
        )
        Observacion.objects.create(
            organizacion=self.organization,
            actividad=activity,
            fuente=self.source,
            concepto="consumo_energia",
            valor_numerico=Decimal(value),
            unidad=unit,
            timestamp_observacion=self.timestamp,
            estado=Observacion.Estado.VALIDADA,
        )
        return activity

    def test_grid_electricity_is_automatic_normalized_calculated_and_traceable(self):
        activity = self.energy_activity()

        selection = select_methodology(activity)
        self.assertEqual(selection["estado"], "calculable_completo")
        quality = EvaluacionCalidadDato.objects.get(observacion__actividad=activity)
        self.assertEqual(
            quality.estado,
            EvaluacionCalidadDato.Estado.CONFIABLE_OBSERVACIONES,
        )
        self.assertEqual(
            selection["seleccion"]["version_metodologia"].metodologia.codigo,
            ENERGY_METHODOLOGY_CODE,
        )

        calculation, _ = calculate_activity(activity)
        self.assertEqual(calculation.resultado, Decimal("0.2466"))
        self.assertEqual(calculation.unidad_resultado, "tCO2e")
        self.assertEqual(calculation.version_factor.factor.codigo, ENERGY_FACTOR_CODE)
        self.assertTrue(ImpactoAmbiental.objects.filter(calculo=calculation).exists())

        snapshot = calculation.snapshot_tecnico
        self.assertEqual(snapshot["metodologia_codigo"], ENERGY_METHODOLOGY_CODE)
        self.assertEqual(snapshot["metodologia_version"], 1)
        self.assertEqual(snapshot["factor_valor"], "0.2466000000")
        self.assertIn("Ministerio", snapshot["factor_fuente"])
        self.assertIn("factor oficial 2025", snapshot["factor_referencia"])
        self.assertEqual(snapshot["factor_contexto"]["factor_year"], 2025)
        self.assertEqual(snapshot["factor_contexto"]["sistema"], "SEN")
        self.assertEqual(snapshot["factor_contexto"]["metodo"], "location_based")
        self.assertEqual(snapshot["factor_contexto"]["alcance"], 2)
        self.assertEqual(snapshot["factor_contexto"]["pais"], "Chile")
        self.assertEqual(Decimal(snapshot["resultado"]), Decimal("0.2466"))
        input_data = snapshot["inputs"][0]
        self.assertEqual(input_data["valor_original"], "1000.000000")
        self.assertEqual(input_data["unidad_original"], "kWh")
        self.assertEqual(input_data["valor"], "1.000000000")
        self.assertEqual(input_data["unidad"], "MWh")
        self.assertEqual(input_data["regla_conversion"], "kWh → MWh")
        self.assertEqual(input_data["factor_conversion"], "0.001")

        indicator_value = ValorIndicador.objects.get(indicador__obra=self.work)
        self.assertEqual(indicator_value.valor, Decimal("0.2466"))
        self.assertEqual(indicator_value.metadata["fuentes"][0]["alcance"], 2)
        self.assertEqual(
            indicator_value.metadata["fuentes"][0]["metodo"], "location_based"
        )

    def test_mwh_input_is_not_reconverted(self):
        calculation, _ = calculate_activity(
            self.energy_activity(code="energy-mwh", value="1", unit="MWh")
        )
        input_data = calculation.snapshot_tecnico["inputs"][0]
        self.assertEqual(calculation.resultado, Decimal("0.2466"))
        self.assertEqual(input_data["valor"], "1.000000")
        self.assertFalse(input_data["conversion_aplicada"])
        self.assertIsNone(input_data["regla_conversion"])

    def test_factor_and_methodology_use_operational_date(self):
        factor = FactorAmbiental.objects.get(codigo=ENERGY_FACTOR_CODE)
        future = VersionFactorAmbiental.objects.create(
            factor=factor,
            version=2,
            valor=Decimal("0.1000"),
            fuente="Version futura gobernada",
            referencia="Aplicable desde 2027",
            region="Chile",
            vigencia_desde=date(2027, 1, 1),
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        calculation, _ = calculate_activity(self.energy_activity(code="energy-historic"))
        self.assertNotEqual(calculation.version_factor_id, future.id)
        self.assertEqual(calculation.version_factor.version, 1)
        self.assertEqual(calculation.resultado, Decimal("0.2466"))

    def test_solar_and_own_generation_do_not_use_grid_methodology(self):
        solar = self.energy_activity(code="solar", resource="solar_fotovoltaica")
        own_generation = self.energy_activity(
            code="own-generation",
            flow=RegistroFlujoAmbiental.Flujo.GENERACION_PROPIA,
            resource="solar_fotovoltaica",
            activity_type=ActividadOperacional.Tipo.GENERACION_ENERGIA,
        )
        for activity in (solar, own_generation):
            selection = select_methodology(activity)
            self.assertIsNone(selection["seleccion"])
            applicable_codes = {
                item["version_metodologia"].metodologia.codigo
                for item in selection["candidatos"]
                if item["estado"] != "no_aplicable"
            }
            self.assertNotIn(ENERGY_METHODOLOGY_CODE, applicable_codes)


class EnergyBootstrapIdempotencyTests(TestCase):
    def test_bootstrap_twice_does_not_duplicate_energy_governance(self):
        call_command("bootstrap_calculation_v2", stdout=StringIO())
        counts = (
            FactorAmbiental.objects.count(),
            VersionFactorAmbiental.objects.count(),
            MetodologiaAmbiental.objects.count(),
        )
        call_command("bootstrap_calculation_v2", stdout=StringIO())
        self.assertEqual(
            counts,
            (
                FactorAmbiental.objects.count(),
                VersionFactorAmbiental.objects.count(),
                MetodologiaAmbiental.objects.count(),
            ),
        )
