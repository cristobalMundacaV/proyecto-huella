from django.core.management.base import BaseCommand
from apps.knowledge.geo_sync import sync_simbio_geo_catalog
class Command(BaseCommand):
    help="Sincroniza el manifest gobernado de capas SIMBIO."
    def handle(self,*args,**options):
        run=sync_simbio_geo_catalog();self.stdout.write(f"source=simbio status={run.estado} received={run.received} created={run.created} modified={run.modified} unchanged={run.unchanged} errors={run.errors}")
