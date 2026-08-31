from django.core.management.base import BaseCommand

from apps.analytics.models import VersionEvidencia
from apps.analytics.services.evidence_processing import process_evidence_version


class Command(BaseCommand):
    help = "Procesa durable e idempotentemente versiones documentales pendientes."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--retry-errors", action="store_true")

    def handle(self, *args, **options):
        states = [VersionEvidencia.EstadoProcesamiento.RECIBIDA]
        if options["retry_errors"]:
            states.append(VersionEvidencia.EstadoProcesamiento.ERROR)
        ids = list(
            VersionEvidencia.objects.filter(
                estado_procesamiento__in=states,
                metadata_tecnica__document_result_version="document-result-v2",
            )
            .order_by("created_at")
            .values_list("id", flat=True)[: options["limit"]]
        )
        for version_id in ids:
            process_evidence_version(version_id, force=options["retry_errors"])
        self.stdout.write(self.style.SUCCESS(f"Versiones procesadas: {len(ids)}"))
