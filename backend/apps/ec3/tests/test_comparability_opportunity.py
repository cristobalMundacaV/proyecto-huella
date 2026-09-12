"""EC3-01 — comparability (capability 7) and opportunity preview (capability 8).

Mirrors test_governance.py's synthetic, offline-only fixture style. Never
asserts adoption/purchase viability; every comparison/opportunity result
must carry explicit, explainable reasons rather than a similarity guess.
"""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.analytics.models import MaterialOperacional, Organizacion, UsuarioOrganizacion
from apps.analytics.services.factor_governance import transition_factor_version
from apps.analytics.services.material_application_profile import approve_profile, create_profile
from apps.analytics.services.material_candidates import (
    build_material_candidate, promote_material_candidate, review_material_candidate,
)
from apps.analytics.services.material_comparable_sets import comparable_alternatives
from apps.analytics.services.material_factor_mapping import approve_material_mapping, propose_material_mapping
from apps.analytics.services.material_functional_use import approve_functional_use, create_functional_use
from apps.analytics.services.material_hotspots import material_hotspots
from apps.analytics.services.material_opportunities import detect_opportunities
from apps.analytics.services.material_suitability import decide_human_approval, record_assessment
from apps.analytics.services.material_technical_property import approve_assertion, create_assertion
from apps.analytics.services.system_environmental_catalog import ensure_system_environmental_catalog
from apps.analytics.test_material_candidates import material_fixture
from apps.ec3.client import Ec3Client
from apps.ec3.comparability import compare_epd_versions
from apps.ec3.models import Candidate
from apps.ec3.opportunity import compare_candidates, material_candidate_opportunities
from apps.ec3.services import ingest_epd, promote_candidate, propose_candidate, propose_mapping, review_candidate
from .fixtures import CONTEXT, SETTINGS, response, steel_payload


def _variant(*, mean=1800, **overrides):
    payload = steel_payload(mean=mean)
    payload.update(overrides)
    return payload


