from django.core.management.base import BaseCommand
from apps.knowledge.snifa_sync import sync_snifa_regulatory_context


class Command(BaseCommand):
    help = "Sincroniza el catalogo y las referencias SNIFA suscritas."

    def handle(self, *args, **options):
        run = sync_snifa_regulatory_context(); self.stdout.write(f"source=snifa status={run.estado} received={run.received} created={run.created} modified={run.modified} unchanged={run.unchanged} errors={run.errors}")
