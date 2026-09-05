from django.core.management.base import BaseCommand, CommandError

from apps.knowledge.resource_sync import sync_retc_hazardous_waste


class Command(BaseCommand):
    help="Descarga e importa el recurso estadístico RETC de generación de residuos peligrosos."
    def add_arguments(self,parser): parser.add_argument("--year",type=int,required=True)
    def handle(self,*args,**options):
        try: result=sync_retc_hazardous_waste(options["year"])
        except Exception as exc: raise CommandError(str(exc)) from exc
        self.stdout.write(f"dataset={result.dataset}\nresource={result.resource_name} ({result.resource_id})\nyear={result.year}\nformat={result.format}\nbytes={result.byte_size}\nsha256={result.sha256}\nrows_read={result.rows_read}\nrows_imported={result.rows_imported}\nrows_rejected={len(result.rejected)}\nartifact_version={result.artifact.version}\nstatus={result.estado}")
