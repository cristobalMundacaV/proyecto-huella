import json
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from apps.analytics.services.material_candidates import build_material_candidates
from apps.knowledge.connectors.okobaudat_detail import VERSION


class Command(BaseCommand):
    help = "Construye candidatos globales desde perfiles hidratados; nunca revisa ni promueve."

    def add_arguments(self, parser):
        parser.add_argument("--process-uuid")
        parser.add_argument("--dataset-version")

    def handle(self, *args, **options):
        filters = {}
        if options["process_uuid"]:
            try:
                filters["process_uuid"] = UUID(options["process_uuid"])
            except ValueError:
                raise CommandError("UUID inválido.") from None
        if options["dataset_version"]:
            if not VERSION.fullmatch(options["dataset_version"]):
                raise CommandError("Dataset version inválida.")
            filters["dataset_version"] = options["dataset_version"]
        self.stdout.write(
            json.dumps(build_material_candidates(**filters), ensure_ascii=False)
        )
