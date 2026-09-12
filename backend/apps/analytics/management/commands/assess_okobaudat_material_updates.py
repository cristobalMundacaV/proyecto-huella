import json

from django.core.management.base import BaseCommand

from apps.analytics.services.material_source_impact import assess_all_candidates


class Command(BaseCommand):
    help = (
        "Read-only, idempotent assessment of whether already-hydrated ÖKOBAUDAT "
        "updates could affect existing material candidates/factors/mappings. "
        "Never fetches upstream, never mutates any candidate, factor, mapping "
        "or calculation. Safe to run repeatedly and concurrently."
    )

    def add_arguments(self, parser):
        parser.add_argument("--status", help="Filtra por estado del candidato.")

    def handle(self, *args, **options):
        filters = {}
        if options.get("status"):
            filters["status"] = options["status"]
        report = assess_all_candidates(**filters)
        self.stdout.write(json.dumps(report, ensure_ascii=False, default=str))
