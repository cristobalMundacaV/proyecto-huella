"""AI INTELLIGENCE macrofase — `python manage.py run_ai_evals`.

Runs the deterministic eval suite (`apps.ai.evals.run_all_evals`) and
prints a category-by-category report. Exits with status 1 if any case
failed — wire this into CI as the "eval suite" gate.
"""
from django.core.management.base import BaseCommand

from apps.ai.evals import run_all_evals


class Command(BaseCommand):
    help = "Runs the AI INTELLIGENCE deterministic eval suite and reports pass/fail by category."

    def handle(self, *args, **options):
        report = run_all_evals()
        for category, bucket in sorted(report["by_category"].items()):
            status = "OK" if bucket["passed"] == bucket["total"] else "FAIL"
            self.stdout.write(f"[{status}] {category}: {bucket['passed']}/{bucket['total']}")
            for failure in bucket["failures"]:
                self.stdout.write(self.style.ERROR(f"    - {failure['name']}: {failure['detail']}"))
        self.stdout.write("")
        self.stdout.write(f"TOTAL: {report['passed']}/{report['total']} passed")
        if not report["all_passed"]:
            self.stdout.write(self.style.ERROR("EVAL SUITE FAILED"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("EVAL SUITE PASSED"))
