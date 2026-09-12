"""SOURCE-WATCH-01H — Operational API & Observability tests."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, SourceState
from .review_queue import open_review_item
from .services import sync_environmental_source

User = get_user_model()


class SourceWatchApiTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="api-source", nombre="API", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        self.run = sync_environmental_source(self.source)
        self.admin = User.objects.create_superuser("api-admin", "api-admin@example.com", "password")
        self.plain_user = User.objects.create_user("api-plain", "api-plain@example.com", "password")

    def _client(self, user=None):
        client = APIClient()
        if user is not None:
            client.force_login(user)
        return client

    def test_overview_requires_authentication(self):
        client = self._client()
        response = client.get("/api/knowledge/source-watch/overview/")
        # DRF's SessionAuthentication has no WWW-Authenticate challenge, so
        # an anonymous request is rejected with 403, not 401 — both equally
        # deny access; this matches DRF's documented default behavior.
        self.assertEqual(response.status_code, 403)

    def test_overview_authenticated(self):
        client = self._client(self.plain_user)
        response = client.get("/api/knowledge/source-watch/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("sources_total", response.json())

    def test_source_health_detail(self):
        client = self._client(self.plain_user)
        response = client.get(f"/api/knowledge/source-watch/sources/{self.source.codigo}/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["health_bucket"], "healthy")

    def test_source_run_changes(self):
        client = self._client(self.plain_user)
        response = client.get(
            f"/api/knowledge/source-watch/sources/{self.source.codigo}/sync-runs/{self.run.pk}/changes/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("classifications", response.json())

    def test_review_items_list_and_filters(self):
        open_review_item(self.run, {
            "external_id": "one", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
            "provenance": {"content_hash": "h1"},
        })
        client = self._client(self.plain_user)
        response = client.get("/api/knowledge/source-watch/review-items/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("results", body)
        self.assertEqual(len(body["results"]), 1)

        filtered = client.get("/api/knowledge/source-watch/review-items/?estado=resolved")
        self.assertEqual(len(filtered.json()["results"]), 0)

    def test_review_item_detail(self):
        item, _ = open_review_item(self.run, {
            "external_id": "one", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
            "provenance": {"content_hash": "h1"},
        })
        client = self._client(self.plain_user)
        response = client.get(f"/api/knowledge/source-watch/review-items/{item.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], item.pk)

    def test_non_superuser_cannot_acknowledge(self):
        item, _ = open_review_item(self.run, {
            "external_id": "one", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
            "provenance": {"content_hash": "h1"},
        })
        client = self._client(self.plain_user)
        response = client.post(f"/api/knowledge/source-watch/review-items/{item.pk}/acknowledge/")
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_acknowledge_and_resolve(self):
        item, _ = open_review_item(self.run, {
            "external_id": "one", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
            "provenance": {"content_hash": "h1"},
        })
        client = self._client(self.admin)
        ack = client.post(f"/api/knowledge/source-watch/review-items/{item.pk}/acknowledge/")
        self.assertEqual(ack.status_code, 200)
        self.assertEqual(ack.json()["estado"], "acknowledged")
        resolved = client.post(f"/api/knowledge/source-watch/review-items/{item.pk}/resolve/")
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["estado"], "resolved")

    def test_review_items_pagination_shape(self):
        for i in range(3):
            open_review_item(self.run, {
                "external_id": f"item-{i}", "domain": "generic", "classification": "changed_unknown_impact",
                "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
                "provenance": {"content_hash": f"hash-{i}"},
            })
        client = self._client(self.plain_user)
        response = client.get("/api/knowledge/source-watch/review-items/?page_size=2")
        body = response.json()
        self.assertEqual(len(body["results"]), 2)
        self.assertIn("next", body)

    def test_review_items_list_query_count_does_not_scale_with_rows(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        client = self._client(self.plain_user)
        open_review_item(self.run, {
            "external_id": "solo", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
            "provenance": {"content_hash": "hash-solo"},
        })
        with CaptureQueriesContext(connection) as one_item:
            client.get("/api/knowledge/source-watch/review-items/")

        for i in range(9):
            open_review_item(self.run, {
                "external_id": f"item-{i}", "domain": "generic", "classification": "changed_unknown_impact",
                "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
                "provenance": {"content_hash": f"hash-{i}"},
            })
        with CaptureQueriesContext(connection) as many_items:
            client.get("/api/knowledge/source-watch/review-items/")

        # select_related("source") + prefetch_related("decisiones") keep the
        # query count constant regardless of row count — no N+1.
        self.assertEqual(len(one_item.captured_queries), len(many_items.captured_queries))

    def test_error_does_not_leak_secret_via_run_changes(self):
        FakeEnvironmentalConnector.error = RuntimeError("Authorization Bearer secret-token")
        failed_run = sync_environmental_source(self.source)
        client = self._client(self.plain_user)
        response = client.get(
            f"/api/knowledge/source-watch/sources/{self.source.codigo}/sync-runs/{failed_run.pk}/changes/"
        )
        self.assertNotIn("secret-token", response.content.decode())
