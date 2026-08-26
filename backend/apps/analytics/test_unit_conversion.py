from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    ActivoOperacional,
    FactorAmbiental,
    FormulaAmbiental,
    FuenteDatos,
    MetodologiaAmbiental,
    Observacion,
    Organizacion,
    VariableFormula,
    Vehiculo,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .services.eligibility_v2 import evaluate_formula
from .services.unit_conversion import UnitConversionError, convert_value


class UnitConversionTests(SimpleTestCase):
    def test_liters_to_cubic_meters(self):
        result = convert_value(Decimal("20"), "L", "m3")

        self.assertEqual(result["valor_normalizado"], Decimal("0.020"))
        self.assertEqual(result["factor_conversion"], Decimal("0.001"))
        self.assertEqual(result["regla"], "L → m3")
        self.assertTrue(result["conversion_aplicada"])

    def test_cubic_meters_to_liters(self):
        result = convert_value(Decimal("1"), "m3", "L")

        self.assertEqual(result["valor_normalizado"], Decimal("1000"))

    def test_kilograms_to_tonnes(self):
        result = convert_value(Decimal("500"), "kg", "t")

        self.assertEqual(result["valor_normalizado"], Decimal("0.500"))

    def test_tonnes_to_kilograms(self):
        result = convert_value(Decimal("1.5"), "t", "kg")

        self.assertEqual(result["valor_normalizado"], Decimal("1500"))

    def test_same_unit_does_not_apply_conversion(self):
        result = convert_value(Decimal("20"), "L", "litros")

        self.assertEqual(result["valor_normalizado"], Decimal("20"))
        self.assertEqual(result["unidad_normalizada"], "L")
        self.assertFalse(result["conversion_aplicada"])
        self.assertEqual(result["factor_conversion"], Decimal("1"))

    def test_volume_to_mass_is_rejected(self):
        with self.assertRaisesRegex(
            UnitConversionError,
            "no existe una conversión segura de L a kg",
        ):
            convert_value(Decimal("20"), "L", "kg")

    def test_mass_to_volume_is_rejected(self):
        with self.assertRaisesRegex(
            UnitConversionError,
            "no existe una conversión segura de kg a m3",
        ):
            convert_value(Decimal("20"), "kg", "m3")

    def test_unknown_unit_is_rejected_clearly(self):
        with self.assertRaisesRegex(UnitConversionError, "Unidad desconocida: galón"):
            convert_value(Decimal("20"), "galón", "L")

    def test_supported_aliases_are_canonicalized(self):
        cubic_meters = convert_value(Decimal("1"), "m³", "m3")
        liters = convert_value(Decimal("1"), "litros", "L")
        tonnes = convert_value(Decimal("1"), "toneladas", "t")

        self.assertEqual(cubic_meters["unidad_original"], "m3")
        self.assertEqual(liters["unidad_original"], "L")
        self.assertEqual(tonnes["unidad_original"], "t")


class EligibilityUnitConversionTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Conversión segura")
        self.source = FuenteDatos.objects.create(
            organizacion=self.organization,
            nombre="Registro operacional",
            tipo=FuenteDatos.Tipo.MANUAL,
        )
        self.activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            codigo="FUEL-CONVERSION-01",
            nombre="Carga de combustible",
            tipo=ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE,
            timestamp_inicio=timezone.now(),
        )
        asset = ActivoOperacional.objects.create(
            organizacion=self.organization,
            codigo="VEH-CONVERSION-01",
            nombre="Vehículo de prueba",
            tipo="vehiculo",
        )
        Vehiculo.objects.create(
            activo=asset,
            tipo_vehiculo="camion",
            combustible="diesel",
        )
        self.activity.activos.add(asset)
        factor = FactorAmbiental.objects.create(
            codigo="factor-conversion-test",
            nombre="Factor de prueba de conversión",
            categoria="combustibles",
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
        )
        VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=Decimal("2.71"),
            fuente="PRUEBA",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        methodology = MetodologiaAmbiental.objects.create(
            codigo="metodo-conversion-test",
            nombre="Método de prueba de conversión",
            categoria="combustibles",
            flujo="combustible_estacionario",
        )
        methodology_version = VersionMetodologia.objects.create(
            metodologia=methodology,
            version=1,
            estado=VersionMetodologia.Estado.BORRADOR,
        )
        self.formula = FormulaAmbiental.objects.create(
            version_metodologia=methodology_version,
            factor_ambiental=factor,
            codigo="formula-conversion-test",
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            expresion_legible="combustible x factor",
        )
        VariableFormula.objects.create(
            formula=self.formula,
            clave="combustible",
            concepto_observacion="combustible_consumido",
            unidad_esperada="m3",
        )

    def observe(self, value, unit):
        return Observacion.objects.create(
            organizacion=self.organization,
            actividad=self.activity,
            fuente=self.source,
            concepto="combustible_consumido",
            valor_numerico=value,
            unidad=unit,
            timestamp_observacion=timezone.now(),
        )

    def test_liters_are_eligible_for_variable_in_cubic_meters(self):
        observation = self.observe("20", "L")

        result = evaluate_formula(self.activity, self.formula)

        self.assertEqual(result["estado"], "calculable_completo")
        self.assertEqual(result["inputs"]["combustible"][1], observation)
        self.assertEqual(
            result["inputs"]["combustible"][2]["valor_normalizado"],
            Decimal("0.020"),
        )
        normalization = result["normalizaciones"]["combustible"]
        self.assertEqual(normalization["valor_original"], Decimal("20"))
        self.assertEqual(normalization["unidad_original"], "L")
        self.assertEqual(normalization["valor_normalizado"], Decimal("0.020"))
        self.assertEqual(normalization["unidad_normalizada"], "m3")
        observation.refresh_from_db()
        self.assertEqual(observation.valor_numerico, Decimal("20"))
        self.assertEqual(observation.unidad, "L")

    def test_kilograms_remain_ineligible_for_variable_in_cubic_meters(self):
        self.observe("20", "kg")

        result = evaluate_formula(self.activity, self.formula)

        self.assertEqual(result["estado"], "no_calculable")
        self.assertIn(
            "Unidad incompatible: no existe una conversión segura de kg a m3.",
            result["motivos"],
        )
        self.assertNotIn("combustible", result["inputs"])
