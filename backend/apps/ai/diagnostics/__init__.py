"""AI-INTELLIGENCE-03 — deterministic environmental diagnostics.

Layering, deliberately kept separate:
    analytics  (apps.ai.analytics_tools, apps.analytics.services.*) -> raw numbers
    diagnostics (this package)                                      -> findings
    LLM (apps.ai.tools/orchestrator)                                -> explanation

Nothing in this package calls an LLM, and nothing outside this package
decides what counts as a finding. `engine.run_environmental_diagnostics`
is the single entry point.
"""
from .engine import run_environmental_diagnostics

__all__ = ["run_environmental_diagnostics"]
