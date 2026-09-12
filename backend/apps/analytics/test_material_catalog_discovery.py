from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Organizacion, UsuarioOrganizacion, MaterialOperacional
from .services.material_candidates import (build_material_candidate,
                                            promote_material_candidate,
                                            review_material_candidate)
from .services.material_factor_mapping import (approve_material_mapping,
                                                propose_material_mapping)
from .test_material_candidates import material_fixture

User = get_user_model()


class MaterialCatalogDiscoveryTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            "discovery-admin", "discovery-admin@example.com", "password"
        )
        self.plain_user = User.objects.create_user("discovery-plain", password="test-pass")
        self.org = Organizacion.objects.create(nombre="Discovery tenant")
        UsuarioOrganizacion.objects.create(user=self.plain_user, organizacion=self.org)

    def candidate_for(self, label):
        return build_material_candidate(material_fixture(label).pk)[0]

    def test_any_authenticated_user_can_search_no_superuser_required(self):
        self.candidate_for("a2")
        self.client.force_login(self.plain_user)
        response = self.client.get("/api/catalogo-material/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)

    def test_search_by_name_substring(self):
        candidate = self.candidate_for("a2")
        self.client.force_login(self.plain_user)
        term = candidate.source_profile.process.name[:6]
        response = self.client.get(f"/api/catalogo-material/?q={term}")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)

    def test_filter_by_standard(self):
        self.candidate_for("a1")
        self.candidate_for("a2")
        self.client.force_login(self.plain_user)
        response = self.client.get(f"/api/catalogo-material/?standard={quote('EN 15804+A1')}")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        for row in results:
            self.assertEqual(row["calidad"]["known"]["standard"], "EN 15804+A1")

    def test_never_ranks_or_scores_results(self):
        self.candidate_for("a2")
        self.client.force_login(self.plain_user)
        response = self.client.get("/api/catalogo-material/")
        results = response.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        for row in results:
            self.assertNotIn("score", row)
            self.assertNotIn("ranking", row)
            self.assertNotIn("alternativas", row)

    def test_quality_filter(self):
        self.candidate_for("a1")
        self.client.force_login(self.plain_user)
        response = self.client.get("/api/catalogo-material/?calidad=requires_review")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertGreaterEqual(len(results), 1)
        for row in results:
            self.assertEqual(row["calidad"]["estado"], "requires_review")

    def test_search_results_are_paginated(self):
        self.candidate_for("a2")
        self.client.force_login(self.plain_user)
        response = self.client.get("/api/catalogo-material/")
        payload = response.json()
        self.assertIn("results", payload)
        self.assertIn("count", payload)

    def test_detail_walks_process_profile_indicators_and_candidate(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        self.client.force_login(self.plain_user)
        response = self.client.get(f"/api/catalogo-material/{candidate.pk}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["process"]["process_uuid"], str(profile.process_uuid))
        self.assertGreaterEqual(len(payload["indicators"]), 1)
        self.assertIsNone(payload["promoted_factor"])

    def test_detail_shows_promoted_factor_when_promoted(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        review_material_candidate(candidate.pk, self.superuser, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.superuser)
        self.client.force_login(self.plain_user)
        response = self.client.get(f"/api/catalogo-material/{candidate.pk}/")
        payload = response.json()
        self.assertEqual(payload["promoted_factor"]["id"], factor.id)
        self.assertEqual(payload["promoted_factor"]["estado_version"], "borrador")

    def test_mapping_visibility_scoped_to_requester_tenant(self):
        profile = material_fixture("a2")
        candidate = build_material_candidate(profile.pk)[0]
        review_material_candidate(candidate.pk, self.superuser, "approved")
        factor, version = promote_material_candidate(candidate.pk, self.superuser)

        material = MaterialOperacional.objects.create(
            organizacion=self.org, codigo="MAT-DISC", nombre="Material", categoria="cemento", unidad_base="kg",
        )
        from datetime import date
        mapping = propose_material_mapping(self.org, material, factor, date(2026, 1, 1), None, self.superuser)
        approve_material_mapping(mapping.pk, self.org, self.superuser)

        other_org = Organizacion.objects.create(nombre="Discovery otro tenant")
        other_user = User.objects.create_user("discovery-other", password="test-pass")
        UsuarioOrganizacion.objects.create(user=other_user, organizacion=other_org)

        self.client.force_login(self.plain_user)
        visible = self.client.get(f"/api/catalogo-material/{candidate.pk}/")
        self.assertEqual(len(visible.json()["mappings"]), 1)

        self.client.force_login(other_user)
        hidden = self.client.get(f"/api/catalogo-material/{candidate.pk}/")
        self.assertEqual(len(hidden.json()["mappings"]), 0)

        self.client.force_login(self.superuser)
        superuser_view = self.client.get(f"/api/catalogo-material/{candidate.pk}/")
        self.assertEqual(len(superuser_view.json()["mappings"]), 1)

    def test_unauthenticated_request_rejected(self):
        material_fixture("a2")
        response = self.client.get("/api/catalogo-material/")
        self.assertIn(response.status_code, (401, 403))

    def test_query_count_stays_bounded_on_list_page(self):
        self.candidate_for("a2")
        self.candidate_for("a1")
        self.client.force_login(self.plain_user)
        # Bounded and independent of result-set size: no N+1 per row from
        # select_related, and the quality assessment is computed purely from
        # already-fetched JSON fields (no extra queries per candidate).
        with self.assertNumQueries(4):
            self.client.get("/api/catalogo-material/")
