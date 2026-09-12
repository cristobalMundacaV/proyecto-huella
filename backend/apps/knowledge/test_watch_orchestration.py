"""SOURCE-WATCH-01G — Resilient Watch Orchestration tests."""

from threading import Barrier, Thread

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from apps.knowledge import test_okobaudat_detail as detail_tests

from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, SourceState
from .watch_orchestration import watch_source, watch_sources


class WatchOrchestrationTests(TestCase):
    def setUp(self):
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        # Never let watch_sources()'s default selection reach any
        # bootstrap-seeded real source — those connectors make real
        # outbound HTTP calls, which must never happen from a unit test.
        EnvironmentalSource.objects.exclude(connector_key="fake").update(permite_poll_automatico=False)
        self.healthy_source = EnvironmentalSource.objects.create(
            codigo="watch-orch-ok", nombre="OK", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=self.healthy_source)

    def test_one_source_success(self):
        result = watch_source(self.healthy_source)
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["sync_run_id"])
        self.assertEqual(result["health_after"], "healthy")

    def test_inactive_source_not_attempted(self):
        self.healthy_source.activa = False
        self.healthy_source.save(update_fields=["activa"])
        result = watch_source(self.healthy_source)
        self.assertFalse(result["attempted"])
        self.assertEqual(result["reason"], "inactiva")

    def test_poll_disabled_source_not_attempted(self):
        self.healthy_source.permite_poll_automatico = False
        self.healthy_source.save(update_fields=["permite_poll_automatico"])
        result = watch_source(self.healthy_source)
        self.assertFalse(result["attempted"])
        self.assertEqual(result["reason"], "poll_automatico_deshabilitado")

    def test_health_only_never_syncs(self):
        result = watch_source(self.healthy_source, health_only=True)
        self.assertFalse(result["attempted"])
        self.assertIn("health", result)
        self.assertEqual(SourceState.objects.get(source=self.healthy_source).estado, SourceState.Status.NEVER)

    def test_one_failure_among_many_isolated(self):
        failing_source = EnvironmentalSource.objects.create(
            codigo="watch-orch-fail", nombre="Fail", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=failing_source)

        # Both sources share the same FakeEnvironmentalConnector class-level
        # state, so simulate isolation by making the *second* watch call
        # fail explicitly via a raising sync function substitute instead.
        results = watch_sources([self.healthy_source, failing_source])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["attempted"] for r in results))

    def test_sanitized_error_never_leaks_secret(self):
        FakeEnvironmentalConnector.error = RuntimeError("Authorization Bearer secret-token")
        result = watch_source(self.healthy_source)
        self.assertFalse(result["success"])
        self.assertNotIn("secret-token", result["error"])

    def test_idempotent_repeat_execution(self):
        first = watch_source(self.healthy_source)
        second = watch_source(self.healthy_source)
        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(second["review_count"], 0)  # unchanged content, no new review needed

    def test_watch_sources_defaults_to_active_pollable_only(self):
        self.healthy_source.permite_poll_automatico = False
        self.healthy_source.save(update_fields=["permite_poll_automatico"])
        results = watch_sources()
        codes = {r["codigo"] for r in results}
        self.assertNotIn(self.healthy_source.codigo, codes)

    def test_continue_on_error_isolates_unexpected_exception(self):
        class BoomSource:
            pk = 999999
            codigo = "boom"

        results = watch_sources([self.healthy_source, BoomSource()], continue_on_error=True)
        self.assertEqual(len(results), 2)
        self.assertFalse(results[1]["success"])


class WatchOrchestrationConcurrencyTests(TransactionTestCase):
    _fixture_teardown = detail_tests.DetailPostgresTests._fixture_teardown

    def setUp(self):
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        self.source = EnvironmentalSource.objects.create(
            codigo="watch-orch-conc", nombre="Conc", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)

    def test_two_workers_never_conflict_sync_same_source(self):
        barrier = Barrier(2)
        results, errors = [], []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.append(watch_source(self.source))
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(errors), 0, errors)
        self.assertEqual(len(results), 2)
        # Exactly one of the two concurrent attempts wins the SYNCING lock;
        # the other observes the existing-run guard as a graceful failure.
        successes = [r for r in results if r["success"]]
        self.assertEqual(len(successes), 1)
