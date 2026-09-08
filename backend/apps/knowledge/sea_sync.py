from .models import EnvironmentalSource, SeaProjectFact, SeaRcaReferenceFact
from .regulatory_facts import build_sea_project_fact_payload, build_sea_rca_fact_payload
from .regulatory_sync import sync_and_materialize


def _materialize(snapshot):
    if snapshot.record_kind != "sea_project": return
    fact, _ = SeaProjectFact.objects.get_or_create(snapshot=snapshot, defaults=build_sea_project_fact_payload(snapshot))
    for item in (snapshot.raw_payload or {}).get("rca_references", []):
        values = build_sea_rca_fact_payload(fact, item)
        document_key = values.pop("document_key")
        SeaRcaReferenceFact.objects.get_or_create(project_fact=fact, document_key=document_key, defaults=values)


def sync_sea_regulatory_context():
    return sync_and_materialize(EnvironmentalSource.objects.get(codigo="sea-seia"), _materialize)
