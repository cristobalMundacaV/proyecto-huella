"""SOURCE-WATCH-01C — Normalized Change Observation tests."""

from django.test import TestCase

from .change_observation import CHANGED, CREATED, DISAPPEARED, REAPPEARED, UNCHANGED, observe_sync_run
from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, SourceState
from .services import sync_environmental_source


class ChangeObservationTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="change-source", nombre="Change", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None

    def _set_batch(self, records, authoritative=True):
        FakeEnvironmentalConnector.batch = ConnectorBatch(
            records=records, authoritative_full_snapshot=authoritative,
        )

    def test_created_event(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1}, title="One")])
        run = sync_environmental_source(self.source)
        observation = observe_sync_run(run)
        self.assertEqual(len(observation["events"]), 1)
        self.assertEqual(observation["events"][0]["classification"], CREATED)
        self.assertEqual(observation["events"][0]["external_id"], "one")

    def test_changed_event(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1}, title="One")])
        sync_environmental_source(self.source)
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 2}, title="One")])
        run = sync_environmental_source(self.source)
        observation = observe_sync_run(run)
        self.assertEqual(len(observation["events"]), 1)
        self.assertEqual(observation["events"][0]["classification"], CHANGED)

    def test_unchanged_event(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1}, title="One")])
        sync_environmental_source(self.source)
        run = sync_environmental_source(self.source)
        observation = observe_sync_run(run)
        self.assertEqual(len(observation["events"]), 1)
        self.assertEqual(observation["events"][0]["classification"], UNCHANGED)

    def test_disappearance_with_authoritative_snapshot(self):
        self._set_batch([
            ConnectorRecord("one", "generic", payload={"a": 1}),
            ConnectorRecord("two", "generic", payload={"a": 2}),
        ], authoritative=True)
        sync_environmental_source(self.source)
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})], authoritative=True)
        run = sync_environmental_source(self.source)
        observation = observe_sync_run(run)
        disappeared = [e for e in observation["events"] if e["classification"] == DISAPPEARED]
        self.assertEqual(len(disappeared), 1)
        self.assertEqual(disappeared[0]["external_id"], "two")

    def test_no_false_disappearance_for_incremental_source(self):
        self._set_batch([
            ConnectorRecord("one", "generic", payload={"a": 1}),
            ConnectorRecord("two", "generic", payload={"a": 2}),
        ], authoritative=True)
        sync_environmental_source(self.source)
        # A non-authoritative (partial/incremental) batch omitting "two"
        # must never mark it disappeared.
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})], authoritative=False)
        run = sync_environmental_source(self.source)
        observation = observe_sync_run(run)
        self.assertFalse(observation["authoritative"])
        disappeared = [e for e in observation["events"] if e["classification"] == DISAPPEARED]
        self.assertEqual(disappeared, [])
        from .models import ExternalRecord

        self.assertEqual(
            ExternalRecord.objects.get(source=self.source, external_id="two").estado,
            ExternalRecord.Status.ACTIVE,
        )

    def test_reappearance(self):
        self._set_batch([
            ConnectorRecord("one", "generic", payload={"a": 1}),
            ConnectorRecord("two", "generic", payload={"a": 2}),
        ], authoritative=True)
        sync_environmental_source(self.source)
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})], authoritative=True)
        sync_environmental_source(self.source)  # "two" disappears here

        self._set_batch([
            ConnectorRecord("one", "generic", payload={"a": 1}),
            ConnectorRecord("two", "generic", payload={"a": 2}),
        ], authoritative=True)
        run = sync_environmental_source(self.source)
        observation = observe_sync_run(run)
        reappeared = [e for e in observation["events"] if e["classification"] == REAPPEARED]
        self.assertEqual(len(reappeared), 1)
        self.assertEqual(reappeared[0]["external_id"], "two")

    def test_idempotent_reanalysis_of_same_run(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})])
        run = sync_environmental_source(self.source)
        first = observe_sync_run(run)
        second = observe_sync_run(run)
        self.assertEqual(first["events"], second["events"])

    def test_unfinished_run_reports_unknown(self):
        SourceState.objects.filter(source=self.source).update(estado="sincronizando")
        from .models import SyncRun
        from django.utils import timezone

        run = SyncRun.objects.create(source=self.source, trigger="manual", started_at=timezone.now())
        observation = observe_sync_run(run)
        self.assertEqual(observation["events"], [])
        self.assertEqual(observation["reason"], "run_not_finished")
