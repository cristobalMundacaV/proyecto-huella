from django.utils import timezone

from apps.analytics.models import DocumentoAmbiental, EvidenciaObra
from apps.analytics.models_acciones import AccionAmbiental
from apps.analytics.views_acciones import serialize_action


def build_action_closure_status(action):
    metadata = action.metadata if isinstance(action.metadata, dict) else {}
    linked_evidence = build_linked_evidence(action, metadata)
    linked_documents = build_linked_documents(action, metadata)
    notes = metadata.get("closure_notes", [])
    references = metadata.get("closure_references", [])
    required_evidence = action.evidence or metadata.get("required_evidence") or "Evidencia ambiental trazable"
    has_support = bool(linked_evidence or linked_documents or notes or references)
    missing_items = []
    warnings = []

    if not has_support:
        missing_items.append("Vincular evidencia, documento, nota o referencia antes de cerrar.")
    if action.status != AccionAmbiental.Estado.COMPLETADA and action.due_date and action.due_date < timezone.localdate():
        warnings.append("La accion esta vencida; registrar resultado y evidencia antes del cierre.")

    return {
        "action_id": action.id,
        "title": action.title,
        "status": closure_status(action, has_support),
        "required_evidence": required_evidence,
        "linked_evidence": linked_evidence,
        "linked_documents": linked_documents,
        "closure_readiness": {
            "can_close": has_support or action.status == AccionAmbiental.Estado.COMPLETADA,
            "missing_items": missing_items,
            "warnings": warnings,
        },
        "technical_context": {
            "source_decision": metadata.get("priority_id") or metadata.get("decision") or action.source_card_id or "",
            "expected_impact": metadata.get("expected_impact") or metadata.get("impact_observed") or "",
            "recommended_next_step": metadata.get("recommended_next_step") or action.tracking_kpi or "",
        },
        "closure": metadata.get("closure", {}),
    }


def attach_evidence_to_action(action, payload):
    metadata = action.metadata if isinstance(action.metadata, dict) else {}
    metadata.setdefault("linked_documents", [])
    metadata.setdefault("linked_evidence", [])
    metadata.setdefault("closure_notes", [])
    metadata.setdefault("closure_references", [])

    evidence_id = payload.get("evidence_id") or payload.get("evidencia_id")
    document_id = payload.get("document_id") or payload.get("documento_id")
    note = clean_text(payload.get("note"))
    reference = clean_text(payload.get("reference"))

    if evidence_id:
        evidence = EvidenciaObra.objects.filter(id=evidence_id, constructora=action.constructora).first()
        if not evidence:
            raise ValueError("Evidencia no encontrada para esta empresa.")
        action.evidencia = evidence
        upsert_ref(metadata["linked_evidence"], {"id": evidence.id, "label": evidence.nombre, "type": evidence.tipo_evidencia})

    if document_id:
        document = DocumentoAmbiental.objects.filter(id=document_id, constructora=action.constructora).first()
        if not document:
            raise ValueError("Documento ambiental no encontrado para esta empresa.")
        upsert_ref(metadata["linked_documents"], {"id": document.id, "label": document.nombre, "type": document.tipo_documento})

    if note:
        metadata["closure_notes"].append({"text": note, "created_at": timezone.now().isoformat()})
    if reference:
        metadata["closure_references"].append({"text": reference, "created_at": timezone.now().isoformat()})

    metadata["last_evidence_update_at"] = timezone.now().isoformat()
    action.metadata = metadata
    if action.status == AccionAmbiental.Estado.PENDIENTE:
        action.status = AccionAmbiental.Estado.EN_PROGRESO
    action.save()
    return {
        "action": serialize_action(action),
        "closure_status": build_action_closure_status(action),
    }


def close_environmental_action(action, payload):
    metadata = action.metadata if isinstance(action.metadata, dict) else {}
    status = build_action_closure_status(action)
    close_with_warning = bool(payload.get("close_with_warning"))
    closure_result = clean_text(payload.get("closure_result"))
    evidence_summary = clean_text(payload.get("evidence_summary"))
    impact_observed = clean_text(payload.get("impact_observed"))

    if not status["closure_readiness"]["can_close"] and not close_with_warning:
        raise ValueError("Falta evidencia o justificacion para cerrar la accion.")
    if close_with_warning and not closure_result:
        raise ValueError("Para cerrar con advertencia debes registrar un resultado de cierre.")

    closure = {
        "closed_at": timezone.now().isoformat(),
        "closed_date": timezone.localdate().isoformat(),
        "closure_result": closure_result or "Accion cerrada con evidencia vinculada.",
        "impact_observed": impact_observed,
        "evidence_summary": evidence_summary,
        "close_with_warning": close_with_warning,
        "responsible": action.responsible or "Equipo ambiental",
        "missing_items_at_close": status["closure_readiness"]["missing_items"],
        "warnings_at_close": status["closure_readiness"]["warnings"],
    }
    metadata["closure"] = closure
    metadata["impact_observed"] = impact_observed
    metadata["evidence_summary"] = evidence_summary
    action.metadata = metadata
    action.status = AccionAmbiental.Estado.COMPLETADA
    action.description = append_closure_to_description(action.description, closure)
    action.save()
    return {
        "action": serialize_action(action),
        "closure_status": build_action_closure_status(action),
        "closure_summary": closure,
    }


def build_linked_evidence(action, metadata):
    refs = list(metadata.get("linked_evidence", []))
    if action.evidencia_id and not any(str(item.get("id")) == str(action.evidencia_id) for item in refs):
        refs.insert(0, {"id": action.evidencia_id, "label": action.evidencia.nombre, "type": action.evidencia.tipo_evidencia})
    return refs


def build_linked_documents(action, metadata):
    return list(metadata.get("linked_documents", []))


def closure_status(action, has_support):
    if action.status == AccionAmbiental.Estado.COMPLETADA:
        return "cerrada"
    if action.status == AccionAmbiental.Estado.VALIDACION:
        return "en_revision"
    if action.status == AccionAmbiental.Estado.EN_PROGRESO:
        return "en_revision" if has_support else "en_progreso"
    return "pendiente"


def append_closure_to_description(description, closure):
    block = (
        "\n\nCierre ambiental:\n"
        f"Fecha: {closure['closed_date']}\n"
        f"Resultado: {closure['closure_result']}\n"
        f"Impacto observado: {closure['impact_observed'] or 'No informado'}\n"
        f"Evidencia usada: {closure['evidence_summary'] or 'Ver metadata/evidencias vinculadas'}\n"
        f"Cierre con advertencia: {'si' if closure['close_with_warning'] else 'no'}"
    )
    return f"{description or ''}{block}"


def upsert_ref(items, ref):
    if any(str(item.get("id")) == str(ref["id"]) for item in items):
        return
    items.append(ref)


def clean_text(value):
    return str(value or "").strip()
