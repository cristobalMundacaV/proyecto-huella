from django.core.management.base import BaseCommand
from apps.knowledge.sea_sync import sync_sea_regulatory_context


class Command(BaseCommand):
    help = "Sincroniza los proyectos SEA suscritos."

    def handle(self, *args, **options):
        run = sync_sea_regulatory_context(); self.stdout.write(f"source=sea-seia status={run.estado} received={run.received} created={run.created} modified={run.modified} unchanged={run.unchanged} errors={run.errors}")
