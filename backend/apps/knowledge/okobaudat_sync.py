from .models import EnvironmentalSource,OekobaudatDataStockFact,OekobaudatProcessFact
from .okobaudat_facts import build_datastock_fact_payload,build_process_fact_payload
from .regulatory_sync import sync_and_materialize

def _materialize(snapshot):
    if snapshot.record_kind=="okobaudat_datastock":OekobaudatDataStockFact.objects.get_or_create(snapshot=snapshot,defaults=build_datastock_fact_payload(snapshot))
    elif snapshot.record_kind=="okobaudat_process":OekobaudatProcessFact.objects.get_or_create(snapshot=snapshot,defaults=build_process_fact_payload(snapshot))

def sync_okobaudat_material_catalog():return sync_and_materialize(EnvironmentalSource.objects.get(codigo="okobaudat"),_materialize)
