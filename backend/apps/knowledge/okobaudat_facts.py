from uuid import UUID

def _uuid(value):return UUID(str(value))

def build_datastock_fact_payload(snapshot):
    payload=snapshot.raw_payload or {}
    if snapshot.source.codigo!="okobaudat" or snapshot.record_kind!="okobaudat_datastock" or not payload.get("datastock_uuid") or not payload.get("short_name"):raise ValueError("Snapshot datastock Oekobaudat incompatible.")
    return {"datastock_uuid":_uuid(payload["datastock_uuid"]),"short_name":payload["short_name"],"display_name":payload.get("display_name",""),"description":payload.get("description",""),"release_label":payload.get("release_label",""),"version_label":payload.get("version_label",""),"source_url":payload["source_url"],"upstream_metadata":payload.get("upstream_metadata",{})}

def build_process_fact_payload(snapshot):
    payload=snapshot.raw_payload or {}
    if snapshot.source.codigo!="okobaudat" or snapshot.record_kind!="okobaudat_process" or not payload.get("process_uuid") or not payload.get("dataset_version") or not payload.get("datastock_uuid"):raise ValueError("Snapshot process Oekobaudat incompatible.")
    result={key:payload.get(key,default) for key,default in {"dataset_version":"","name":"","base_name":"","location_raw":"","dataset_type_raw":"","owner_raw":"","classification":[],"languages":{},"compliance_standard_raw":"unknown","compliance_source_uuid":"","permanent_uri":"","source_url":"","process_metadata":{}}.items()}
    result.update({"datastock_uuid":_uuid(payload["datastock_uuid"]),"process_uuid":_uuid(payload["process_uuid"])});return result
