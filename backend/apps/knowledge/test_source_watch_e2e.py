"""SOURCE-WATCH-01J — closure E2E.

Exercises the complete chain: watch cycle -> sync/observation -> change
detection -> classification -> impact routing -> review queue -> operator
API, across at least: a healthy unchanged source, a changed source, a
source failure with last-known-good data preserved, and a source producing
a human-review item. Also demonstrates disappearance safety (authoritative
vs incremental) and historical reconstruction without re-fetching upstream.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .change_classification import classify_run
from .change_observation import observe_sync_run
from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .impact_routing import route_run_impact
from .models import EnvironmentalSource, ExternalRecord, SourceState, SourceWatchReviewItem
from .review_queue import open_items_from_run
from .source_health import source_health
from .watch_orchestration import watch_source

User = get_user_model()


class MultiSourceEndToEndTests(TestCase):
    def setUp(self):
        FakeEnvironmentalConnector.error = None

    def _source(self, codigo):
        source = EnvironmentalSource.objects.create(
            codigo=codigo, nombre=codigo, organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=source)
        return source

    def test_healthy_unchanged_source_full_cycle(self):
        source = self._source("e2e-healthy")
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        watch_source(source)  # first sync: creates
        result = watch_source(source)  # second sync: unchanged
        self.assertTrue(result["success"])
        self.assertEqual(result["health_after"], "healthy")
        self.assertEqual(result["review_count"], 0)

    def test_changed_source_opens_review_and_routes_impact(self):
        source = self._source("e2e-changed")
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        watch_source(source)
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 2})])
        result = watch_source(source)
        self.assertTrue(result["success"])
        self.assertEqual(result["review_count"], 1)
        item = SourceWatchReviewItem.objects.get(source=source)
        self.assertEqual(item.classification, "changed_unknown_impact")
        self.assertTrue(item.estado, SourceWatchReviewItem.Estado.OPEN)

    def test_source_failure_preserves_last_known_good(self):
        source = self._source("e2e-failure")
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        watch_source(source)
        before_snapshot = ExternalRecord.objects.get(source=source).current_snapshot_id

        FakeEnvironmentalConnector.error = RuntimeError("upstream down")
        result = watch_source(source)
        self.assertFalse(result["success"])
        self.assertEqual(result["health_after"], "error_with_last_version")

        record = ExternalRecord.objects.get(source=source)
        self.assertEqual(record.current_snapshot_id, before_snapshot)
        health = source_health(source)
        self.assertTrue(health["last_known_good_available"])

    def test_disappearance_safety_authoritative_vs_incremental(self):
        source = self._source("e2e-disappearance")
        FakeEnvironmentalConnector.batch = ConnectorBatch(
            records=[
                ConnectorRecord("keep", "generic", payload={"a": 1}),
                ConnectorRecord("maybe-gone", "generic", payload={"a": 2}),
            ],
            authoritative_full_snapshot=True,
        )
        watch_source(source)

        # Incremental/non-authoritative observation omitting "maybe-gone"
        # must never mark it disappeared.
        FakeEnvironmentalConnector.batch = ConnectorBatch(
            records=[ConnectorRecord("keep", "generic", payload={"a": 1})],
            authoritative_full_snapshot=False,
        )
        watch_source(source)
        self.assertEqual(
            ExternalRecord.objects.get(source=source, external_id="maybe-gone").estado,
            ExternalRecord.Status.ACTIVE,
        )

        # An authoritative observation omitting it DOES mark it missing.
        FakeEnvironmentalConnector.batch = ConnectorBatch(
            records=[ConnectorRecord("keep", "generic", payload={"a": 1})],
            authoritative_full_snapshot=True,
        )
        result = watch_source(source)
        self.assertEqual(
            ExternalRecord.objects.get(source=source, external_id="maybe-gone").estado,
            ExternalRecord.Status.MISSING,
        )
        self.assertEqual(result["review_count"], 1)

    def test_historical_reconstruction_without_refetching_upstream(self):
        source = self._source("e2e-history")
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        watch_source(source)
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 2})])
        result = watch_source(source)
        run_id = result["sync_run_id"]

        # Reconstruct strictly by ID, from persisted rows only — never
        # touching FakeEnvironmentalConnector / "upstream" again.
        from .models import SyncRun

        run = SyncRun.objects.get(pk=run_id)
        observation = observe_sync_run(run)
        classified = classify_run(run)
        impacted = route_run_impact(run)
        self.assertEqual(len(observation["events"]), 1)
        self.assertEqual(observation["events"][0]["classification"], "changed")
        self.assertEqual(classified["classifications"][0]["classification"], "changed_unknown_impact")
        self.assertEqual(impacted["impacts"][0]["impact_level"], "unknown_impact")

    def test_okobaudat_source_specific_e2e(self):
        from apps.analytics.services.factor_governance import transition_factor_version
        from apps.analytics.services.material_candidates import (
            build_material_candidate, promote_material_candidate, review_material_candidate,
        )
        from apps.analytics.test_material_candidates import material_fixture

        reviewer = User.objects.create_superuser("e2e-okobaudat", "e2e-okobaudat@example.com", "password")
        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")

        okobaudat_source = fixture_profile.process.snapshot.source
        from .change_classification import classify_change

        event = {
            "external_id": str(fixture_profile.process.process_uuid),
            "classification": "changed",
            "snapshot_id": fixture_profile.snapshot_id,
            "content_hash": fixture_profile.snapshot.content_hash,
            "retrieved_at": None,
        }
        classification = classify_change(event, okobaudat_source)
        self.assertEqual(classification["domain"], "okobaudat")
        self.assertEqual(classification["classification"], "okobaudat_no_impact")

    def test_legal_source_specific_e2e(self):
        from .change_classification import classify_change

        bcn_source = EnvironmentalSource.objects.create(
            codigo="e2e-bcn", nombre="BCN", organismo="Tests",
            connector_key="bcn_leychile_sparql", tipo_acceso="SPARQL", nivel_autoridad="test", stale_after_hours=10,
        )
        event = {"external_id": "norma-e2e", "classification": "changed", "snapshot_id": 1, "content_hash": "x", "retrieved_at": None}
        classification = classify_change(event, bcn_source)
        self.assertEqual(classification["domain"], "legal")
        self.assertTrue(classification["requires_review"])

    def test_review_resolution_never_mutates_downstream(self):
        source = self._source("e2e-review-safe")
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        watch_source(source)
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 2})])
        watch_source(source)
        item = SourceWatchReviewItem.objects.get(source=source)

        admin = User.objects.create_superuser("e2e-review-admin", "e2e-review-admin@example.com", "password")
        from .review_queue import resolve_review_item

        resolved = resolve_review_item(item.pk, admin)
        self.assertEqual(resolved.estado, SourceWatchReviewItem.Estado.RESOLVED)
        # Resolving is purely a record of human attention — the record's
        # own current_snapshot/estado are completely unaffected.
        record = ExternalRecord.objects.get(source=source, external_id="one")
        self.assertEqual(record.estado, ExternalRecord.Status.ACTIVE)
