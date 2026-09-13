"""AI INTELLIGENCE macrofase — eval suite runner.

Seeds/reuses the real synthetic demo tenant (never a mock), builds the
minimal cross-tenant/RBAC fixtures every category needs, runs every case
in `cases.CASE_FUNCTIONS`, and returns a structured report. Exits
non-zero (via the management command) if any case fails — this is the
"eval suite" gate, always runnable offline/in CI.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.analytics.models import Obra, Organizacion, UsuarioOrganizacion

from .cases import CASE_FUNCTIONS

User = get_user_model()

EVAL_STRANGER_USERNAME = "ai-eval-stranger"
EVAL_FOREIGN_ORG_ID = "AI_EVAL_FOREIGN_ORG"


def _build_fixtures():
    call_command("seed_ai_demo_tenant")
    organization = Organizacion.objects.get(organizacion_id="DEMO_HORIZONTE")
    membership = UsuarioOrganizacion.objects.filter(organizacion=organization).select_related("user").first()
    user = membership.user
    obra = Obra.objects.get(organizacion=organization, nombre="Edificio Horizonte Norte")

    stranger, _ = User.objects.get_or_create(
        username=EVAL_STRANGER_USERNAME, defaults={"email": "ai-eval-stranger@example.invalid"},
    )
    foreign_org, _ = Organizacion.objects.get_or_create(
        organizacion_id=EVAL_FOREIGN_ORG_ID, defaults={"nombre": "AI Eval Foreign Org", "preset": "construccion", "activa": True},
    )
    foreign_obra, _ = Obra.objects.get_or_create(
        organizacion=foreign_org, codigo_obra="AI_EVAL_FOREIGN_OBRA",
        defaults={"nombre": "AI Eval Foreign Obra", "fecha_inicio": date(2026, 1, 1), "estado": "en_ejecucion"},
    )
    return {
        "organization": organization, "user": user, "obra": obra,
        "stranger": stranger, "foreign_obra": foreign_obra,
    }


def run_all_evals():
    fixtures = _build_fixtures()
    results = []
    for case_function in CASE_FUNCTIONS:
        results.extend(case_function(**fixtures))

    by_category = {}
    for result in results:
        bucket = by_category.setdefault(result["category"], {"total": 0, "passed": 0, "failures": []})
        bucket["total"] += 1
        if result["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failures"].append(result)

    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    return {
        "total": total, "passed": passed, "failed": total - passed,
        "all_passed": passed == total,
        "by_category": by_category,
        "results": results,
    }
