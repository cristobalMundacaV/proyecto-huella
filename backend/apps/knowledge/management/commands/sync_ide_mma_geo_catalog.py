from django.core.management.base import BaseCommand
from apps.knowledge.geo_sync import sync_ide_mma_geo_catalog
class Command(BaseCommand):
    help="Sincroniza catalogos publicos documentados de IDE MMA."
    def handle(self,*args,**options):
        run=sync_ide_mma_geo_catalog();self.stdout.write(f"source=ide-mma status={run.estado} received={run.received} created={run.created} modified={run.modified} unchanged={run.unchanged} errors={run.errors}")
