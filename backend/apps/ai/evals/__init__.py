"""AI INTELLIGENCE macrofase — deterministic evaluation suite.

A repeatable, CI-appropriate regression gate — never requires network
access or a live LLM (that is what the separate real-OpenRouter smoke
scripts are for). Every eval case exercises the actual backend code path
(tools/diagnostics/analytics/forecasting/etc.) the same way the
orchestrator would, and asserts a concrete, deterministic outcome.

Run via `python manage.py run_ai_evals`.
"""
from .runner import run_all_evals

__all__ = ["run_all_evals"]
