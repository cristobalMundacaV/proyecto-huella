from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from .models import (
    ActividadOperacional,
    FactorAmbiental,
    FormulaAmbiental,
    MetodologiaAmbiental,
    Organizacion,
    RegistroFlujoAmbiental,
    VariableFormula,
    VersionFactorAmbiental,
    VersionMetodologia,
)
from .services.eligibility_v2 import evaluate_formula
from .services.fuel_factor_selector import select_fuel_factor

STATIONARY = {
    "estado": "clasificado",
    "categoria": "combustion_estacionaria",
    "alcance": 1,
}


class FuelFactorSelectorTests(TestCase):
    def setUp(self):
        self.organization = Organizacion.objects.create(nombre="Tenant factores")
        self.other = Organizacion.objects.create(nombre="Otro tenant")
        values = {
            ("combustion_estacionaria", "glp"): "1.59",
            ("combustion_estacionaria", "gas_natural"): "1.98",
            ("combustion_estacionaria", "diesel"): "2.71",
            ("combustion_movil", "glp"): "1.72",
            ("combustion_movil", "gas_natural"): "2.09",
            ("combustion_movil", "diesel"): "2.74",
        }
        for factor in FactorAmbiental.objects.filter(codigo__startswith="huellachile-"):
            VersionFactorAmbiental.objects.create(
                factor=factor,
                version=1,
                valor=Decimal(
                    values[
                        (
                            factor.contexto["categoria_huella"],
                            factor.contexto["combustible"],
                        )
                    ]
                ),
                fuente="Fixture gobernado",
                estado=VersionFactorAmbiental.Estado.ACTIVO,
            )
        self.activity_date = date(2025, 3, 1)

    def select(self, classification=STATIONARY, fuel="diesel", unit="m3", on_date=None):
        return select_fuel_factor(
            self.organization,
            classification,
            fuel,
            unit,
            on_date or self.activity_date,
        )

    def tenant_factor(
        self,
        organization=None,
        *,
        state=VersionFactorAmbiental.Estado.ACTIVO,
        category="combustion_estacionaria",
        fuel="diesel",
        valid_from=None,
        valid_to=None,
        unit="m3",
        value=Decimal("2.50"),
        metadata=True,
        code_suffix="",
    ):
        organization = organization or self.organization
        factor = FactorAmbiental.objects.create(
            organizacion=organization,
            codigo=f"tenant-{organization.id}-{category}-{fuel}{code_suffix}",
            nombre="Factor privado aprobado",
            categoria=category,
            unidad_entrada=unit,
            unidad_resultado="tCO2e",
            contexto=(
                {
                    "proveedor": "Tenant",
                    "alcance": 1,
                    "categoria_huella": category,
                    "combustible": fuel,
                }
                if metadata
                else {}
            ),
        )
        return VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=value,
            fuente="Factor privado validado",
            vigencia_desde=valid_from,
            vigencia_hasta=valid_to,
            estado=state,
        )

    def test_applicable_tenant_factor_has_priority(self):
        tenant = self.tenant_factor()

        selection = self.select()

        self.assertEqual(selection["estado"], "seleccionado")
        self.assertEqual(selection["origen"], "tenant")
        self.assertEqual(selection["factor_version"], tenant)

    def test_huellachile_is_used_when_tenant_factor_does_not_exist(self):
        selection = self.select()

        self.assertEqual(selection["estado"], "seleccionado")
        self.assertEqual(selection["origen"], "huellachile")
        self.assertEqual(
            selection["factor_version"].factor.codigo,
            "huellachile-combustion-estacionaria-diesel",
        )

    def test_missing_factor_is_not_calculable(self):
        selection = self.select(fuel="hidrogeno")

        self.assertEqual(selection["estado"], "no_calculable")
        self.assertIsNone(selection["factor_version"])

    def test_mobile_factor_is_not_used_for_stationary_activity(self):
        tenant = self.tenant_factor(category="combustion_movil")

        selection = self.select()

        self.assertNotEqual(selection["factor_version"], tenant)
        self.assertEqual(selection["origen"], "huellachile")

    def test_factor_for_another_fuel_is_not_used(self):
        tenant = self.tenant_factor(fuel="glp")

        selection = self.select()

        self.assertNotEqual(selection["factor_version"], tenant)
        self.assertEqual(selection["origen"], "huellachile")

    def test_inactive_or_expired_tenant_factor_falls_back_to_huellachile(self):
        self.tenant_factor(state=VersionFactorAmbiental.Estado.VALIDADO)
        expired = self.tenant_factor(
            fuel="gas_natural",
            valid_to=self.activity_date - timedelta(days=1),
        )

        diesel = self.select()
        gas = self.select(fuel="gas_natural")

        self.assertEqual(diesel["origen"], "huellachile")
        self.assertEqual(gas["origen"], "huellachile")
        self.assertNotEqual(gas["factor_version"], expired)

    def test_factor_from_other_tenant_is_never_exposed(self):
        foreign = self.tenant_factor(organization=self.other)

        selection = self.select()

        self.assertNotEqual(selection["factor_version"], foreign)
        self.assertEqual(selection["origen"], "huellachile")

    def test_pending_classification_never_selects_a_factor(self):
        selection = self.select(
            {"estado": "requiere_clasificacion", "categoria": None, "alcance": 1},
        )

        self.assertEqual(selection["estado"], "no_calculable")
        self.assertIsNone(selection["factor_version"])

    def test_mobile_diesel_selects_mobile_huellachile_factor(self):
        selection = self.select(
            classification={
                "estado": "clasificado",
                "categoria": "combustion_movil",
                "alcance": 1,
            }
        )

        self.assertEqual(selection["origen"], "huellachile")
        self.assertEqual(
            selection["factor_version"].factor.codigo,
            "huellachile-combustion-movil-diesel",
        )

    def test_tenant_without_required_metadata_is_discarded(self):
        incomplete = self.tenant_factor(metadata=False)

        selection = self.select()

        self.assertEqual(selection["origen"], "huellachile")
        candidate = next(
            item
            for item in selection["candidatos"]
            if item["version_id"] == incomplete.id
        )
        self.assertEqual(candidate["estado"], "descartado")
        self.assertTrue(
            any("metadata obligatoria" in reason for reason in candidate["motivos"])
        )

    def test_tenant_with_incompatible_unit_is_discarded(self):
        incompatible = self.tenant_factor(unit="kg")

        selection = self.select(unit="m³")

        self.assertEqual(selection["origen"], "huellachile")
        candidate = next(
            item
            for item in selection["candidatos"]
            if item["version_id"] == incompatible.id
        )
        self.assertTrue(
            any("Unidad incompatible" in reason for reason in candidate["motivos"])
        )

    def test_factor_valid_today_but_not_on_activity_date_is_discarded(self):
        future = self.tenant_factor(valid_from=date(2026, 1, 1))

        selection = self.select(on_date=date(2025, 3, 1))

        self.assertEqual(selection["origen"], "huellachile")
        candidate = next(
            item for item in selection["candidatos"] if item["version_id"] == future.id
        )
        self.assertTrue(
            any("aún no estaba vigente" in reason for reason in candidate["motivos"])
        )

    def test_historical_factor_valid_on_activity_date_is_selected(self):
        historical = self.tenant_factor(valid_to=date(2025, 12, 31))

        selection = self.select(on_date=date(2025, 3, 1))

        self.assertEqual(selection["origen"], "tenant")
        self.assertEqual(selection["factor_version"], historical)

    def test_multiple_active_tenant_versions_require_review(self):
        first = self.tenant_factor()
        VersionFactorAmbiental.objects.create(
            factor=first.factor,
            version=2,
            valor=Decimal("2.60"),
            fuente="Factor privado alternativo",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )

        selection = self.select()

        self.assertEqual(selection["estado"], "requiere_revision")
        self.assertIsNone(selection["factor_version"])

    def test_multiple_active_huellachile_versions_require_review(self):
        global_factor = FactorAmbiental.objects.get(
            codigo="huellachile-combustion-estacionaria-diesel",
            organizacion__isnull=True,
        )
        VersionFactorAmbiental.objects.create(
            factor=global_factor,
            version=2,
            valor=Decimal("2.72"),
            fuente="HuellaChile alternativa",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )

        selection = self.select()

        self.assertEqual(selection["estado"], "requiere_revision")
        self.assertIsNone(selection["factor_version"])

    def test_zero_factor_is_selectable(self):
        zero = self.tenant_factor(value=Decimal("0"))

        selection = self.select()

        self.assertEqual(selection["factor_version"], zero)
        self.assertEqual(selection["factor_version"].valor, Decimal("0"))

    def test_response_traces_selected_and_discarded_candidates(self):
        selected = self.tenant_factor()
        discarded = self.tenant_factor(
            fuel="glp",
            code_suffix="-discarded",
        )

        selection = self.select()

        self.assertEqual(selection["factor_version"], selected)
        by_version = {item["version_id"]: item for item in selection["candidatos"]}
        self.assertEqual(by_version[selected.id]["estado"], "aplicable")
        self.assertEqual(by_version[discarded.id]["estado"], "descartado")
        self.assertIn(
            "El combustible no coincide.", by_version[discarded.id]["motivos"]
        )

    def test_eligibility_uses_activity_timestamp_and_required_input_unit(self):
        timestamp = timezone.make_aware(
            datetime(2025, 3, 1, 10, 30),
            timezone.get_current_timezone(),
        )
        activity = ActividadOperacional.objects.create(
            organizacion=self.organization,
            tipo=ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO,
            codigo="fuel-historical-selection",
            nombre="Combustible histórico",
            timestamp_inicio=timestamp,
            metadata={"clasificacion_ambiental": STATIONARY},
        )
        RegistroFlujoAmbiental.objects.create(
            organizacion=self.organization,
            actividad=activity,
            flujo=RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO,
            periodo_inicio=timestamp,
            tipo_recurso="diesel",
            destino_operacional=RegistroFlujoAmbiental.DestinoOperacional.GENERADOR,
        )
        factor = FactorAmbiental.objects.get(
            codigo="huellachile-combustion-estacionaria-diesel",
            organizacion__isnull=True,
        )
        methodology = MetodologiaAmbiental.objects.create(
            codigo="fuel-historical-method",
            nombre="Método histórico",
            categoria="combustibles",
            flujo="combustible_estacionario",
        )
        version = VersionMetodologia.objects.create(
            metodologia=methodology,
            version=1,
            estado=VersionMetodologia.Estado.BORRADOR,
        )
        formula = FormulaAmbiental.objects.create(
            version_metodologia=version,
            factor_ambiental=factor,
            codigo="fuel-historical-formula",
            tipo=FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE,
            expresion_legible="combustible x factor",
        )
        VariableFormula.objects.create(
            formula=formula,
            clave="combustible",
            concepto_observacion="combustible_consumido",
            unidad_esperada="m3",
        )

        with patch(
            "apps.analytics.services.eligibility_v2.select_fuel_factor",
            wraps=select_fuel_factor,
        ) as selector:
            evaluate_formula(activity, formula)

        _, classification, fuel, required_unit, on_date = selector.call_args.args
        self.assertEqual(classification["categoria"], "combustion_estacionaria")
        self.assertEqual(fuel, "diesel")
        self.assertEqual(required_unit, "m3")
        self.assertEqual(on_date, timestamp)
