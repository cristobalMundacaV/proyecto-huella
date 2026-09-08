from .models import EnvironmentalSource, SnifaOpenDatasetFact, SnifaRegulatoryReferenceFact
from .regulatory_facts import build_snifa_dataset_fact_payload, build_snifa_reference_fact_payload
from .regulatory_sync import sync_and_materialize


def _materialize(snapshot):
    if snapshot.record_kind == "snifa_open_dataset":
        SnifaOpenDatasetFact.objects.get_or_create(snapshot=snapshot, defaults=build_snifa_dataset_fact_payload(snapshot))
    elif snapshot.record_kind == "snifa_regulatory_reference":
        SnifaRegulatoryReferenceFact.objects.get_or_create(snapshot=snapshot, defaults=build_snifa_reference_fact_payload(snapshot))


def sync_snifa_regulatory_context():
    return sync_and_materialize(EnvironmentalSource.objects.get(codigo="snifa"), _materialize)
