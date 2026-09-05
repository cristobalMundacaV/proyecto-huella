from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.models import EnvironmentalSource
from apps.knowledge.services import sync_environmental_source


class Command(BaseCommand):
    help = "Sincroniza una fuente registrada en Environmental Knowledge Hub."

    def add_arguments(self, parser):
        parser.add_argument("source_code")

    def handle(self, *args, **options):
        try:
            source = EnvironmentalSource.objects.get(codigo=options["source_code"])
        except EnvironmentalSource.DoesNotExist as exc:
            raise CommandError(f"Fuente no registrada: {options['source_code']}") from exc
        run = sync_environmental_source(source)
        self.stdout.write(
            f"source={source.codigo} status={run.estado} received={run.received} "
            f"created={run.created} modified={run.modified} unchanged={run.unchanged} disappeared={run.disappeared}"
        )
        if run.estado == "error":
            raise CommandError(run.message or "La sincronización terminó con error.")
