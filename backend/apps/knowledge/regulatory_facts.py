from datetime import date


def parsed_date(value):
    return date.fromisoformat(str(value)[:10]) if value else None


def build_snifa_dataset_fact_payload(snapshot):
    payload = snapshot.raw_payload or {}
    if (
        snapshot.source.codigo != "snifa"
        or snapshot.record_kind != "snifa_open_dataset"
        or not payload.get("dataset_code")
        or not payload.get("title")
        or not payload.get("source_url")
    ):
        raise ValueError("Dataset SNIFA incompleto o incompatible.")
    return {
        "dataset_code": payload["dataset_code"],
        "title": payload["title"],
        "description": payload.get("description", ""),
        "publisher": payload.get("publisher", "Superintendencia del Medio Ambiente"),
        "source_url": payload["source_url"],
    }


def build_snifa_reference_fact_payload(snapshot):
    payload = snapshot.raw_payload or {}
    if snapshot.source.codigo != "snifa" or snapshot.record_kind != "snifa_regulatory_reference" or not payload.get("reference_type") or not payload.get("external_key") or not payload.get("source_url"):
        raise ValueError("Referencia SNIFA incompleta o incompatible.")
    return {
        "reference_type": payload["reference_type"], "external_key": payload["external_key"],
        "expediente": payload.get("expediente", ""), "unit_external_key": payload.get("unit_external_key", ""),
        "unit_name": payload.get("unit_name", ""), "holder_name": payload.get("holder_name", ""),
        "category": payload.get("category", ""), "region": payload.get("region", ""),
        "commune": payload.get("commune", ""), "status_raw": payload.get("status_raw", ""),
        "event_date": parsed_date(payload.get("event_date_raw")), "sanction_amount_raw": payload.get("sanction_amount_raw", ""),
        "payment_status_raw": payload.get("payment_status_raw", ""), "instrument_references": payload.get("instrument_references", []),
        "source_url": payload["source_url"],
    }


def build_sea_project_fact_payload(snapshot):
    payload = snapshot.raw_payload or {}
    if snapshot.source.codigo != "sea-seia" or snapshot.record_kind != "sea_project" or not payload.get("project_key") or not payload.get("name") or not payload.get("project_url"):
        raise ValueError("Proyecto SEA incompleto o incompatible.")
    return {
        "project_key": payload["project_key"], "folio": payload.get("folio", ""), "name": payload["name"],
        "holder_name": payload.get("holder_name", ""), "region": payload.get("region", ""), "communes": payload.get("communes", []),
        "presentation_type_raw": payload.get("presentation_type_raw", ""), "status_raw": payload.get("status_raw", ""),
        "sector_raw": payload.get("sector_raw", ""), "project_type_raw": payload.get("project_type_raw", ""),
        "admission_reason_raw": payload.get("admission_reason_raw", ""), "submission_date": parsed_date(payload.get("submission_date")),
        "qualification_date": parsed_date(payload.get("qualification_date")), "project_url": payload["project_url"],
        "expediente_url": payload.get("expediente_url", ""),
    }


def build_sea_rca_fact_payload(project_fact, item):
    if not isinstance(item, dict) or not item.get("document_key"):
        raise ValueError("Referencia RCA incompleta.")
    source_items = (project_fact.snapshot.raw_payload or {}).get("rca_references", [])
    source = next((candidate for candidate in source_items if candidate.get("document_key") == item["document_key"]), None)
    if source is None or not source.get("title") or not source.get("document_url"):
        raise ValueError("Referencia RCA no pertenece al snapshot del proyecto.")
    return {
        "document_key": source["document_key"], "rca_number_raw": source.get("rca_number_raw", ""),
        "title": source["title"], "document_date": parsed_date(source.get("document_date")),
        "qualification_result_raw": source.get("qualification_result_raw", ""), "document_url": source["document_url"],
        "metadata": source.get("metadata", {}),
    }


def model_fact_payload(instance, fields):
    return {field: getattr(instance, field) for field in fields}
