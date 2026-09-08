from .geo_facts import build_ide_dataset_fact_payload,build_ide_download_fact_payload,build_simbio_layer_fact_payload
from .models import EnvironmentalSource,IdeMmaDatasetFact,IdeMmaDownloadResourceFact,SimbioGeoLayerFact
from .regulatory_sync import sync_and_materialize

def _materialize_simbio(snapshot):
    if snapshot.record_kind=="simbio_geo_layer":SimbioGeoLayerFact.objects.get_or_create(snapshot=snapshot,defaults=build_simbio_layer_fact_payload(snapshot))

def _materialize_ide(snapshot):
    if snapshot.record_kind=="ide_mma_dataset":IdeMmaDatasetFact.objects.get_or_create(snapshot=snapshot,defaults=build_ide_dataset_fact_payload(snapshot))
    elif snapshot.record_kind=="ide_mma_download_resource":IdeMmaDownloadResourceFact.objects.get_or_create(snapshot=snapshot,defaults=build_ide_download_fact_payload(snapshot))

def sync_simbio_geo_catalog():return sync_and_materialize(EnvironmentalSource.objects.get(codigo="simbio"),_materialize_simbio)
def sync_ide_mma_geo_catalog():return sync_and_materialize(EnvironmentalSource.objects.get(codigo="ide-mma"),_materialize_ide)
