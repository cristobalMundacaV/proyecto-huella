from .models import EnvironmentalSource, SnifaOpenDatasetFact, SnifaRegulatoryReferenceFact
from .regulatory_sync import parsed_date, sync_and_materialize


def _materialize(snapshot):
    payload = snapshot.raw_payload or {}
    if snapshot.record_kind == "snifa_open_dataset":
        if not payload.get("dataset_code") or not payload.get("title") or not payload.get("source_url"): raise ValueError("Dataset SNIFA incompleto.")
        SnifaOpenDatasetFact.objects.get_or_create(snapshot=snapshot, defaults={"dataset_code":payload["dataset_code"],"title":payload["title"],"description":payload.get("description", ""),"publisher":payload.get("publisher", "Superintendencia del Medio Ambiente"),"source_url":payload["source_url"]})
    elif snapshot.record_kind == "snifa_regulatory_reference":
        if not payload.get("reference_type") or not payload.get("external_key") or not payload.get("source_url"): raise ValueError("Referencia SNIFA incompleta.")
        SnifaRegulatoryReferenceFact.objects.get_or_create(snapshot=snapshot, defaults={"reference_type":payload["reference_type"],"external_key":payload["external_key"],"expediente":payload.get("expediente", ""),"unit_external_key":payload.get("unit_external_key", ""),"unit_name":payload.get("unit_name", ""),"holder_name":payload.get("holder_name", ""),"category":payload.get("category", ""),"region":payload.get("region", ""),"commune":payload.get("commune", ""),"status_raw":payload.get("status_raw", ""),"event_date":parsed_date(payload.get("event_date_raw")),"sanction_amount_raw":payload.get("sanction_amount_raw", ""),"payment_status_raw":payload.get("payment_status_raw", ""),"instrument_references":payload.get("instrument_references", []),"source_url":payload["source_url"]})


def sync_snifa_regulatory_context():
    return sync_and_materialize(EnvironmentalSource.objects.get(codigo="snifa"), _materialize)
