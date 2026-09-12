"""MI-01D — Comparable Alternative Sets tests, built on real ÖKOBAUDAT
fixtures (labels "a1" and "a2") reused from MATERIAL-DATA so no new upstream
facts are invented. "a1" is EN 15804+A1 (unit m3, negative GWP); "a2" is
EN 15804+A2 (unit kg, positive GWP)."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import MaterialOperacional, Organizacion, UsuarioOrganizacion, VersionFactorAmbiental
from .services.factor_governance import transition_factor_version
from .services.material_application_profile import approve_profile, create_profile
from .services.material_candidates import (
    build_material_candidate,
    promote_material_candidate,
    review_material_candidate,
)
from .services.material_comparable_sets import comparable_alternatives, eligibility_chain
from .services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from .services.material_functional_use import approve_functional_use, create_functional_use
from .services.material_suitability import decide_human_approval, record_assessment
from .services.material_technical_property import approve_assertion, create_assertion
from .services.system_environmental_catalog import ensure_system_environmental_catalog
from .test_material_candidates import material_fixture

User = get_user_model()


class ComparableSetsTests(TestCase):
    def setUp(self):
        ensure_system_environmental_catalog()
        self.reviewer = User.objects.create_superuser(
            "mi01d-reviewer", "mi01d-reviewer@example.com", "password"
        )
        self.org = Organizacion.objects.create(nombre="MI-01D org")
        self.other_org = Organizacion.objects.create(nombre="MI-01D otro tenant")
        UsuarioOrganizacion.objects.create(
            user=self.reviewer, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN,
        )
        profile = create_profile(
            self.org, self.reviewer, "PERFIL-01D", "Perfil comparabilidad", Decimal("1"), "unidad",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}],
        )
        self.profile = approve_profile(profile.pk, self.org, self.reviewer)
        self._factor_cache = {}

    def _activated_factor(self, label):
        if label in self._factor_cache:
            return self._factor_cache[label]
        profile = material_fixture(label)
        candidate, _created, evaluation = build_material_candidate(profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, self.reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        version = transition_factor_version(version, "activo")
        self.assertEqual(version.estado, VersionFactorAmbiental.Estado.ACTIVO)
        self._factor_cache[label] = (factor, profile)
        return factor, profile

    def _eligible_material(self, label, codigo, *, org=None, unit=None):
        org = org or self.org
        factor, fixture_profile = self._activated_factor(label)
        unit = unit or ("kg" if label == "a2" else "m3")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo=codigo, nombre=f"Material {codigo}",
            categoria="materiales", unidad_base=unit,
        )
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.reviewer)
        approve_material_mapping(mapping.pk, org, self.reviewer)

        if org.pk == self.org.pk:
            assertion = create_assertion(
                org, self.reviewer, material, "cumple_norma", "boolean",
                "manual_professional_assertion", date(2026, 1, 1), value_boolean=True,
            )
            approve_assertion(assertion.pk, org, self.reviewer)
            assessment = record_assessment(org, self.reviewer, material, self.profile)
            decide_human_approval(assessment.pk, org, self.reviewer, approved=True)
            functional_use = create_functional_use(
                org, self.reviewer, material, self.profile, Decimal("1"), unit, "Justificación técnica",
            )
            approve_functional_use(functional_use.pk, org, self.reviewer)
        return material

    def test_same_standard_materials_are_comparable(self):
        source = self._eligible_material("a2", "MAT-A2-SRC")
        alt = self._eligible_material("a2", "MAT-A2-ALT")
        result = comparable_alternatives(self.org, source, self.profile, [alt])
        self.assertTrue(result["source_eligible"])
        self.assertEqual([c["material_id"] for c in result["comparable_candidates"]], [alt.pk])
        self.assertEqual(result["excluded_candidates"], [])

    def test_a1_a2_not_directly_comparable(self):
        source = self._eligible_material("a1", "MAT-A1-SRC")
        alt = self._eligible_material("a2", "MAT-A2-ALT2")
        result = comparable_alternatives(self.org, source, self.profile, [alt])
        self.assertTrue(result["source_eligible"])
        self.assertEqual(result["comparable_candidates"], [])
        self.assertEqual(len(result["excluded_candidates"]), 1)
        self.assertIn("standard_mismatch", result["excluded_candidates"][0]["reasons"])

    def test_missing_suitability_approval_excludes_candidate(self):
        source = self._eligible_material("a2", "MAT-A2-SRC2")
        factor, _ = self._activated_factor("a2")
        unapproved = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-NOSUIT", nombre="Sin suitability",
            categoria="materiales", unidad_base="kg",
        )
        mapping = propose_material_mapping(self.org, unapproved, factor, date(2026, 1, 1), None, self.reviewer)
        approve_material_mapping(mapping.pk, self.org, self.reviewer)
        # No assertion / assessment / functional use recorded for `unapproved`.
        result = comparable_alternatives(self.org, source, self.profile, [unapproved])
        self.assertEqual(result["comparable_candidates"], [])
        reasons = result["excluded_candidates"][0]["reasons"]
        self.assertIn("suitability_not_approved", reasons)
        self.assertIn("functional_use_not_approved", reasons)

    def test_missing_environmental_factor_excludes_candidate(self):
        source = self._eligible_material("a2", "MAT-A2-SRC3")
        no_factor_material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-NOFACTOR", nombre="Sin factor",
            categoria="materiales", unidad_base="kg",
        )
        result = comparable_alternatives(self.org, source, self.profile, [no_factor_material])
        self.assertIn(
            "environmental_factor_not_available",
            result["excluded_candidates"][0]["reasons"],
        )

    def test_ineligible_source_returns_no_comparable_candidates(self):
        ineligible_source = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-SRC-INELIG", nombre="Fuente sin datos",
            categoria="materiales", unidad_base="kg",
        )
        alt = self._eligible_material("a2", "MAT-A2-ALT3")
        result = comparable_alternatives(self.org, ineligible_source, self.profile, [alt])
        self.assertFalse(result["source_eligible"])
        self.assertEqual(result["comparable_candidates"], [])

    def test_cross_tenant_candidate_never_comparable(self):
        source = self._eligible_material("a2", "MAT-A2-SRC4")
        foreign = self._eligible_material("a2", "MAT-A2-FOREIGN", org=self.other_org)
        result = comparable_alternatives(self.org, source, self.profile, [foreign])
        self.assertEqual(result["comparable_candidates"], [])
        self.assertIn("different_organization", result["excluded_candidates"][0]["reasons"])

    def test_name_similarity_never_confers_comparability(self):
        # Two materials with near-identical names/codes but no governed chain
        # at all must never be comparable — comparability comes only from
        # the explicit chain, never from naming.
        source = self._eligible_material("a2", "HORMIGON-G30-A")
        lookalike = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="HORMIGON-G30-B", nombre="Hormigón G30",
            categoria="materiales", unidad_base="kg",
        )
        result = comparable_alternatives(self.org, source, self.profile, [lookalike])
        self.assertEqual(result["comparable_candidates"], [])

    def test_eligibility_chain_explicit_for_comparable_material(self):
        material = self._eligible_material("a2", "MAT-A2-CHAIN")
        chain, reasons = eligibility_chain(self.org, material, self.profile)
        self.assertIsNone(reasons)
        self.assertEqual(chain["material_id"], material.pk)
        self.assertEqual(chain["standard"], "A2")
