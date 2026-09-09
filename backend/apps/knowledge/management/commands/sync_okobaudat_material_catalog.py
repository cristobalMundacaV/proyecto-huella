from django.core.management.base import BaseCommand
from apps.knowledge.bootstrap import ensure_environmental_source_registry
from apps.knowledge.models import EnvironmentalSource
from apps.knowledge.okobaudat_sync import sync_okobaudat_material_catalog

class Command(BaseCommand):
    help="Sincroniza el catalogo publico global de materiales Oekobaudat."
    def handle(self,*args,**options):
        ensure_environmental_source_registry();run=sync_okobaudat_material_catalog();metadata=EnvironmentalSource.objects.get(codigo="okobaudat").sync_state.metadata
        self.stdout.write(f"datastocks_received={metadata.get('datastocks_received',0)} selected_datastock={metadata.get('selected_datastock_name','')} processes_received={metadata.get('processes_received',0)} created={run.created} modified={run.modified} unchanged={run.unchanged} errors={run.errors}")
