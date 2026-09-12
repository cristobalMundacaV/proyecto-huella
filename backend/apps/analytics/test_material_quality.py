from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import FactorAmbiental, MaterialOperacional, Organizacion, VersionFactorAmbiental
from .services.material_candidates import (build_material_candidate,
                                            promote_material_candidate,
                                            review_material_candidate)
from .services.material_factor_mapping import (approve_material_mapping,
                                                propose_material_mapping)
from .services.material_quality import (INSUFFICIENT, REQUIRES_REVIEW,
                                        SUFFICIENT, assess_factor_data_quality,
                                        assess_material_data_quality)
from .test_material_candidates import material_fixture

User = get_user_model()


class MaterialQualityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("quality-admin", "quality-admin@example.com", "password")

    def candidate(self, label="a2"):
        profile = material_fixture(label)
        return build_material_candidate(profile.pk)[0]

    def test_a2_candidate_is_sufficient_or_requires_review_but_never_insufficient(self):
        candidate = self.candidate("a2")
        result = assess_material_data_quality(candidate)
        self.assertIn(result["estado"], {SUFFICIENT, REQUIRES_REVIEW})
        self.assertEqual(result["known"]["standard"], "EN 15804+A2")
        self.assertTrue(result["known"]["gwp_available"])

    def test_a1_candidate_flags_legacy_standard_warning(self):
        candidate = self.candidate("a1")
        result = assess_material_data_quality(candidate)
        self.assertIn("legacy_a1_standard", result["warnings"])
        self.assertEqual(result["estado"], REQUIRES_REVIEW)

    def test_incompatible_candidate_is_insufficient_and_reuses_01c_reasons(self):
        candidate = self.candidate("a2")
        candidate.functional_context = {**candidate.functional_context}
        broken_eligibility = {"compatible": False, "source_current": True, "reasons": ["missing_gwp"]}
        candidate.initial_eligibility = broken_eligibility
        result = assess_material_data_quality(candidate)
        self.assertEqual(result["estado"], INSUFFICIENT)
        self.assertEqual(result["reasons"], ["missing_gwp"])
        self.assertEqual(result["warnings"], [])

    def test_unknown_metadata_surfaces_as_unknown_not_guessed(self):
        candidate = self.candidate("a2")
        candidate.functional_context = {
            **candidate.functional_context,
            "owner_manufacturer": "unknown",
            "location": "unknown",
        }
        result = assess_material_data_quality(candidate)
        self.assertIn("owner_manufacturer", result["unknown"])
        self.assertIn("location", result["unknown"])
        for field in ("owner_manufacturer", "location"):
            self.assertIn(result["known"][field], (None, "unknown", ""))

    def test_private_factor_has_no_okobaudat_origin(self):
        org = Organizacion.objects.create(nombre="Calidad privada")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo="MAT-PRIV", nombre="Material privado", categoria="otro", unidad_base="kg",
        )
        factor = FactorAmbiental.objects.create(
            organizacion=org, codigo="factor-privado", nombre="Privado", categoria="materiales",
            unidad_entrada="kg", unidad_resultado="kgCO2e",
        )
        result = assess_factor_data_quality(factor)
        self.assertEqual(result["estado"], REQUIRES_REVIEW)
        self.assertIn("sin_origen_okobaudat", result["warnings"])

    def test_promoted_factor_resolves_back_to_its_candidate_quality(self):
        candidate = self.candidate("a2")
        review_material_candidate(candidate.pk, self.user, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.user)
        result = assess_factor_data_quality(factor)
        self.assertEqual(result, assess_material_data_quality(candidate))

    def test_quality_is_reconstructible_after_mapping_lifecycle(self):
        """Quality verdict must not depend on later mapping/version events."""
        candidate = self.candidate("a2")
        review_material_candidate(candidate.pk, self.user, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.user)
        before = assess_factor_data_quality(factor)

        org = Organizacion.objects.create(nombre="Calidad reconstruccion")
        material = MaterialOperacional.objects.create(
            organizacion=org, codigo="MAT-RECON", nombre="Reconstruccion", categoria="cemento", unidad_base="kg",
        )
        from datetime import date
        mapping = propose_material_mapping(org, material, factor, date(2026, 1, 1), None, self.user)
        approve_material_mapping(mapping.pk, org, self.user)

        after = assess_factor_data_quality(factor)
        self.assertEqual(before, after)


class MaterialQualityApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("quality-api-admin", "quality-api-admin@example.com", "password")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_quality_endpoint_requires_superuser(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        anon = APIClient()
        response = anon.get(f"/api/environmental-governance/material-factor-candidates/{candidate.pk}/calidad/")
        self.assertEqual(response.status_code, 403)

    def test_quality_endpoint_returns_assessment(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        response = self.client.get(f"/api/environmental-governance/material-factor-candidates/{candidate.pk}/calidad/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()["estado"], {SUFFICIENT, REQUIRES_REVIEW, INSUFFICIENT})