@override_settings(**SETTINGS)
class ComparabilityOpportunityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("ec3-compare", "ec3-compare@example.org", "test")
        self.org = Organizacion.objects.create(nombre="EC3 comparability synthetic")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="EC3-STEEL-CMP",
            nombre="Acero estructural sintético comparable", categoria="materiales", unidad_base="kg")
        self.session = Mock()
        self.session.get.return_value = response(steel_payload())
        self.client = Ec3Client(session=self.session, limiter=Mock(), sleep=Mock())
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def _ingest(self, epd_id, payload):
        self.session.get.return_value = response(payload)
        return ingest_epd(epd_id, self.user, client=self.client)

    def _mapped_candidate(self):
        version = self._ingest("ec3test1", steel_payload())
        candidate = propose_candidate(self.material, version, self.user)
        review_candidate(candidate.pk, self.user, "approved", "EF 3.0", CONTEXT)
        promote_candidate(candidate.pk, self.user)
        candidate.refresh_from_db()
        for state in ("pruebas", "validado", "activo"):
            transition_factor_version(candidate.promoted_version, state)
        candidate = propose_mapping(candidate.pk, self.user, date(2020, 1, 1))
        approve_material_mapping(candidate.mapping_id, self.org, self.user, "Synthetic mapping approval")
        candidate.refresh_from_db()
        return candidate

    # -- comparability --------------------------------------------------

    def test_identical_category_unit_geography_scope_method_is_comparable(self):
        version_a = self._ingest("ec3test1", steel_payload())
        version_b = self._ingest("ec3test2", _variant(id="ec3test2"))
        result = compare_epd_versions(version_a, version_b, "EF 3.0")
        self.assertEqual(result["result"], "COMPARABLE")
        self.assertEqual(result["reasons"], [])

    def test_category_mismatch_is_not_comparable_with_explicit_reason(self):
        version_a = self._ingest("ec3test1", steel_payload())
        version_b = self._ingest("ec3test2", _variant(id="ec3test2", ec3={"category": "Concrete", "product_specific": True}))
        result = compare_epd_versions(version_a, version_b, "EF 3.0")
        self.assertEqual(result["result"], "NOT_COMPARABLE")
        self.assertIn("category_mismatch", result["reasons"])

    def test_disjoint_geography_is_not_comparable(self):
        version_a = self._ingest("ec3test1", steel_payload())
        version_b = self._ingest("ec3test2", _variant(id="ec3test2", applicable_in=["US"]))
        result = compare_epd_versions(version_a, version_b, "EF 3.0")
        self.assertEqual(result["result"], "NOT_COMPARABLE")
        self.assertIn("geography_disjoint", result["reasons"])

    def test_pcr_mismatch_alone_is_partially_comparable(self):
        version_a = self._ingest("ec3test1", steel_payload())
        version_b = self._ingest("ec3test2", _variant(id="ec3test2", pcr={"id": "https://example.org/other-pcr", "name": "Other PCR"}))
        result = compare_epd_versions(version_a, version_b, "EF 3.0")
        self.assertEqual(result["result"], "PARTIALLY_COMPARABLE")
        self.assertEqual(result["reasons"], ["pcr_mismatch"])

    def test_ineligible_epd_is_review_required_not_a_guess(self):
        version_a = self._ingest("ec3test1", steel_payload())
        expired = _variant(id="ec3test2", valid_until="2020-01-02T00:00:00Z")
        version_b = self._ingest("ec3test2", expired)
        result = compare_epd_versions(version_a, version_b, "EF 3.0")
        self.assertEqual(result["result"], "REVIEW_REQUIRED")
        self.assertIn("epd_b_not_eligible", result["reasons"])

    # -- opportunity preview ----------------------------------------------

    def test_no_candidates_yields_empty_preview(self):
        preview = material_candidate_opportunities(self.org, self.material, "EF 3.0")
        self.assertEqual(preview["candidates"], [])
        self.assertIsNone(preview["baseline_value_per_unit"])

    def test_ineligible_candidate_reports_reasons_without_reduction(self):
        payload = steel_payload()
        payload.pop("pcr")
        version = self._ingest("ec3test1", payload)
        propose_candidate(self.material, version, self.user)
        preview = material_candidate_opportunities(self.org, self.material, "EF 3.0")
        self.assertEqual(len(preview["candidates"]), 1)
        entry = preview["candidates"][0]
        self.assertFalse(entry["eligible"])
        self.assertIn("missing_pcr", entry["eligibility_reasons"])
        self.assertIsNone(entry["potential_reduction_per_baseline_unit"])
        self.assertTrue(entry["requires_human_review"])

    def test_eligible_candidate_without_baseline_reports_no_active_baseline(self):
        version = self._ingest("ec3test1", steel_payload())
        propose_candidate(self.material, version, self.user)
        preview = material_candidate_opportunities(self.org, self.material, "EF 3.0")
        entry = preview["candidates"][0]
        self.assertTrue(entry["eligible"])
        self.assertIsNone(entry["potential_reduction_per_baseline_unit"])
        self.assertIn("no_active_baseline_factor", entry["comparison_reasons"])

    def test_cheaper_candidate_reports_positive_potential_reduction_against_mapped_baseline(self):
        self._mapped_candidate()  # baseline: mean=1800 kgCO2e / 1000 kg
        cheaper = self._ingest("ec3test2", _variant(id="ec3test2", program_operator_doc_id="OTHER-001", mean=900))
        propose_candidate(self.material, cheaper, self.user)
        preview = material_candidate_opportunities(self.org, self.material, "EF 3.0")
        # Only the not-yet-applied candidate is previewed — the mapped one is excluded.
        self.assertEqual(len(preview["candidates"]), 1)
        entry = preview["candidates"][0]
        self.assertEqual(entry["direction"], "lower")
        self.assertGreater(Decimal(entry["potential_reduction_per_baseline_unit"]), 0)

    def test_mapped_candidate_itself_is_excluded_from_preview(self):
        self._mapped_candidate()
        preview = material_candidate_opportunities(self.org, self.material, "EF 3.0")
        self.assertEqual(preview["candidates"], [])

    def test_different_organization_is_rejected(self):
        other_org = Organizacion.objects.create(nombre="Other org")
        result = material_candidate_opportunities(other_org, self.material, "EF 3.0")
        self.assertEqual(result["reason"], "different_organization")

    # -- compare_candidates service ---------------------------------------

    def test_compare_candidates_reports_potential_difference_when_comparable(self):
        version_a = self._ingest("ec3test1", steel_payload())
        version_b = self._ingest("ec3test2", _variant(id="ec3test2", program_operator_doc_id="OTHER-001", mean=900))
        candidate_a = propose_candidate(self.material, version_a, self.user)
        candidate_b = propose_candidate(self.material, version_b, self.user)
        result = compare_candidates(candidate_a, candidate_b, "EF 3.0")
        self.assertEqual(result["comparability"], "COMPARABLE")
        self.assertIsNotNone(result["potential_difference"])
        self.assertTrue(result["requires_human_review"])

    def test_compare_candidates_not_comparable_has_no_difference(self):
        version_a = self._ingest("ec3test1", steel_payload())
        version_b = self._ingest("ec3test2", _variant(id="ec3test2", ec3={"category": "Concrete", "product_specific": True}))
        candidate_a = propose_candidate(self.material, version_a, self.user)
        candidate_b = propose_candidate(self.material, version_b, self.user)
        result = compare_candidates(candidate_a, candidate_b, "EF 3.0")
        self.assertEqual(result["comparability"], "NOT_COMPARABLE")
        self.assertIsNone(result["potential_difference"])


