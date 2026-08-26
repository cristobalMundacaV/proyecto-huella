from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import FactorAmbiental, Organizacion, VersionFactorAmbiental
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
        call_command("import_huellachile_factors", stdout=StringIO())

    def tenant_factor(
        self,
        organization=None,
        *,
        state=VersionFactorAmbiental.Estado.ACTIVO,
        category="combustion_estacionaria",
        fuel="diesel",
        valid_from=None,
        valid_to=None,
    ):
        organization = organization or self.organization
        factor = FactorAmbiental.objects.create(
            organizacion=organization,
            codigo=f"tenant-{organization.id}-{category}-{fuel}",
            nombre="Factor privado aprobado",
            categoria=category,
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
            contexto={
                "proveedor": "Tenant",
                "alcance": 1,
                "categoria_huella": category,
                "combustible": fuel,
            },
        )
        return VersionFactorAmbiental.objects.create(
            factor=factor,
            version=1,
            valor=Decimal("2.50"),
            fuente="Factor privado validado",
            vigencia_desde=valid_from,
            vigencia_hasta=valid_to,
            estado=state,
        )

    def test_applicable_tenant_factor_has_priority(self):
        tenant = self.tenant_factor()

        selection = select_fuel_factor(self.organization, STATIONARY, "diesel")

        self.assertEqual(selection["estado"], "seleccionado")
        self.assertEqual(selection["origen"], "tenant")
        self.assertEqual(selection["factor_version"], tenant)

    def test_huellachile_is_used_when_tenant_factor_does_not_exist(self):
        selection = select_fuel_factor(self.organization, STATIONARY, "diesel")

        self.assertEqual(selection["estado"], "seleccionado")
        self.assertEqual(selection["origen"], "huellachile")
        self.assertEqual(
            selection["factor_version"].factor.codigo,
            "huellachile-combustion-estacionaria-diesel",
        )

    def test_missing_factor_is_not_calculable(self):
        selection = select_fuel_factor(self.organization, STATIONARY, "hidrogeno")

        self.assertEqual(selection["estado"], "no_calculable")
        self.assertIsNone(selection["factor_version"])

    def test_mobile_factor_is_not_used_for_stationary_activity(self):
        tenant = self.tenant_factor(category="combustion_movil")

        selection = select_fuel_factor(self.organization, STATIONARY, "diesel")

        self.assertNotEqual(selection["factor_version"], tenant)
        self.assertEqual(selection["origen"], "huellachile")

    def test_factor_for_another_fuel_is_not_used(self):
        tenant = self.tenant_factor(fuel="glp")

        selection = select_fuel_factor(self.organization, STATIONARY, "diesel")

        self.assertNotEqual(selection["factor_version"], tenant)
        self.assertEqual(selection["origen"], "huellachile")

    def test_inactive_or_expired_tenant_factor_falls_back_to_huellachile(self):
        self.tenant_factor(state=VersionFactorAmbiental.Estado.VALIDADO)
        expired = self.tenant_factor(
            fuel="gas_natural",
            valid_to=timezone.localdate() - timedelta(days=1),
        )

        diesel = select_fuel_factor(self.organization, STATIONARY, "diesel")
        gas = select_fuel_factor(self.organization, STATIONARY, "gas_natural")

        self.assertEqual(diesel["origen"], "huellachile")
        self.assertEqual(gas["origen"], "huellachile")
        self.assertNotEqual(gas["factor_version"], expired)

    def test_factor_from_other_tenant_is_never_exposed(self):
        foreign = self.tenant_factor(organization=self.other)

        selection = select_fuel_factor(self.organization, STATIONARY, "diesel")

        self.assertNotEqual(selection["factor_version"], foreign)
        self.assertEqual(selection["origen"], "huellachile")

    def test_pending_classification_never_selects_a_factor(self):
        selection = select_fuel_factor(
            self.organization,
            {"estado": "requiere_clasificacion", "categoria": None, "alcance": 1},
            "diesel",
        )

        self.assertEqual(selection["estado"], "no_calculable")
        self.assertIsNone(selection["factor_version"])
