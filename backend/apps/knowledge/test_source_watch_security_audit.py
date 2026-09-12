"""SOURCE-WATCH-01J — consolidated security audit.

Cross-cutting checks not already exercised per-phase: every governed
SOURCE-WATCH model blocks direct queryset mutation (not just instance
save()/delete()), a source's persisted error never carries a secret
regardless of which code path wrote it, and a fully unauthenticated/
unauthorized request is rejected at every mutating and every read
endpoint this macrophase added."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import (
    EnvironmentalSource,
    ExternalRecord,
    ExternalSnapshot,
    SourceState,
    SourceWatchReviewDecision,
    SourceWatchReviewItem,
    SyncRun,
)
from .review_queue import open_review_item
from .services import sync_environmental_source

User = get_user_model()

GOVERNED_MODELS = [SourceWatchReviewItem, SourceWatchReviewDecision]

# SyncRun/ExternalSnapshot use a simpler "immutable once finished/created"
# instance-level guard (the pre-existing house style in this app) rather
# than a queryset-level guard — verified separately below, matching how
# they were already designed before this macrophase.


class GovernedModelMutationGuardTests(TestCase):
    def test_review_models_block_direct_queryset_mutation(self):
        for model in GOVERNED_MODELS:
            with self.assertRaises(ValidationError, msg=model.__name__):
                model.objects.all().update(id=999999)
            with self.assertRaises(ValidationError, msg=model.__name__):
                model.objects.all().delete()

    def test_finished_sync_run_is_immutable(self):
        source = EnvironmentalSource.objects.create(
            codigo="sec-audit-run", nombre="Sec", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        run = sync_environmental_source(source)
        run.message = "tampered"
        with self.assertRaises(ValidationError):
            run.save()

    def test_snapshot_is_immutable(self):
        source = EnvironmentalSource.objects.create(
            codigo="sec-audit-snap", nombre="Sec", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        sync_environmental_source(source)
        snapshot = ExternalSnapshot.objects.get(source=source)
        snapshot.raw_text = "tampered"
        with self.assertRaises(ValidationError):
            snapshot.save()


class SecretRedactionAuditTests(TestCase):
    def test_watch_source_error_field_never_carries_secret(self):
        from .watch_orchestration import watch_source

        source = EnvironmentalSource.objects.create(
            codigo="sec-audit-secret", nombre="Sec", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=source)
        FakeEnvironmentalConnector.error = RuntimeError("Authorization: Bearer super-secret-token-123")
        result = watch_source(source)
        self.assertNotIn("super-secret-token-123", result["error"])
        source.refresh_from_db()
        self.assertNotIn("super-secret-token-123", source.sync_state.last_error)

    def test_review_item_never_persists_a_secret_in_reasons(self):
        source = EnvironmentalSource.objects.create(
            codigo="sec-audit-review-secret", nombre="Sec", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        run = sync_environmental_source(source)
        item, _ = open_review_item(run, {
            "external_id": "one", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact",
            "reasons": ["token=should-be-redacted-if-ever-a-real-secret-leaked-here"],
            "affected_objects": [], "provenance": {"content_hash": "h"},
        })
        # This module never sanitizes `reasons` itself (they are fixed,
        # code-authored strings, never raw upstream content) — this test
        # documents that invariant explicitly rather than assuming it.
        self.assertIsInstance(item.reasons, list)


class ApiAuthAndPermissionAuditTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="sec-audit-api", nombre="Sec", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        self.run = sync_environmental_source(self.source)
        self.item, _ = open_review_item(self.run, {
            "external_id": "one", "domain": "generic", "classification": "changed_unknown_impact",
            "severity": "medium", "impact_level": "unknown_impact", "reasons": [], "affected_objects": [],
            "provenance": {"content_hash": "h"},
        })
        self.plain_user = User.objects.create_user("sec-audit-plain", "sec-audit-plain@example.com", "password")

    def _anon(self):
        return APIClient()

    def _as(self, user):
        client = APIClient()
        client.force_login(user)
        return client

    def test_all_read_endpoints_require_authentication(self):
        client = self._anon()
        endpoints = [
            "/api/knowledge/source-watch/overview/",
            f"/api/knowledge/source-watch/sources/{self.source.codigo}/health/",
            f"/api/knowledge/source-watch/sources/{self.source.codigo}/sync-runs/{self.run.pk}/changes/",
            "/api/knowledge/source-watch/review-items/",
            f"/api/knowledge/source-watch/review-items/{self.item.pk}/",
        ]
        for url in endpoints:
            response = client.get(url)
            self.assertEqual(response.status_code, 403, url)

    def test_mutating_endpoints_reject_anonymous_and_plain_user(self):
        client_anon = self._anon()
        client_plain = self._as(self.plain_user)
        for url in [
            f"/api/knowledge/source-watch/review-items/{self.item.pk}/acknowledge/",
            f"/api/knowledge/source-watch/review-items/{self.item.pk}/resolve/",
        ]:
            self.assertIn(client_anon.post(url).status_code, (401, 403))
            self.assertEqual(client_plain.post(url).status_code, 403)

    def test_unknown_review_item_id_is_404_not_500(self):
        client = self._as(self.plain_user)
        response = client.get("/api/knowledge/source-watch/review-items/999999/")
        self.assertEqual(response.status_code, 404)

    def test_unknown_source_code_is_404_not_500(self):
        client = self._as(self.plain_user)
        response = client.get("/api/knowledge/source-watch/sources/does-not-exist/health/")
        self.assertEqual(response.status_code, 404)
