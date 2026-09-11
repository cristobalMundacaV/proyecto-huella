from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import FactorAmbiental, MaterialOperacional, Organizacion, VersionFactorAmbiental
from .services.material_factor_mapping import (
    approve_material_mapping,
    propose_material_mapping,
)
from .services.material_factor_selector import select_material_factor

User = get_user_model()


class MaterialFactorSelectorTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="Selector material")
        self.other_org = Organizacion.objects.create(nombre="Otro tenant selector")
        self.user = User.objects.create_superuser(
            "selector-admin", "selector-admin@example.com", "password"
        )
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org,
            codigo="MAT-CEM",
            nombre="Cemento Portland",
            categoria="cemento",
            unidad_base="kg",
            proveedor_fabricante="Proveedor X",
        )
        self.factor = FactorAmbiental.objects.create(
            organizacion=self.org,
            codigo="factor-cemento",
            nombre="Cemento",
            categoria="materiales",
            unidad_entrada="kg",
            unidad_resultado="kgCO2e",
        )
        self.version = VersionFactorAmbiental.objects.create(
            factor=self.factor,
            version=1,
            valor=Decimal("0.847351015163189"),
            fuente="Fixture",
            referencia="Test",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
            vigencia_desde=date(2026, 1, 1),
        )
        self.on_date = date(2026, 3, 1)

    def approved_mapping(self, **overrides):
        kwargs = {
            "vigencia_desde": date(2026, 1, 1),
            "vigencia_hasta": None,
        }
        kwargs.update(overrides)
        mapping = propose_material_mapping(
            self.org, self.material, self.factor, kwargs["vigencia_desde"],
            kwargs["vigencia_hasta"], self.user,
        )
        return approve_material_mapping(mapping.pk, self.org, self.user)

    def test_no_mapping_means_no_factor(self):
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])
        self.assertEqual(result["status"], "no_calculable")

    def test_exact_material_name_without_mapping_gives_no_factor(self):
        FactorAmbiental.objects.filter(pk=self.factor.pk).update(
            contexto={"material_codigo": "MAT-CEM", "producto": "Cemento Portland", "especificidad": "producto"}
        )
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])

    def test_exact_material_code_without_mapping_gives_no_factor(self):
        FactorAmbiental.objects.filter(pk=self.factor.pk).update(
            contexto={"material_codigo": "MAT-CEM", "especificidad": "producto"}
        )
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])

    def test_same_category_without_mapping_gives_no_factor(self):
        FactorAmbiental.objects.filter(pk=self.factor.pk).update(
            contexto={"especificidad": "categoria", "material_categoria": "cemento"}
        )
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])

    def test_supplier_match_without_mapping_gives_no_factor(self):
        FactorAmbiental.objects.filter(pk=self.factor.pk).update(
            contexto={"proveedor": "Proveedor X"}
        )
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])

    def test_explicit_mapping_selected(self):
        self.approved_mapping()
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertEqual(result["factor_version"], self.version)
        self.assertEqual(result["status"], "calculable")
        self.assertEqual(result["specificity"], "explicit_mapping")
        self.assertIsNotNone(result["mapping"])

    def test_approved_mapping_with_draft_version_is_not_calculable(self):
        draft_factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-borrador", nombre="Borrador",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        VersionFactorAmbiental.objects.create(
            factor=draft_factor, version=1, valor=Decimal("0.4"), fuente="Fixture",
            estado=VersionFactorAmbiental.Estado.BORRADOR, vigencia_desde=date(2026, 1, 1),
        )
        mapping = propose_material_mapping(
            self.org, self.material, draft_factor, date(2026, 1, 1), None, self.user,
        )
        approve_material_mapping(mapping.pk, self.org, self.user)
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])
        self.assertEqual(result["status"], "no_calculable")
        self.assertIn("ACTIVA", result["reason"])

    def test_expired_mapping_is_not_calculable(self):
        self.approved_mapping(
            vigencia_desde=date(2025, 1, 1), vigencia_hasta=date(2025, 12, 31)
        )
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])
        self.assertEqual(result["status"], "no_calculable")

    def test_future_mapping_is_not_calculable_before_valid_from(self):
        self.approved_mapping(vigencia_desde=date(2027, 1, 1), vigencia_hasta=None)
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertIsNone(result["factor_version"])

    def test_mapping_selects_correct_window_by_effective_date(self):
        old_mapping = propose_material_mapping(
            self.org, self.material, self.factor, date(2026, 1, 1), date(2026, 8, 31), self.user,
        )
        approve_material_mapping(old_mapping.pk, self.org, self.user)
        other_factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-cemento-y", nombre="Cemento Y",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        other_version = VersionFactorAmbiental.objects.create(
            factor=other_factor, version=1, valor=Decimal("0.5"), fuente="Fixture",
            estado=VersionFactorAmbiental.Estado.ACTIVO, vigencia_desde=date(2026, 1, 1),
        )
        new_mapping = propose_material_mapping(
            self.org, self.material, other_factor, date(2026, 9, 1), None, self.user,
        )
        approve_material_mapping(new_mapping.pk, self.org, self.user)

        july = select_material_factor(self.org, self.material, "kg", date(2026, 7, 10))
        self.assertEqual(july["factor_version"], self.version)

        september = select_material_factor(self.org, self.material, "kg", date(2026, 9, 15))
        self.assertEqual(september["factor_version"], other_version)

    def test_kg_factor_kg_reception(self):
        self.approved_mapping()
        result = select_material_factor(self.org, self.material, "kg", self.on_date)
        self.assertEqual(result["status"], "calculable")

    def test_kg_factor_t_reception_converts(self):
        self.approved_mapping()
        result = select_material_factor(self.org, self.material, "t", self.on_date)
        self.assertEqual(result["status"], "calculable")

    def test_m3_factor_m3_reception(self):
        self.factor.unidad_entrada = "m3"
        self.factor.save(update_fields=["unidad_entrada"])
        self.approved_mapping()
        result = select_material_factor(self.org, self.material, "m3", self.on_date)
        self.assertEqual(result["status"], "calculable")

    def test_m3_reception_vs_kg_factor_is_unsupported(self):
        self.approved_mapping()
        result = select_material_factor(self.org, self.material, "m3", self.on_date)
        self.assertEqual(result["status"], "no_calculable")
        self.assertIn("incompatible", result["reason"])

    def test_unknown_unit_is_unsupported(self):
        self.approved_mapping()
        result = select_material_factor(self.org, self.material, "sacos", self.on_date)
        self.assertEqual(result["status"], "no_calculable")

    def test_negative_factor_preserves_sign(self):
        negative_factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-negativo", nombre="A1 negativo",
            categoria="materiales_a1a3", unidad_entrada="m3", unidad_resultado="kgCO2e",
        )
        negative_version = VersionFactorAmbiental.objects.create(
            factor=negative_factor, version=1, valor=Decimal("-647.4201396839651"),
            fuente="Fixture", estado=VersionFactorAmbiental.Estado.ACTIVO,
            vigencia_desde=date(2026, 1, 1),
        )
        mapping = propose_material_mapping(
            self.org, self.material, negative_factor, date(2026, 1, 1), None, self.user,
        )
        approve_material_mapping(mapping.pk, self.org, self.user)
        result = select_material_factor(self.org, self.material, "m3", self.on_date)
        self.assertEqual(result["factor_version"], negative_version)
        self.assertLess(result["factor_version"].valor, 0)
