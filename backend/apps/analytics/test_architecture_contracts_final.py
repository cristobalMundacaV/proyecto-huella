from pathlib import Path

from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARCHITECTURE_ROOT = PROJECT_ROOT / "docs" / "architecture"
ANALYTICS_ROOT = Path(__file__).resolve().parent

ARCHITECTURE_DOCUMENTS = {
    "ARQ-02": "ARQ_02_MODEL_MODULARIZATION.md",
    "ARQ-03": "ARQ_03_APPLICATION_LAYERS.md",
    "ARQ-04": "ARQ_04_OPERATIONAL_KERNEL.md",
    "ARQ-05": "ARQ_05_UNIFIED_CAPTURE.md",
    "ARQ-06": "ARQ_06_CONSTRUCTION_V1_FLOWS.md",
    "ARQ-07": "ARQ_07_GENERIC_ENVIRONMENTAL_ENGINE.md",
    "ARQ-08": "ARQ_08_REQUIREMENTS_COMPLIANCE.md",
    "ARQ-09": "ARQ_09_IMPROVEMENT_LOOP.md",
    "ARQ-10": "ARQ_10_INTELLIGENCE_BOUNDARIES.md",
    "ARQ-11": "ARQ_11_FRONTEND_ALIGNMENT.md",
    "ARQ-12": "ARQ_12_LEGACY_RETIREMENT.md",
}

CRITICAL_POSTGRES_MODULES = (
    "test_application_layers.py",
    "test_model_modularization.py",
    "test_operational_kernel_contract.py",
    "test_unified_capture.py",
    "test_construction_flow_contracts_v1.py",
    "test_generic_environmental_engine.py",
    "test_calculation_v2.py",
    "test_requirements_compliance_contract.py",
    "test_intervention_v2.py",
    "test_intelligence_boundaries.py",
    "test_professional_v2.py",
    "test_rbac.py",
    "test_rbac02_scope.py",
)


class FinalArchitectureContractTests(SimpleTestCase):
    def test_every_closed_phase_has_a_versioned_contract(self):
        for phase, filename in ARCHITECTURE_DOCUMENTS.items():
            path = ARCHITECTURE_ROOT / filename
            self.assertTrue(path.is_file(), f"Missing contract for {phase}: {filename}")
            content = path.read_text(encoding="utf-8")
            self.assertIn(phase, content)
            self.assertIn("CLOSED", content)

    def test_official_runner_is_postgresql_only(self):
        runner = (
            PROJECT_ROOT / "backend" / "scripts" / "run_tests_postgres.py"
        ).read_text(encoding="utf-8")
        self.assertIn('POSTGRES_ENGINE = "django.db.backends.postgresql"', runner)
        self.assertIn("if engine != POSTGRES_ENGINE:", runner)
        self.assertIn('if connection.vendor != "postgresql":', runner)
        self.assertNotIn("django.db.backends.sqlite3", runner)

    def test_critical_matrix_has_no_explicit_sqlite_dependency(self):
        for filename in CRITICAL_POSTGRES_MODULES:
            path = ANALYTICS_ROOT / filename
            self.assertTrue(path.is_file(), filename)
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("sqlite", content, filename)
            self.assertNotIn("override_settings(databases", content, filename)

    def test_contract_chain_is_explicit_in_final_document(self):
        final_contract = (
            ARCHITECTURE_ROOT / "ARQ_13_CONTRACTS_TESTS_DOCS.md"
        ).read_text(encoding="utf-8")
        for boundary in (
            "Operational Kernel",
            "Unified Capture",
            "Environment",
            "Calculation",
            "Compliance",
            "Improvement",
            "Intelligence",
            "Reporting",
            "Frontend",
        ):
            self.assertIn(boundary, final_contract)
        self.assertIn("Debt register", final_contract)
