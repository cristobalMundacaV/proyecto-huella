import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from ..models import DiscrepanciaDato
from .document_extraction import normalize_text
from .unit_conversion import UnitConversionError, canonicalize_unit, convert_value


DOCUMENT_EXPECTATIONS = {
    "combustible_consumido": {"factura_combustible", "documento_transporte"},
    "consumo_energia": {"boleta_electrica"},
    "consumo_agua": {"factura_agua"},
    "cantidad_residuo": {"ticket_pesaje", "certificado_residuos"},
    "distancia_recorrida_km": {"guia_despacho", "documento_transporte"},
    "masa_transportada_t": {"guia_despacho", "ticket_pesaje", "documento_transporte"},
}

CRITICAL_FIELDS = {"cantidad", "tipo_recurso"}


def classify_evidence_relevance(extraction, observation):
    detected = extraction.get("tipo_documento") or "otro"
    expected = DOCUMENT_EXPECTATIONS.get(observation.concepto, set())
    confidence = Decimal(str(extraction.get("confianza") or 0))
    explicit = extraction.get("relevancia_detectada")
    if explicit in {"pertinente", "parcialmente_pertinente", "no_pertinente", "indeterminado"}:
        if explicit == "no_pertinente" and confidence < Decimal("0.75"):
            return {"estado": "indeterminado", "confianza": str(confidence), "motivo": "La clasificación sugirió que el archivo no era pertinente, pero no tuvo confianza suficiente para rechazarlo automáticamente."}
        return {"estado": explicit, "confianza": str(confidence), "motivo": extraction.get("motivo_relevancia") or "Resultado entregado por la etapa de clasificación documental."}
    if detected in expected:
        if confidence >= Decimal("0.75"):
            return {"estado": "pertinente", "confianza": str(confidence), "motivo": "El tipo documental corresponde al dato registrado."}
        return {"estado": "parcialmente_pertinente", "confianza": str(confidence), "motivo": "El tipo parece compatible, pero la clasificación documental requiere revisión."}
    if detected != "otro" and expected:
        if confidence >= Decimal("0.75"):
            return {"estado": "no_pertinente", "confianza": str(confidence), "motivo": "El documento detectado no corresponde al tipo de respaldo esperado."}
        return {"estado": "indeterminado", "confianza": str(confidence), "motivo": "La clasificación sugiere otro documento, pero no tiene confianza suficiente para rechazarlo automáticamente."}
    if extraction.get("texto_extraido") or extraction.get("claims"):
        return {"estado": "parcialmente_pertinente", "confianza": str(confidence), "motivo": "El documento contiene información extraíble, pero su tipo no pudo confirmarse."}
    return {"estado": "indeterminado", "confianza": str(confidence), "motivo": "No fue posible determinar la pertinencia del archivo sin inventar contenido."}


def extract_evidence_claims(extraction):
    return {
        key: value
        for key, value in dict(extraction.get("claims") or {}).items()
        if value not in (None, "")
    }


def technical_extraction_validation(extraction):
    execution_status = extraction.get("execution_status")
    if execution_status == "success" or not execution_status:
        return None
    messages = {
        "unavailable": "La extracción automática no está disponible; el respaldo queda pendiente de procesamiento.",
        "failed": "La extracción automática falló técnicamente; el respaldo requiere revisión técnica.",
        "unsupported": "El formato no puede procesarse automáticamente; el respaldo requiere revisión técnica.",
        "empty": "No se obtuvo contenido procesable del archivo; el respaldo requiere revisión técnica.",
    }
    return {
        "estado": "indeterminada",
        "veredicto": "indeterminada",
        "relevancia": None,
        "comparaciones": [],
        "motivos": [messages.get(execution_status, messages["failed"])],
        "resultado_extraccion": {
            key: extraction.get(key)
            for key in ("execution_status", "extractor_used", "provider_used", "model_used", "failure_code", "claims_count")
        },
        "version_contrato": "validacion-documental-v2",
    }


def _text_comparison(field, declared, extracted):
    if extracted in (None, ""):
        return {"campo": field, "estado": "no_disponible", "declarado": declared, "documental": None}
    matches = normalize_text(declared) == normalize_text(extracted)
    return {"campo": field, "estado": "coincide" if matches else "contradice", "declarado": declared, "documental": extracted}


def _quantity_comparison(observation, claims):
    extracted = claims.get("cantidad")
    extracted_unit = claims.get("unidad")
    if extracted in (None, ""):
        return {"campo": "cantidad", "estado": "no_disponible", "declarado": str(observation.valor_numerico), "documental": None}
    try:
        converted = convert_value(extracted, extracted_unit, observation.unidad)
        declared = Decimal(str(observation.valor_numerico))
        documental = converted["valor_normalizado"]
    except (UnitConversionError, InvalidOperation):
        return {"campo": "cantidad", "estado": "requiere_revision", "declarado": f"{observation.valor_numerico} {observation.unidad}".strip(), "documental": f"{extracted} {extracted_unit}".strip(), "motivo": "No existe una conversión determinística segura entre las unidades."}
    tolerance = max(abs(declared) * Decimal("0.005"), Decimal("0.000001"))
    matches = abs(declared - documental) <= tolerance
    state = "compatible_por_conversion" if matches and converted["conversion_aplicada"] else ("coincide" if matches else "contradice")
    return {"campo": "cantidad", "estado": state, "declarado": f"{declared} {observation.unidad}".strip(), "documental": f"{extracted} {extracted_unit}".strip(), "diferencia_absoluta": str(abs(declared - documental)), "conversion": converted.get("regla")}


