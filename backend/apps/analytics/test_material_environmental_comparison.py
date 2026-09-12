"""MI-01E — Deterministic Environmental Comparison tests.

Reuses the real ÖKOBAUDAT fixtures ("a1" = EN 15804+A1, negative GWP, m3;
"a2" = EN 15804+A2, positive GWP, kg) for the governed integration path, and
direct FactorAmbiental/VersionFactorAmbiental construction for pure-math
edge cases (zero/negative baseline) that do not need to be comparability-
eligible to exercise the arithmetic itself.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import FactorAmbiental, MaterialOperacional, Organizacion, UsuarioOrganizacion, VersionFactorAmbiental
from .services.factor_governance import transition_factor_version
from .services.material_application_profile import approve_profile, create_profile
from .services.material_candidates import (
    build_material_candidate,
    promote_material_candidate,
    review_material_candidate,
)
from .services.material_environmental_comparison import compare_materials, material_impact_per_functional_unit
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_functional_use import approve_functional_use, create_functional_use
from .services.material_suitability import decide_human_approval, record_assessment
from .services.material_technical_property import approve_assertion, create_assertion
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


class EnvironmentalComparisonIntegrationTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "mi01e-reviewer", "mi01e-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01E org")
        UsuarioOrganizacion.objects.create(
            user=self.reviewer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        profile = create_profile(
            self.org, self.reviewer, "PERFIL-01E", "Perfil comparacion", Decimal("1"), "m2",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        self.profile = approve_profile(profile.pk, self.org, self.reviewer)
        self._factor_cache = {}

    def _activated_factor(self, label):
        if label in self._factor_cache:
            return self._factor_cache[label]
        fixture_profile = material_fixture(label)
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        version = transition_factor_version(version, "activo")
        self._factor_cache[label] = (factor, version)
        return factor, version

    def _eligible_material(self, label, codigo, quantity, unit=None):
        factor, version = self._activated_factor(label)
        unit = unit or ("kg" if label == "a2" else "m3")
        material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base=unit,
        )
        mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.reviewer)
        approve_material_mapping(mapping.pk, self.org, self.reviewer)
        assertion = create_assertion(
            self.org, self.reviewer, material, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
        )
        approve_assertion(assertion.pk, self.org, self.reviewer)
        assessment = record_assessment(self.org, self.reviewer, material, self.profile)
        decide_human_approval(assessment.pk, self.org, self.reviewer, approved=True)
        functional_use = create_functional_use(
            self.org, self.reviewer, material, self.profile, Decimal(str(quantity)), unit, "Justificación técnica",
        )
        approve_functional_use(functional_use.pk, self.org, self.reviewer)
        return material, version

    def test_equal_functional_quantities(self):
        baseline, _ = self._eligible_material("a2", "MAT-EQ-A", "10")
        alternative, _ = self._eligible_material("a2", "MAT-EQ-B", "10")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertTrue(result["comparable"])
        self.assertEqual(result["absolute_delta"], Decimal("0"))
        self.assertEqual(result["relative_delta"], Decimal("0"))

    def test_different_functional_quantities_change_ranking(self):
        # Same per-kg factor (same fixture) but different functional
        # quantities must change the per-functional-unit impact.
        baseline, _ = self._eligible_material("a2", "MAT-DIF-A", "10")
        alternative, _ = self._eligible_material("a2", "MAT-DIF-B", "6")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertTrue(result["comparable"])
        self.assertLess(
            result["alternative"]["impact_a1a3_per_functional_unit"],
            result["baseline"]["impact_a1a3_per_functional_unit"],
        )
        self.assertLess(result["absolute_delta"], 0)

    def test_tonnes_to_kg_governed_conversion(self):
        baseline, _ = self._eligible_material("a2", "MAT-CONV-A", "10", unit="kg")
        alternative, _ = self._eligible_material("a2", "MAT-CONV-B", "0.01", unit="t")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertTrue(result["comparable"])
        self.assertEqual(
            result["baseline"]["impact_a1a3_per_functional_unit"],
            result["alternative"]["impact_a1a3_per_functional_unit"],
        )

    def test_a1_comparison(self):
        baseline, _ = self._eligible_material("a1", "MAT-A1-CMP-A", "2")
        alternative, _ = self._eligible_material("a1", "MAT-A1-CMP-B", "3")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertTrue(result["comparable"])
        self.assertLess(result["baseline"]["impact_a1a3_per_functional_unit"], 0)
        self.assertIn("negative_gwp_present_sign_preserved", result["warnings"])

    def test_a2_comparison(self):
        baseline, _ = self._eligible_material("a2", "MAT-A2-CMP-A", "10")
        alternative, _ = self._eligible_material("a2", "MAT-A2-CMP-B", "12")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertTrue(result["comparable"])
        self.assertGreater(result["baseline"]["impact_a1a3_per_functional_unit"], 0)

    def test_a1_a2_rejected_as_not_comparable(self):
        baseline, _ = self._eligible_material("a1", "MAT-A1-REJ", "2")
        alternative, _ = self._eligible_material("a2", "MAT-A2-REJ", "10")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertFalse(result["comparable"])
        self.assertEqual(result["reason"], "standard_mismatch")

    def test_negative_baseline_percentage_handling(self):
        baseline, _ = self._eligible_material("a1", "MAT-NEGBASE-A", "2")
        alternative, _ = self._eligible_material("a1", "MAT-NEGBASE-B", "2")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertTrue(result["comparable"])
        self.assertLess(result["baseline"]["impact_a1a3_per_functional_unit"], 0)
        self.assertIsNone(result["relative_delta"])
        self.assertIn("baseline_negative_percentage_omitted", result["warnings"])

    def test_historical_provenance_traceable(self):
        baseline, version = self._eligible_material("a2", "MAT-HIST-A", "10")
        alternative, _ = self._eligible_material("a2", "MAT-HIST-B", "10")
        result = compare_materials(self.org, baseline, alternative, self.profile)
        self.assertEqual(result["baseline"]["factor_version_id"], version.pk)
        self.assertEqual(result["baseline"]["material_id"], baseline.pk)


class ImpactPureMathTests(TestCase):
    def setUp(self):
        self.org = Organizacion.objects.create(nombre="MI-01E math org")
        self.reviewer = User.objects.create_superuser(
            "mi01e-math-reviewer", "mi01e-math-reviewer@example.com", "password"
        )
        UsuarioOrganizacion.objects.create(
            user=self.reviewer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        profile = create_profile(self.org, self.reviewer, "PERFIL-MATH", "Perfil", Decimal("1"), "m2")
        self.profile = approve_profile(profile.pk, self.org, self.reviewer)
        self.material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-MATH", nombre="Material math",
            categoria="materiales", unidad_base="kg",
        )
        self.functional_use = create_functional_use(
            self.org, self.reviewer, self.material, self.profile, Decimal("10"), "kg", "Justificación",
        )
        approve_functional_use(self.functional_use.pk, self.org, self.reviewer)

    def _version(self, valor):
        factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo=f"factor-math-{valor}", nombre="Factor math",
            categoria="materiales", unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        return VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal(str(valor)), fuente="test",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )

    def test_worked_example_lower_per_kg_factor_can_still_lose(self):
        # 10 kg/FU x 0.8 kgCO2e/kg = 8 kgCO2e/FU (baseline)
        # 6 kg/FU x 1.0 kgCO2e/kg = 6 kgCO2e/FU (alternative) — alternative
        # wins despite a HIGHER per-kg factor, because its functional
        # quantity is lower. This is the exact worked example from ARQ-10.
        baseline_use = create_functional_use(
            self.org, self.reviewer, self.material, self.profile, Decimal("10"), "kg", "A",
        )
        approve_functional_use(baseline_use.pk, self.org, self.reviewer)
        other_material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-MATH-B", nombre="Material B",
            categoria="materiales", unidad_base="kg",
        )
        alt_use = create_functional_use(
            self.org, self.reviewer, other_material, self.profile, Decimal("6"), "kg", "B",
        )
        approve_functional_use(alt_use.pk, self.org, self.reviewer)

        baseline_version = self._version("0.8")
        alt_version = self._version("1.0")
        baseline_impact, _ = material_impact_per_functional_unit(baseline_use, baseline_version)
        alt_impact, _ = material_impact_per_functional_unit(alt_use, alt_version)
        self.assertEqual(baseline_impact, Decimal("8.0"))
        self.assertEqual(alt_impact, Decimal("6.0"))
        self.assertLess(alt_impact, baseline_impact)

    def test_zero_factor_gives_zero_impact(self):
        version = self._version("0")
        impact, error = material_impact_per_functional_unit(self.functional_use, version)
        self.assertIsNone(error)
        self.assertEqual(impact, Decimal("0"))

    def test_negative_factor_preserves_sign(self):
        version = self._version("-2.5")
        impact, error = material_impact_per_functional_unit(self.functional_use, version)
        self.assertIsNone(error)
        self.assertLess(impact, 0)

    def test_incompatible_unit_between_functional_use_and_factor(self):
        factor = FactorAmbiental.objects.create(
            organizacion=self.org, codigo="factor-incompat", nombre="Factor incompatible",
            categoria="materiales", unidad_entrada="L", unidad_resultado="kgCO2e",
        )
        version = VersionFactorAmbiental.objects.create(
            factor=factor, version=1, valor=Decimal("1"), fuente="test",
            estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        impact, error = material_impact_per_functional_unit(self.functional_use, version)
        self.assertIsNone(impact)
        self.assertIsNotNone(error)
