from .models import EnvironmentalSource, SeaProjectFact, SeaRcaReferenceFact
from .regulatory_sync import parsed_date, sync_and_materialize


def _materialize(snapshot):
    if snapshot.record_kind != "sea_project": return
    payload = snapshot.raw_payload or {}
    if not payload.get("project_key") or not payload.get("name") or not payload.get("project_url"): raise ValueError("Proyecto SEA incompleto.")
    fact, _ = SeaProjectFact.objects.get_or_create(snapshot=snapshot, defaults={"project_key":payload["project_key"],"folio":payload.get("folio", ""),"name":payload["name"],"holder_name":payload.get("holder_name", ""),"region":payload.get("region", ""),"communes":payload.get("communes", []),"presentation_type_raw":payload.get("presentation_type_raw", ""),"status_raw":payload.get("status_raw", ""),"sector_raw":payload.get("sector_raw", ""),"project_type_raw":payload.get("project_type_raw", ""),"admission_reason_raw":payload.get("admission_reason_raw", ""),"submission_date":parsed_date(payload.get("submission_date")),"qualification_date":parsed_date(payload.get("qualification_date")),"project_url":payload["project_url"],"expediente_url":payload.get("expediente_url", "")})
    for item in payload.get("rca_references", []):
        if not item.get("document_key") or not item.get("title") or not item.get("document_url"): raise ValueError("Referencia RCA incompleta.")
        SeaRcaReferenceFact.objects.get_or_create(project_fact=fact, document_key=item["document_key"], defaults={"rca_number_raw":item.get("rca_number_raw", ""),"title":item["title"],"document_date":parsed_date(item.get("document_date")),"qualification_result_raw":item.get("qualification_result_raw", ""),"document_url":item["document_url"],"metadata":item.get("metadata", {})})


def sync_sea_regulatory_context():
    return sync_and_materialize(EnvironmentalSource.objects.get(codigo="sea-seia"), _materialize)