def compare_evidence_to_observation(observation, claims, context=None):
    context = context or {}
    comparisons = [_quantity_comparison(observation, claims)] if observation.valor_numerico is not None else []
    document_unit = claims.get("unidad")
    if observation.unidad:
        if not document_unit:
            comparisons.append({"campo": "unidad", "estado": "no_disponible", "declarado": observation.unidad, "documental": None})
        else:
            try:
                declared_unit = canonicalize_unit(observation.unidad)
                normalized_unit = canonicalize_unit(document_unit)
                if declared_unit == normalized_unit:
                    state = "coincide"
                else:
                    convert_value(1, normalized_unit, declared_unit)
                    state = "compatible_por_conversion"
            except UnitConversionError:
                state = "requiere_revision"
            comparisons.append({"campo": "unidad", "estado": state, "declarado": observation.unidad, "documental": document_unit})
    declared_resource = context.get("tipo_recurso")
    if declared_resource:
        comparisons.append(_text_comparison("tipo_recurso", declared_resource, claims.get("tipo_recurso")))
    if observation.timestamp_observacion:
        document_date = claims.get("fecha")
        declared_date = observation.timestamp_observacion.date().isoformat()
        if not document_date:
            comparisons.append({"campo": "fecha", "estado": "no_disponible", "declarado": declared_date, "documental": None})
        else:
            try:
                delta = abs((date.fromisoformat(document_date) - date.fromisoformat(declared_date)).days)
                comparisons.append({"campo": "fecha", "estado": "coincide" if delta == 0 else "contradice", "declarado": declared_date, "documental": document_date, "diferencia_dias": delta})
            except ValueError:
                comparisons.append({"campo": "fecha", "estado": "requiere_revision", "declarado": declared_date, "documental": document_date})
    trace = context.get("claims_trazables") or {}
    for comparison in comparisons:
        if comparison["campo"] in trace:
            comparison["trazabilidad_documental"] = trace[comparison["campo"]]
    return comparisons


def evaluate_evidence_validation(relevance, comparisons):
    if relevance["estado"] == "no_pertinente":
        state = "no_pertinente"
    elif relevance["estado"] == "indeterminado":
        state = "indeterminada"
    elif any(item["estado"] == "contradice" for item in comparisons):
        state = "contradiccion"
    elif relevance["estado"] == "parcialmente_pertinente":
        state = "compatible_incompleta"
    elif any(item["estado"] in {"no_disponible", "requiere_revision"} for item in comparisons):
        state = "compatible_incompleta"
    elif comparisons:
        state = "verificada"
    else:
        state = "indeterminada"
    return {
        "estado": state,
        "veredicto": state,
        "relevancia": relevance,
        "comparaciones": comparisons,
        "motivos": [relevance["motivo"]] + [item.get("motivo") or f"{item['campo']}: {item['estado']}." for item in comparisons],
        "version_contrato": "validacion-documental-v2",
    }


def _sync_discrepancies(observation, validation):
    contradictions = [item for item in validation["comparaciones"] if item["estado"] == "contradice"]
    active = DiscrepanciaDato.objects.filter(actividad=observation.actividad, concepto__startswith="evidencia_").exclude(estado__in=[DiscrepanciaDato.Estado.RESUELTA, DiscrepanciaDato.Estado.DESCARTADA])
    contradiction_fields = {item["campo"] for item in contradictions}
    active.exclude(concepto__in=[f"evidencia_{field}" for field in contradiction_fields]).update(estado=DiscrepanciaDato.Estado.RESUELTA, resolucion="La versión documental vigente ya no presenta esta contradicción.")
    for item in contradictions:
        severity = DiscrepanciaDato.Severidad.ALTA if item["campo"] in CRITICAL_FIELDS else DiscrepanciaDato.Severidad.MEDIA
        discrepancy = active.filter(concepto=f"evidencia_{item['campo']}").first()
        values = {
            "estado": DiscrepanciaDato.Estado.REQUIERE_REVISION,
            "severidad": severity,
            "motivo": json.dumps(item, ensure_ascii=False),
        }
        if discrepancy:
            for field, value in values.items():
                setattr(discrepancy, field, value)
            discrepancy.save(update_fields=[*values, "updated_at"])
        else:
            discrepancy = DiscrepanciaDato.objects.create(
                organizacion=observation.organizacion,
                actividad=observation.actividad,
                concepto=f"evidencia_{item['campo']}",
                **values,
            )
        discrepancy.observaciones.add(observation)


@transaction.atomic
def validate_observation_evidence(observation, extraction, context=None, version=None):
    context = context or {}
    extraction = dict(extraction or {})
    extraction["expected"] = {
        "cantidad": str(observation.valor_numerico) if observation.valor_numerico is not None else None,
        "unidad": observation.unidad or None,
        "fecha": observation.timestamp_observacion.date().isoformat() if observation.timestamp_observacion else None,
        "tipo_recurso": context.get("tipo_recurso") or None,
    }
    technical_validation = technical_extraction_validation(extraction)
    if technical_validation:
        validation = technical_validation
        _sync_discrepancies(observation, validation)
        return validation
    relevance = classify_evidence_relevance(extraction, observation)
    claims = extract_evidence_claims(extraction)
    context = {**context, "claims_trazables": extraction.get("claims_trazables") or {}}
    comparisons = compare_evidence_to_observation(observation, claims, context)
    validation = evaluate_evidence_validation(relevance, comparisons)
    _sync_discrepancies(observation, validation)
    return validation