@override_settings(**SETTINGS)
class CrossSourceReuseTests(TestCase):
    """Proves an EC3-mapped material participates in MI's EXISTING,
    unmodified `material_comparable_sets.comparable_alternatives` —
    capabilities 7/8 REUSE, not a parallel EC3-specific engine. This test
    is what surfaced a real gap this session fixed: `ec3.reporting.
    factor_quality` never populated a `standard` (EN 15804 generation)
    field, so `eligibility_chain` always reported `standard_unknown` for
    every EC3-mapped material, no matter how correctly it was reviewed,
    promoted and mapped — permanently excluding it from comparison
    against an ÖKOBAUDAT-mapped alternative of the same real generation."""

    def setUp(self):
        ensure_system_environmental_catalog()
        self.user = get_user_model().objects.create_superuser("ec3-reuse", "ec3-reuse@example.org", "test")
        self.org = Organizacion.objects.create(nombre="EC3 cross-source reuse synthetic")
        UsuarioOrganizacion.objects.create(user=self.user, organizacion=self.org, rol=UsuarioOrganizacion.Rol.ADMIN)
        profile = create_profile(self.org, self.user, "PERFIL-EC3-REUSE", "Perfil EC3 reuse", Decimal("1"), "kg",
            requisitos=[{"key": "cumple_norma", "type": "boolean", "operator": "is_true"}])
        self.profile = approve_profile(profile.pk, self.org, self.user)

    def _approve_use(self, material):
        assertion = create_assertion(self.org, self.user, material, "cumple_norma", "boolean",
            "manual_professional_assertion", date(2026, 1, 1), value_boolean=True)
        approve_assertion(assertion.pk, self.org, self.user)
        assessment = record_assessment(self.org, self.user, material, self.profile)
        decide_human_approval(assessment.pk, self.org, self.user, approved=True)
        functional_use = create_functional_use(self.org, self.user, material, self.profile, Decimal("1"), "kg",
            "Justificación técnica")
        approve_functional_use(functional_use.pk, self.org, self.user)

    def test_ec3_mapped_material_is_no_longer_standard_unknown_and_is_comparable(self):
        session = Mock()
        session.get.return_value = response(steel_payload())
        client = Ec3Client(session=session, limiter=Mock(), sleep=Mock())
        ec3_material = MaterialOperacional.objects.create(organizacion=self.org, codigo="EC3-REUSE-STEEL",
            nombre="Acero EC3 reuse", categoria="materiales", unidad_base="kg")
        version = ingest_epd("ec3test1", self.user, client=client)
        candidate = propose_candidate(ec3_material, version, self.user)
        review_candidate(candidate.pk, self.user, "approved", "EF 3.0", CONTEXT)
        promote_candidate(candidate.pk, self.user)
        candidate.refresh_from_db()
        for state in ("pruebas", "validado", "activo"):
            transition_factor_version(candidate.promoted_version, state)
        candidate = propose_mapping(candidate.pk, self.user, date(2020, 1, 1))
        approve_material_mapping(candidate.mapping_id, self.org, self.user, "Synthetic reuse mapping")
        self._approve_use(ec3_material)

        okobaudat_profile = material_fixture("a2")
        okobaudat_candidate, _created, evaluation = build_material_candidate(okobaudat_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(okobaudat_candidate.pk, self.user, "approved")
        okobaudat_factor, okobaudat_version = promote_material_candidate(okobaudat_candidate.pk, self.user)
        transition_factor_version(okobaudat_version, "pruebas")
        transition_factor_version(okobaudat_version, "validado")
        transition_factor_version(okobaudat_version, "activo")
        okobaudat_material = MaterialOperacional.objects.create(organizacion=self.org, codigo="OKB-REUSE-A2",
            nombre="ÖKOBAUDAT reuse a2", categoria="materiales", unidad_base="kg")
        okobaudat_mapping = propose_material_mapping(self.org, okobaudat_material, okobaudat_factor,
            date(2020, 1, 1), None, self.user)
        approve_material_mapping(okobaudat_mapping.pk, self.org, self.user)
        self._approve_use(okobaudat_material)

        result = comparable_alternatives(self.org, ec3_material, self.profile, [okobaudat_material])
        self.assertTrue(result["source_eligible"], result.get("source_exclusion_reasons"))
        self.assertEqual(result["source_chain"]["standard"], "A2")
        self.assertEqual([c["material_id"] for c in result["comparable_candidates"]], [okobaudat_material.pk])
        self.assertEqual(result["excluded_candidates"], [])


@override_settings(**SETTINGS)
class ComparabilityOpportunityApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("ec3-api-cmp", "ec3-api-cmp@example.org", "test")
        self.plain_user = get_user_model().objects.create_user("ec3-plain-cmp", "ec3-plain-cmp@example.org", "test")
        self.org = Organizacion.objects.create(nombre="EC3 API comparability synthetic")
        self.material = MaterialOperacional.objects.create(organizacion=self.org, codigo="EC3-STEEL-API",
            nombre="Acero API sintético", categoria="materiales", unidad_base="kg")
        self.session = Mock()
        self.session.get.return_value = response(steel_payload())
        self.client_obj = Ec3Client(session=self.session, limiter=Mock(), sleep=Mock())
        version = ingest_epd("ec3test1", self.user, client=self.client_obj)
        self.candidate = propose_candidate(self.material, version, self.user)
        self.api = APIClient()

    def test_eligibility_endpoint_requires_superuser(self):
        url = f"/api/integrations/ec3/candidates/{self.candidate.pk}/eligibility/?lcia_method=EF+3.0"
        self.assertEqual(self.api.get(url).status_code, 403)
        self.api.force_authenticate(self.plain_user)
        self.assertEqual(self.api.get(url).status_code, 403)
        self.api.force_authenticate(self.user)
        result = self.api.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["compatible"])

    def test_versions_endpoint_lists_local_versions(self):
        self.api.force_authenticate(self.user)
        result = self.api.get("/api/integrations/ec3/epds/ec3test1/versions/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data["versions"]), 1)

    def test_versions_endpoint_unknown_epd_is_404(self):
        self.api.force_authenticate(self.user)
        result = self.api.get("/api/integrations/ec3/epds/zzzzzzzz/versions/")
        self.assertEqual(result.status_code, 404)

    def test_material_opportunities_endpoint_enforces_tenant_permission(self):
        self.api.force_authenticate(self.plain_user)
        url = f"/api/integrations/ec3/materials/{self.material.pk}/opportunities/?lcia_method=EF+3.0"
        self.assertEqual(self.api.get(url).status_code, 403)
        self.api.force_authenticate(self.user)
        result = self.api.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertIn("candidates", result.data)
