from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .management.commands.bootstrap_calculation_v2 import METHODOLOGY_CODE
from .models import (
    ActividadOperacional,
    CalculoAmbiental,
    FactorAmbiental,
    FormulaAmbiental,
    FuenteDatos,
    MetodologiaAmbiental,
    Observacion,
    Organizacion,
    RegistroFlujoAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .services.calculation_v2 import calculate_activity
from .services.methodology_selector import select_methodology


class FuelCalculationBootstrapTests(TestCase):
    def bootstrap(self):
        output = StringIO()
        call_command("bootstrap_calculation_v2", stdout=output)
        return output.getvalue()

    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Construccion E2E")
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Vale de combustible",
            tipo=FuenteDatos.Tipo.MANUAL,
        )

    def activity(self, *, pk, flow, destination, activity_type):
        timestamp = timezone.now()
        activity = ActividadOperacional.objects.create(
            id=pk,
            organizacion=self.organization,
            codigo=f"fuel-{pk}",
            nombre=f"Combustible {destination}",
            tipo=activity_type,
            timestamp_inicio=timestamp,
        )
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            flujo=flow,
            periodo_inicio=timestamp,
            tipo_recurso="diesel",
            destino_operacional=destination,
        )
        Observacion.objects.create(
            organizacion=self.organization,
            actividad=activity,
            fuente=self.source,
            concepto="combustible_consumido",
            valor_numerico=Decimal("250"),
            unidad="L",
            timestamp_observacion=timestamp,
            estado=Observacion.Estado.VALIDADA,
        )
        return activity

    def provision_test_fuel_versions(self):
        values = {
            ("combustion_estacionaria", "diesel"): Decimal("2.71"),
            ("combustion_movil", "diesel"): Decimal("2.74"),
        }
        for (category, fuel), value in values.items():
            factor = FactorAmbiental.objects.get(
                contexto__categoria_huella=category,
                contexto__combustible=fuel,
            )
            VersionFactorAmbiental.objects.create(
                factor=factor,
                version=1,
                valor=value,
                fuente="Fixture gobernado",
                referencia="Valor aislado para regresión Calculation V2",
                estado=VersionFactorAmbiental.Estado.ACTIVO,
            )

    def test_system_provisions_catalog_and_governed_methodology(self):
        self.assertEqual(
            FactorAmbiental.objects.filter(codigo__startswith="huellachile-").count(),
            6,
        )
        methodology = MetodologiaAmbiental.objects.get(codigo=METHODOLOGY_CODE)
        self.assertIsNone(methodology.organizacion_id)
        version = methodology.versiones.get(version=1)
        self.assertEqual(version.estado, VersionMetodologia.Estado.ACTIVA)
        self.assertTrue(version.fuente_referencia)
        self.assertEqual(version.prioridad, 10)
        self.assertEqual(
            version.formula.tipo, FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO
        )
        self.assertIsNone(version.formula.factor_ambiental_id)
        variable = version.formula.variables.get()
        self.assertEqual(variable.clave, "combustible_consumido")
        self.assertEqual(variable.unidad_esperada, "m3")

    def test_bootstrap_is_idempotent(self):
        self.bootstrap()
        counts = (
            FactorAmbiental.objects.count(),
            VersionFactorAmbiental.objects.count(),
            MetodologiaAmbiental.objects.count(),
            VersionMetodologia.objects.count(),
            FormulaAmbiental.objects.count(),
            VariableFormula.objects.count(),
        )

        self.bootstrap()

        self.assertEqual(
            counts,
            (
                FactorAmbiental.objects.count(),
                VersionFactorAmbiental.objects.count(),
                MetodologiaAmbiental.objects.count(),
                VersionMetodologia.objects.count(),
                FormulaAmbiental.objects.count(),
                VariableFormula.objects.count(),
            ),
        )

    def test_stationary_diesel_e2e_is_automatic_normalized_and_traceable(self):
        self.bootstrap()
        self.provision_test_fuel_versions()
        activity = self.activity(
            pk=777,
            flow=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
            destination=RegistroFlujoAmbiental.DestinoOperacional.GENERADOR,
            activity_type=ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
        )

        selection = select_methodology(activity)

        self.assertEqual(selection["estado"], "calculable_completo")
        self.assertEqual(
            selection["seleccion"]["version_metodologia"].metodologia.codigo,
            METHODOLOGY_CODE,
        )
        self.assertEqual(
            selection["seleccion"]["elegibilidad"]["clasificacion_combustible"][
                "categoria"
            ],
            "combustion_estacionaria",
        )
        self.assertNotIn(
            "La actividad no tiene un vehiculo asociado.",
            selection["seleccion"]["elegibilidad"]["motivos"],
        )
        calculation, _ = calculate_activity(activity)

        self.assertEqual(calculation.resultado, Decimal("0.6775"))
        self.assertEqual(calculation.unidad_resultado, "tCO2e")
        self.assertEqual(
            calculation.version_factor.factor.codigo,
            "huellachile-combustion-estacionaria-diesel",
        )
        snapshot = calculation.snapshot_tecnico
        self.assertEqual(snapshot["metodologia_codigo"], METHODOLOGY_CODE)
        self.assertEqual(snapshot["metodologia_version"], 1)
        self.assertEqual(
            snapshot["factor_codigo"], calculation.version_factor.factor.codigo
        )
        self.assertEqual(snapshot["factor_valor"], "2.7100000000")
        self.assertEqual(snapshot["factor_fuente"], "Fixture gobernado")
        self.assertTrue(snapshot["factor_referencia"])
        self.assertEqual(Decimal(snapshot["resultado"]), Decimal("0.6775"))
        input_snapshot = snapshot["inputs"][0]
        self.assertEqual(input_snapshot["valor_original"], "250.000000")
        self.assertEqual(input_snapshot["unidad_original"], "L")
        self.assertEqual(input_snapshot["valor"], "0.250000000")
        self.assertEqual(input_snapshot["unidad"], "m3")
        self.assertTrue(input_snapshot["conversion_aplicada"])
        self.assertEqual(input_snapshot["factor_conversion"], "0.001")
        self.assertEqual(CalculoAmbiental.objects.count(), 1)

    def test_mobile_fuel_keeps_dynamic_mobile_factor_selection(self):
        self.bootstrap()
        self.provision_test_fuel_versions()
        activity = self.activity(
            pk=778,
            flow=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_MOVIL,
            destination=RegistroFlujoAmbiental.DestinoOperacional.VEHICULO,
            activity_type=ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE,
        )

        calculation, selection = calculate_activity(activity)

        self.assertEqual(selection["estado"], "calculable_completo")
        self.assertEqual(
            calculation.version_factor.factor.codigo,
            "huellachile-combustion-movil-diesel",
        )
        self.assertEqual(calculation.resultado, Decimal("0.685"))
