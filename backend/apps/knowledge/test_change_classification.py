"""SOURCE-WATCH-01D — Source-Specific Change Classification tests."""

from django.test import TestCase

from .change_classification import HIGH, LOW, MEDIUM, UNKNOWN_IMPACT, classify_change, classify_run
from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, SourceState
from .services import sync_environmental_source


class GenericClassificationTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="classify-generic", nombre="Generic", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test",
            stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None

    def _set_batch(self, records, authoritative=True):
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=records, authoritative_full_snapshot=authoritative)

    def test_unknown_change_fails_closed_never_no_impact(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})])
        sync_environmental_source(self.source)
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 2})])
        run = sync_environmental_source(self.source)
        result = classify_run(run)
        self.assertEqual(len(result["classifications"]), 1)
        classification = result["classifications"][0]
        self.assertEqual(classification["classification"], UNKNOWN_IMPACT)
        self.assertTrue(classification["requires_review"])
        self.assertEqual(classification["severity"], MEDIUM)

    def test_new_record_is_low_severity_no_review(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})])
        run = sync_environmental_source(self.source)
        result = classify_run(run)
        classification = result["classifications"][0]
        self.assertEqual(classification["classification"], "new_record")
        self.assertFalse(classification["requires_review"])
        self.assertEqual(classification["severity"], LOW)

    def test_unchanged_never_requires_review(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})])
        sync_environmental_source(self.source)
        run = sync_environmental_source(self.source)
        result = classify_run(run)
        classification = result["classifications"][0]
        self.assertEqual(classification["classification"], "unchanged")
        self.assertFalse(classification["requires_review"])

    def test_disappearance_always_requires_review(self):
        self._set_batch([
            ConnectorRecord("one", "generic", payload={"a": 1}),
            ConnectorRecord("two", "generic", payload={"a": 2}),
        ])
        sync_environmental_source(self.source)
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})])
        run = sync_environmental_source(self.source)
        result = classify_run(run)
        disappeared = [c for c in result["classifications"] if c["event_classification"] == "disappeared"]
        self.assertEqual(len(disappeared), 1)
        self.assertTrue(disappeared[0]["requires_review"])
        self.assertEqual(disappeared[0]["severity"], HIGH)

    def test_malformed_event_kind_still_fails_closed(self):
        # An event classification the classifier does not explicitly know
        # about must still land in the fail-closed branch, never no_impact.
        classification = classify_change({"external_id": "x", "classification": "totally_unexpected"}, self.source)
        self.assertEqual(classification["classification"], UNKNOWN_IMPACT)
        self.assertTrue(classification["requires_review"])

    def test_idempotent_classification(self):
        self._set_batch([ConnectorRecord("one", "generic", payload={"a": 1})])
        run = sync_environmental_source(self.source)
        first = classify_run(run)
        second = classify_run(run)
        self.assertEqual(first, second)


class BcnLegalClassificationTests(TestCase):
    def setUp(self):
        self.source = EnvironmentalSource.objects.create(
            codigo="classify-bcn", nombre="BCN", organismo="Tests",
            connector_key="bcn_leychile_sparql", tipo_acceso="SPARQL", nivel_autoridad="test",
            stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)
        FakeEnvironmentalConnector.error = None

    def test_legal_change_always_high_severity_and_requires_review(self):
        event = {"external_id": "norma-1", "classification": "changed", "snapshot_id": 1, "content_hash": "x", "retrieved_at": None}
        classification = classify_change(event, self.source)
        self.assertEqual(classification["classification"], "legal_norm_changed")
        self.assertEqual(classification["severity"], HIGH)
        self.assertTrue(classification["requires_review"])
        self.assertEqual(classification["domain"], "legal")

    def test_unchanged_legal_source_defers_to_generic(self):
        event = {"external_id": "norma-1", "classification": "unchanged", "snapshot_id": 1, "content_hash": "x", "retrieved_at": None}
        classification = classify_change(event, self.source)
        self.assertEqual(classification["classification"], "unchanged")
        self.assertFalse(classification["requires_review"])


class OekobaudatClassificationTests(TestCase):
    def test_okobaudat_reuses_material_data_impact_assessment(self):
        from datetime import date
        from decimal import Decimal

        from apps.analytics.services.factor_governance import transition_factor_version
        from apps.analytics.services.material_candidates import (
            build_material_candidate,
            promote_material_candidate,
            review_material_candidate,
        )
        from apps.analytics.test_material_candidates import material_fixture
        from django.contrib.auth import get_user_model

        from .change_classification import classify_change
        from .models import ExternalSnapshot

        User = get_user_model()
        reviewer = User.objects.create_superuser("sw01d-reviewer", "sw01d-reviewer@example.com", "password")

        fixture_profile = material_fixture("a2")
        candidate, _created, evaluation = build_material_candidate(fixture_profile.pk)
        self.assertTrue(evaluation["compatible"])
        review_material_candidate(candidate.pk, reviewer, "approved")
        factor, version = promote_material_candidate(candidate.pk, reviewer)
        transition_factor_version(version, "pruebas")
        transition_factor_version(version, "validado")
        transition_factor_version(version, "activo")

        source = fixture_profile.process.snapshot.source
        event = {
            "external_id": str(fixture_profile.process.process_uuid),
            "classification": "changed",
            "snapshot_id": fixture_profile.snapshot_id,
            "content_hash": fixture_profile.snapshot.content_hash,
            "retrieved_at": None,
        }
        classification = classify_change(event, source)
        self.assertEqual(classification["domain"], "okobaudat")
        # The candidate has not changed relative to its own frozen
        # normalization, so this must be a real "no_impact" verdict —
        # never invented, always the actual MATERIAL-DATA assessment.
        self.assertEqual(classification["classification"], "okobaudat_no_impact")
        self.assertFalse(classification["requires_review"])
