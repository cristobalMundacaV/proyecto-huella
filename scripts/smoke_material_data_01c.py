"""Run via manage.py shell on the isolated local PostgreSQL validation DB only.

All fixture/review/promotion writes are rolled back; only the JSON report remains.
"""

import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from apps.analytics.test_material_candidates import material_fixture
from apps.analytics.services.material_candidates import (
    build_material_candidate,
    build_material_candidates,
    review_material_candidate,
    promote_material_candidate,
)
from apps.analytics.models import MaterialEnvironmentalFactorCandidate

database = settings.DATABASES["default"]
if (
    database["HOST"] != "127.0.0.1"
    or database["PORT"] != "55440"
    or database["NAME"] != "test_material01c"
):
    raise RuntimeError(
        "Smoke restricted to isolated local test_material01c on port 55440"
    )

report = {
    "scope": "official 01B XML fixtures; no network; all database writes rolled back",
    "profiles": [],
}
with transaction.atomic():
    user = get_user_model().objects.create_superuser(
        "material-smoke-reviewer", "", None
    )
    for label in ("a2", "a1"):
        profile = material_fixture(label)
        candidate, created, result = build_material_candidate(profile.pk)
        assert created and result["compatible"], result
        review_material_candidate(
            candidate.pk,
            user,
            "approved",
            "Local fixture smoke: verify normalization and provenance, no product equivalence.",
        )
        factor, version = promote_material_candidate(candidate.pk, user)
        candidate.refresh_from_db()
        report["profiles"].append(
            {
                "candidate_id": candidate.pk,
                "status": candidate.status,
                "normalization": candidate.normalization,
                "provenance": candidate.provenance,
                "functional_context": candidate.functional_context,
                "eligibility": {
                    k: result[k] for k in ("compatible", "source_current", "reasons")
                },
                "review": list(
                    candidate.reviews.values(
                        "id",
                        "decision",
                        "reviewer_id",
                        "reviewed_at",
                        "note",
                        "context",
                    )
                ),
                "factor": {
                    "id": factor.pk,
                    "context": factor.contexto,
                    "input_unit": factor.unidad_entrada,
                    "result_unit": factor.unidad_resultado,
                },
                "version": {
                    "id": version.pk,
                    "estado": version.estado,
                    "valor": str(version.valor),
                },
            }
        )
    report["repeat_build"] = build_material_candidates()
    assert report["repeat_build"]["created"] == 0
    assert MaterialEnvironmentalFactorCandidate.objects.count() == 2
    transaction.set_rollback(True)

output = Path(settings.PROJECT_ROOT) / "docs" / "material-data-01c-smoke.json"
output.write_text(
    json.dumps(report, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(output)
