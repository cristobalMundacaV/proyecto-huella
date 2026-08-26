from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db.models import Q
from rest_framework.test import APITestCase

from .models import (
    FactorAmbiental,
    Organizacion,
    UsuarioOrganizacion,
    VersionFactorAmbiental,
)


PREFIX = "huellachile-"


class ImportHuellaChileFactorsTests(APITestCase):
    def import_catalog(self):
        output = StringIO()
        call_command("import_huellachile_factors", stdout=output)
        return output.getvalue()

    def factors(self):
        return FactorAmbiental.objects.filter(
            organizacion__isnull=True,
            codigo__startswith=PREFIX,
        )

    def test_import_creates_six_global_factors(self):
        self.import_catalog()

        self.assertEqual(self.factors().count(), 6)
        expected = {
            "huellachile-combustion-estacionaria-glp": (Decimal("1.59"), "tCO2e"),
            "huellachile-combustion-estacionaria-gas-natural": (Decimal("1.98"), "kgCO2e"),
            "huellachile-combustion-estacionaria-diesel": (Decimal("2.71"), "tCO2e"),
            "huellachile-combustion-movil-glp": (Decimal("1.72"), "tCO2e"),
            "huellachile-combustion-movil-gas-natural": (Decimal("2.09"), "tCO2e"),
            "huellachile-combustion-movil-diesel": (Decimal("2.74"), "tCO2e"),
        }
        for code, (value, result_unit) in expected.items():
            factor = self.factors().get(codigo=code)
            self.assertEqual(factor.unidad_entrada, "m3")
            self.assertEqual(factor.unidad_resultado, result_unit)
            self.assertEqual(factor.versiones.get().valor, value)

    def test_second_import_is_idempotent(self):
        self.import_catalog()
        self.import_catalog()

        self.assertEqual(self.factors().count(), 6)
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(factor__in=self.factors()).count(),
            6,
        )

    def test_stationary_diesel_preserves_official_value_and_units(self):
        self.import_catalog()

        factor = self.factors().get(
            codigo="huellachile-combustion-estacionaria-diesel"
        )
        self.assertEqual(factor.unidad_entrada, "m3")
        self.assertEqual(factor.unidad_resultado, "tCO2e")
        self.assertEqual(factor.versiones.get().valor, Decimal("2.71"))

    def test_mobile_diesel_is_a_distinct_factor(self):
        self.import_catalog()

        stationary = self.factors().get(
            codigo="huellachile-combustion-estacionaria-diesel"
        )
        mobile = self.factors().get(codigo="huellachile-combustion-movil-diesel")
        self.assertNotEqual(stationary.pk, mobile.pk)
        self.assertEqual(mobile.versiones.get().valor, Decimal("2.74"))

    def test_every_factor_is_global(self):
        self.import_catalog()

        self.assertFalse(self.factors().exclude(organizacion__isnull=True).exists())
        self.assertEqual(self.factors().count(), 6)

    def test_every_factor_has_one_active_version(self):
        self.import_catalog()

        for factor in self.factors():
            versions = factor.versiones.filter(
                estado=VersionFactorAmbiental.Estado.ACTIVO
            )
            self.assertEqual(versions.count(), 1)
            self.assertIsNone(versions.get().vigencia_desde)
            self.assertIsNone(versions.get().vigencia_hasta)

    def test_metadata_identifies_source_scope_category_fuel_and_document(self):
        self.import_catalog()

        for factor in self.factors():
            self.assertEqual(factor.contexto["proveedor"], "HuellaChile")
            self.assertEqual(factor.contexto["alcance"], 1)
            self.assertIn(
                factor.contexto["categoria_huella"],
                {"combustion_estacionaria", "combustion_movil"},
            )
            self.assertIn(
                factor.contexto["combustible"],
                {"glp", "gas_natural", "diesel"},
            )
            self.assertEqual(factor.contexto["documento_version"], 3)
            self.assertEqual(factor.contexto["fecha_actualizacion"], "2024-11-28")

    def test_tenant_factor_coexists_and_other_tenant_is_not_exposed(self):
        self.import_catalog()
        own = Organizacion.objects.create(nombre="Tenant propio")
        other = Organizacion.objects.create(nombre="Tenant ajeno")
        code = "huellachile-combustion-estacionaria-diesel"
        own_factor = FactorAmbiental.objects.create(
            organizacion=own,
            codigo=code,
            nombre="Factor privado propio",
            categoria="combustion_estacionaria",
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
        )
        other_factor = FactorAmbiental.objects.create(
            organizacion=other,
            codigo=code,
            nombre="Factor privado ajeno",
            categoria="combustion_estacionaria",
            unidad_entrada="m3",
            unidad_resultado="tCO2e",
        )
        visible = FactorAmbiental.objects.filter(
            Q(organizacion=own) | Q(organizacion__isnull=True)
        )
        self.assertEqual(visible.filter(codigo=code).count(), 2)
        self.assertTrue(visible.filter(pk=own_factor.pk).exists())
        self.assertFalse(visible.filter(pk=other_factor.pk).exists())

        user = User.objects.create_user("factor-reader", password="test-pass")
        UsuarioOrganizacion.objects.create(user=user, organizacion=own)
        self.client.force_login(user)
        response = self.client.get(
            f"/api/organizaciones/{own.organizacion_id}/factores-ambientales/"
        )
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data}
        self.assertIn(own_factor.id, ids)
        self.assertNotIn(other_factor.id, ids)
