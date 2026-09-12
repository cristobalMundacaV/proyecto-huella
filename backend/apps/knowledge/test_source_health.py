"""SOURCE-WATCH-01B — Source Health & Freshness Authority tests."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, ExternalRecord, SourceState
from .services import sync_environmental_source
from .source_health import source_health


class SourceHealthTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="health-source", nombre="Health", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(
            records=[ConnectorRecord("one", "generic", payload={"a": 1}, title="One")]
        )

    def test_never_synced(self):
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "never_synced")
        self.assertFalse(health["last_known_good_available"])

    def test_healthy_after_successful_sync(self):
        sync_environmental_source(self.source)
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "healthy")
        self.assertTrue(health["last_known_good_available"])
        self.assertIsNotNone(health["last_run_summary"])
        self.assertEqual(health["last_run_summary"]["created"], 1)

    def test_near_stale_and_stale_boundaries(self):
        sync_environmental_source(self.source)
        state = self.source.sync_state
        state.refresh_from_db()
        state.last_successful_sync_at = timezone.now() - timedelta(hours=9)
        state.estado = "actualizada"
        state.save()
        self.assertEqual(source_health(self.source)["health_bucket"], "near_stale")

        state.last_successful_sync_at = timezone.now() - timedelta(hours=11)
        state.save()
        self.assertEqual(source_health(self.source)["health_bucket"], "stale")

    def test_error_with_last_version_preserves_last_known_good(self):
        sync_environmental_source(self.source)
        FakeEnvironmentalConnector.error = RuntimeError("Authorization Bearer secret-token")
        sync_environmental_source(self.source)
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "error_with_last_version")
        self.assertTrue(health["last_known_good_available"])
        self.assertNotIn("secret-token", health["last_error"])
        # The previously synced record must still be reachable.
        self.assertEqual(ExternalRecord.objects.filter(source=self.source).count(), 1)

    def test_error_without_last_version(self):
        FakeEnvironmentalConnector.error = RuntimeError("fallo inicial")
        sync_environmental_source(self.source)
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "error_without_version")
        self.assertFalse(health["last_known_good_available"])

    def test_syncing_state(self):
        SourceState.objects.filter(source=self.source).update(estado="sincronizando")
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "syncing")

    def test_inactive_source(self):
        self.source.activa = False
        self.source.save(update_fields=["activa"])
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "inactive")

    def test_timezone_correctness_of_age(self):
        sync_environmental_source(self.source)
        health = source_health(self.source)
        self.assertIsNotNone(health["age_seconds"])
        self.assertGreaterEqual(health["age_seconds"], 0)
        self.assertIsNotNone(health["next_freshness_boundary"])
        self.assertTrue(timezone.is_aware(health["next_freshness_boundary"]))

    def test_partial_with_and_without_version(self):
        state = self.source.sync_state
        state.estado = "parcial"
        state.save()
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "partial_without_version")

        sync_environmental_source(self.source)
        state.refresh_from_db()
        state.estado = "parcial"
        state.save()
        health = source_health(self.source)
        self.assertEqual(health["health_bucket"], "partial_with_last_version")
