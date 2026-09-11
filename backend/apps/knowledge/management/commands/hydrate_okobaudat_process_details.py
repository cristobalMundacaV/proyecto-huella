import json
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from ...okobaudat_detail_sync import hydrate_details


class Command(BaseCommand):
    help = "Hidrata detalles oficiales Oekobaudat y publica perfiles inmutables A1-A3; reanudar ejecutando nuevamente."

    def add_arguments(self, parser):
        parser.add_argument("--process-uuid", type=UUID)
        parser.add_argument("--dataset-version")
        parser.add_argument("--limit", type=int, help="Maximo de identidades pendientes a procesar; las ya hidratadas no consumen el limite.")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--delay", type=float, default=1.0)
        parser.add_argument("--refetch-failed-reason", default="", help="Razon tecnica gobernada: vuelve a observar solo identidades NO materializadas.")

    def handle(self, *args, **options):
        def progress(uuid, version, result):
            self.stdout.write(f"{uuid} {version}: {result['status']}" + (f" ({result['error']})" if result.get("error") else ""))
        try:
            result = hydrate_details(process_uuid=options["process_uuid"], dataset_version=options["dataset_version"],
                limit=options["limit"], batch_size=options["batch_size"], delay=options["delay"],
                refetch_reason=options["refetch_failed_reason"], progress=progress)
        except Exception:
            raise CommandError("No fue posible ejecutar la hidratacion Oekobaudat.") from None
        self.stdout.write(json.dumps(result, sort_keys=True))
        if result["failed"]:
            raise CommandError("Hidratacion parcial; consulte el resumen y reintente las identidades fallidas.")
