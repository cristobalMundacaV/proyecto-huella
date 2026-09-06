from django.core.management.base import BaseCommand, CommandError
from apps.knowledge.bcn_sync import sync_bcn_legal_norms


class Command(BaseCommand):
    help = "Sincroniza el corpus jurídico monitoreado de BCN/LeyChile."

    def handle(self, *args, **options):
        result = sync_bcn_legal_norms()
        self.stdout.write(
            f"estado={result.estado} received={result.received} created={result.created} modified={result.modified} unchanged={result.unchanged} errors={result.errors}"
        )
        if result.estado == "error":
            raise CommandError(result.message)
