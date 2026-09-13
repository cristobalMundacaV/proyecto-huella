"""AI INTELLIGENCE macrofase — the deterministic eval suite, wired into
the regular test run so it is checked on every `manage.py test apps.ai`,
not only via the standalone `run_ai_evals` management command."""
from django.test import TestCase

from apps.ai.evals import run_all_evals

EXPECTED_CATEGORIES = {
    "lookup", "analytics", "ranking", "diagnostics", "forecast", "anomaly", "risk", "scenarios",
    "prioritization", "provenance", "rbac", "cross_tenant", "adversarial", "tool_routing", "multi_turn",
}


class EvalSuiteTests(TestCase):
    def test_all_eval_categories_are_present(self):
        report = run_all_evals()
        self.assertEqual(set(report["by_category"].keys()), EXPECTED_CATEGORIES)

    def test_eval_suite_passes_completely(self):
        report = run_all_evals()
        failures = [result for result in report["results"] if not result["passed"]]
        self.assertEqual(failures, [], f"Eval failures: {failures}")
        self.assertTrue(report["all_passed"])
        self.assertGreater(report["total"], 0)
