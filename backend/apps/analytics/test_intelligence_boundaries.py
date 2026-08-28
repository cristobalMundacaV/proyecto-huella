import ast
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .policies.intelligence import (
    AI_AUTHORITY,
    IntelligenceOperation,
    validate_ai_operation,
)


class IntelligenceAuthorityBoundaryTests(SimpleTestCase):
    def test_authority_matrix_denies_deterministic_decisions(self):
        self.assertTrue(AI_AUTHORITY[IntelligenceOperation.READ_CONTEXT])
        self.assertTrue(AI_AUTHORITY[IntelligenceOperation.SUGGEST])
        self.assertTrue(AI_AUTHORITY[IntelligenceOperation.PREPARE_COMMAND])

        for operation in (
            IntelligenceOperation.APPLY_ACTION,
            IntelligenceOperation.CALCULATE_ENVIRONMENTAL_TRUTH,
            IntelligenceOperation.DECIDE_COMPLIANCE,
            IntelligenceOperation.VERIFY_IMPROVEMENT,
            IntelligenceOperation.CLOSE_PROBLEM,
        ):
            self.assertFalse(AI_AUTHORITY[operation])
            with self.assertRaises(ValidationError):
                validate_ai_operation(operation)

    def test_provider_facing_service_does_not_import_deterministic_authorities(self):
        root = Path(__file__).resolve().parent
        forbidden = {
            "calculation_v2",
            "compliance",
            "intervention_v2",
            "copilot_commands",
            "environmental_action_closure_service",
        }
        for filename in ("copilot_v2.py", "environmental_agent.py"):
            tree = ast.parse((root / "services" / filename).read_text(encoding="utf-8"))
            imports = {
                (node.module or "").rsplit(".", 1)[-1]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertTrue(forbidden.isdisjoint(imports), filename)
