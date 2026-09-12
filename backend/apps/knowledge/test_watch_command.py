"""SOURCE-WATCH-01I — Continuous Watch Command / Scheduling Readiness tests."""

import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .connectors.base import ConnectorBatch, ConnectorRecord
from .connectors.fake import FakeEnvironmentalConnector
from .models import EnvironmentalSource, SourceState


class WatchCommandTests(TestCase):
    def setUp(self):
        FakeEnvironmentalConnector.error = None
        FakeEnvironmentalConnector.batch = ConnectorBatch(records=[ConnectorRecord("one", "generic", payload={"a": 1})])
        # Never let "--all-active" (no --source) reach any bootstrap-seeded
        # real source (retc/huellachile/bcn-leychile/...) — those connectors
        # make real outbound HTTP calls, which must never happen from a
        # unit test. Only this test's own fake-connector sources should be
        # eligible for auto-poll.
        EnvironmentalSource.objects.exclude(connector_key="fake").update(permite_poll_automatico=False)
        self.source = EnvironmentalSource.objects.create(
            codigo="cmd-source", nombre="Cmd", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=self.source)

    def _run(self, *args):
        out = StringIO()
        call_command("watch_environmental_sources", *args, stdout=out)
        return out.getvalue()

    def test_single_source_selection(self):
        output = self._run("--source", self.source.codigo, "--json")
        results = json.loads(output)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])

    def test_unknown_source_code_raises(self):
        with self.assertRaises(CommandError):
            self._run("--source", "does-not-exist")

    def test_inactive_source_skipped_in_all_active_mode(self):
        self.source.activa = False
        self.source.save(update_fields=["activa"])
        output = self._run("--json")
        results = json.loads(output)
        # "--all-active" mode also sees any bootstrap-seeded sources already
        # present in this DB (post_migrate registry seeding); only assert
        # that *this* now-inactive source specifically is absent.
        codes = {r["codigo"] for r in results}
        self.assertNotIn(self.source.codigo, codes)

    def test_health_only_never_syncs(self):
        output = self._run("--source", self.source.codigo, "--health-only", "--json")
        results = json.loads(output)
        self.assertFalse(results[0]["attempted"])
        self.assertEqual(SourceState.objects.get(source=self.source).estado, SourceState.Status.NEVER)

    def test_dry_run_never_syncs(self):
        output = self._run("--source", self.source.codigo, "--dry-run", "--json")
        results = json.loads(output)
        self.assertFalse(results[0]["attempted"])

    def test_failure_reported_not_raised_by_default(self):
        FakeEnvironmentalConnector.error = RuntimeError("fallo de prueba")
        output = self._run("--source", self.source.codigo, "--json")
        results = json.loads(output)
        self.assertFalse(results[0]["success"])
        self.assertIn("fallo de prueba", results[0]["error"])

    def test_repeat_execution_is_safe(self):
        first = json.loads(self._run("--source", self.source.codigo, "--json"))
        second = json.loads(self._run("--source", self.source.codigo, "--json"))
        self.assertTrue(first[0]["success"])
        self.assertTrue(second[0]["success"])

    def test_continue_on_error_is_default(self):
        other_source = EnvironmentalSource.objects.create(
            codigo="cmd-source-2", nombre="Cmd2", organismo="Tests",
            connector_key="fake", tipo_acceso="REST", nivel_autoridad="test", stale_after_hours=10,
        )
        SourceState.objects.create(source=other_source)
        output = self._run("--json")
        results = json.loads(output)
        # "--all-active" also includes any bootstrap-seeded sources already
        # present; only assert that both of *this test's* sources were
        # attempted, not the exact total count.
        codes = {r["codigo"] for r in results}
        self.assertIn(self.source.codigo, codes)
        self.assertIn(other_source.codigo, codes)

    def test_human_readable_output_by_default(self):
        output = self._run("--source", self.source.codigo)
        self.assertIn("source=cmd-source", output)
        self.assertIn("success=True", output)
