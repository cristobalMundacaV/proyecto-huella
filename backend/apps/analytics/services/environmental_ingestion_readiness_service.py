from collections import Counter

from django.utils import timezone

from apps.analytics.models import DocumentoAmbiental, EvidenciaObra, RegistroEmision, VariableAmbientalExtraida


PRESET_REQUIREMENTS = {
    "construccion": {
        "documents": ["factura", "guia", "rcd", "pesaje", "combustible", "energia", "agua"],
        "variables": ["hormigon", "acero", "diesel", "kwh", "agua", "rcd", "km"],
        "fields": ["periodo", "cantidad", "unidad", "proveedor", "obra", "fuente", "evidencia"],
    },
    "transporte": {
        "documents": ["combustible", "ruta", "gps", "mantencion", "neumatico", "aceite"],
        "variables": ["diesel", "km", "rendimiento", "ralenti", "carga"],
        "fields": ["vehiculo", "patente", "ruta", "km", "litros", "cliente", "fecha"],
    },
    "forestal": {
        "documents": ["trozas", "produccion", "energia", "combustible", "biomasa", "residuo", "transporte"],
        "variables": ["m3", "kwh", "biomasa", "aserrin", "humedad", "diesel"],
        "fields": ["lote", "especie", "m3", "proceso", "energia", "destino", "fecha"],
    },
    "industrial": {
        "documents": ["riles", "respel", "sidrep", "sinader", "energia", "combustible", "produccion"],
        "variables": ["ph", "dbo5", "dqo", "sst", "respel", "kwh", "agua"],
        "fields": ["proceso", "periodo", "valor", "unidad", "limite", "normativa", "documento"],
    },
    "industrial_agroindustria": {
        "documents": ["riles", "respel", "sidrep", "sinader", "energia", "combustible", "produccion"],
        "variables": ["ph", "dbo5", "dqo", "sst", "respel", "kwh", "agua"],
        "fields": ["proceso", "periodo", "valor", "unidad", "limite", "normativa", "documento"],
    },
    "mineria": {
        "documents": ["rca", "agua", "relaves", "mp10", "mp2.5", "combustible", "monitoreo"],
        "variables": ["agua", "mp10", "mp2.5", "relaves", "diesel", "respel"],
        "fields": ["faena", "punto", "valor", "unidad", "limite", "fecha", "evidencia"],
    },
    "energia": {
        "documents": ["cems", "so2", "nox", "opacidad", "combustible", "generacion", "mantencion"],
        "variables": ["so2", "nox", "opacidad", "co2", "mwh", "combustible"],
        "fields": ["unidad_generadora", "chimenea", "valor", "unidad", "continuidad", "fecha", "combustible"],
    },
}


def build_environmental_ingestion_readiness(organizacion):
    preset_key = normalize_preset(organizacion)
    requirements = PRESET_REQUIREMENTS.get(preset_key, PRESET_REQUIREMENTS["industrial"])
    documents = list(DocumentoAmbiental.objects.filter(organizacion=organizacion).order_by("-created_at"))
    variables = list(VariableAmbientalExtraida.objects.filter(organizacion=organizacion).order_by("-created_at"))
    evidences = list(EvidenciaObra.objects.filter(organizacion=organizacion).order_by("-created_at")[:20])
    records = RegistroEmision.objects.filter(organizacion=organizacion)

    doc_coverage = coverage_items(requirements["documents"], documents, document_text)
    variable_coverage = coverage_items(requirements["variables"], variables, variable_text)
    field_coverage = infer_field_coverage(requirements["fields"], documents, variables, records)
    source_distribution = Counter([doc.fuente_origen or "manual" for doc in documents])
    status_distribution = Counter([doc.estado_validacion or "pendiente" for doc in documents])
    processing_distribution = Counter([doc.estado_procesamiento or "pendiente" for doc in documents])

    score = readiness_score(doc_coverage, variable_coverage, field_coverage, documents, variables, records)
    next_uploads = build_next_uploads(doc_coverage, variable_coverage, field_coverage, preset_key)
    blockers = build_blockers(documents, variables, records, doc_coverage, variable_coverage)

    return {
        "organizacion_id": organizacion.organizacion_id,
        "preset": organizacion.preset,
        "rubro": organizacion.rubro,
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "score": score,
            "status": readiness_label(score),
            "documents_total": len(documents),
            "variables_total": len(variables),
            "evidences_total": len(evidences),
            "records_total": records.count(),
            "source_distribution": dict(source_distribution),
            "validation_distribution": dict(status_distribution),
            "processing_distribution": dict(processing_distribution),
        },
        "document_coverage": doc_coverage,
        "variable_coverage": variable_coverage,
        "field_coverage": field_coverage,
        "next_uploads": next_uploads,
        "blockers": blockers,
        "recent_documents": [serialize_document(item) for item in documents[:8]],
        "recent_variables": [serialize_variable(item) for item in variables[:8]],
    }


def normalize_preset(organizacion):
    text = f"{organizacion.preset} {organizacion.rubro}".lower()
    if "transporte" in text:
        return "transporte"
    if "aserr" in text or "forestal" in text:
        return "forestal"
    if "min" in text:
        return "mineria"
    if "energ" in text or "cems" in text:
        return "energia"
    if "constr" in text:
        return "construccion"
    return organizacion.preset or "industrial"


def coverage_items(expected, current_items, text_builder):
    results = []
    corpus = "\n".join(text_builder(item) for item in current_items).lower()
    for keyword in expected:
        present = keyword.lower() in corpus
        matches = [serialize_match(item, text_builder) for item in current_items if keyword.lower() in text_builder(item).lower()][:3]
        results.append({
            "key": keyword,
            "label": humanize(keyword),
            "status": "covered" if present else "missing",
            "matches": matches,
            "reason": "Existe respaldo asociado." if present else "Falta documento o variable base para alimentar calculos y reporte.",
        })
    return results


def infer_field_coverage(expected, documents, variables, records):
    record_count = records.count()
    has_provider = records.exclude(proveedor="").exists()
    has_distance = records.filter(distancia_km__isnull=False).exists()
    has_units = records.exclude(unidad="").exists()
    has_dates = records.filter(fecha__isnull=False).exists() or any(doc.fecha_documento for doc in documents)
    variable_names = " ".join(f"{item.variable_id} {item.nombre} {item.unidad}" for item in variables).lower()
    doc_texts = " ".join(document_text(item) for item in documents).lower()
    checks = {
        "periodo": has_dates,
        "fecha": has_dates,
        "cantidad": record_count > 0,
        "valor": bool(variables) or record_count > 0,
        "unidad": has_units or any(item.unidad for item in variables),
        "proveedor": has_provider,
        "obra": records.filter(obra__isnull=False).exists(),
        "fuente": record_count > 0,
        "evidencia": bool(documents),
        "vehiculo": "vehiculo" in doc_texts or "patente" in doc_texts,
        "patente": "patente" in doc_texts,
        "ruta": has_distance or "ruta" in doc_texts,
        "km": has_distance or "km" in variable_names,
        "litros": "litro" in variable_names or "diesel" in variable_names,
        "cliente": "cliente" in doc_texts,
        "lote": "lote" in doc_texts or records.filter(lote_forestal__isnull=False).exists(),
        "especie": "especie" in doc_texts,
        "m3": "m3" in variable_names or "m³" in variable_names,
        "proceso": "proceso" in doc_texts or "proceso" in variable_names,
        "energia": "kwh" in variable_names or "energia" in doc_texts,
        "destino": "destino" in doc_texts,
        "limite": any(item.limite_aplicable is not None for item in variables),
        "normativa": "normativa" in doc_texts or any((item.metadata or {}).get("normativa") for item in variables),
        "documento": bool(documents),
        "faena": "faena" in doc_texts,
        "punto": any(item.punto_medicion for item in variables),
        "unidad_generadora": "unidad generadora" in doc_texts,
        "chimenea": "chimenea" in doc_texts or "cems" in doc_texts,
        "continuidad": "continuidad" in doc_texts or "cems" in doc_texts,
        "combustible": "combustible" in doc_texts or "diesel" in variable_names,
    }
    return [{"key": item, "label": humanize(item), "status": "covered" if checks.get(item) else "missing"} for item in expected]


def readiness_score(doc_coverage, variable_coverage, field_coverage, documents, variables, records):
    doc_pct = pct_covered(doc_coverage)
    variable_pct = pct_covered(variable_coverage)
    field_pct = pct_covered(field_coverage)
    volume_bonus = 10 if documents and records.exists() else 5 if documents or records.exists() else 0
    variable_bonus = 10 if variables else 0
    return min(round((doc_pct * 0.35) + (variable_pct * 0.25) + (field_pct * 0.25) + volume_bonus + variable_bonus), 100)


def pct_covered(items):
    if not items:
        return 0
    return (sum(1 for item in items if item.get("status") == "covered") / len(items)) * 100


def build_next_uploads(doc_coverage, variable_coverage, field_coverage, preset_key):
    uploads = []
    for item in doc_coverage:
        if item["status"] == "missing":
            uploads.append({"title": f"Cargar {item['label']}", "type": "documento", "priority": "alta", "reason": item["reason"]})
    for item in variable_coverage:
        if item["status"] == "missing":
            uploads.append({"title": f"Capturar variable {item['label']}", "type": "variable", "priority": "media", "reason": "Sin esta variable el KPI o escenario queda incompleto."})
    missing_fields = [item["label"] for item in field_coverage if item["status"] == "missing"][:4]
    if missing_fields:
        uploads.append({"title": "Completar campos base de ingesta", "type": "campo", "priority": "media", "reason": f"Faltan campos: {', '.join(missing_fields)}."})
    if not uploads:
        uploads.append({"title": "Mantener ingesta mensual", "type": "seguimiento", "priority": "baja", "reason": f"La base de ingesta para {preset_key} tiene cobertura suficiente para seguimiento."})
    return uploads[:8]


def build_blockers(documents, variables, records, doc_coverage, variable_coverage):
    blockers = []
    if not documents:
        blockers.append("No hay documentos ambientales cargados.")
    if not records.exists():
        blockers.append("No hay registros de emision asociados a la empresa.")
    if not variables:
        blockers.append("No hay variables ambientales extraidas o registradas.")
    if any(item["status"] == "missing" for item in doc_coverage[:2]):
        blockers.append("Faltan documentos criticos iniciales del preset.")
    if any(item["status"] == "missing" for item in variable_coverage[:2]):
        blockers.append("Faltan variables criticas iniciales del preset.")
    return blockers[:6]


def serialize_document(document):
    return {"id": document.id, "nombre": document.nombre, "tipo_documento": document.tipo_documento, "fuente_origen": document.fuente_origen, "estado_procesamiento": document.estado_procesamiento, "estado_validacion": document.estado_validacion, "fecha_documento": document.fecha_documento.isoformat() if document.fecha_documento else ""}


def serialize_variable(variable):
    return {"id": variable.id, "variable_id": variable.variable_id, "nombre": variable.nombre, "valor": float(variable.valor) if variable.valor is not None else None, "unidad": variable.unidad, "estado_cumplimiento": variable.estado_cumplimiento}


def serialize_match(item, text_builder):
    return {"id": getattr(item, "id", None), "label": getattr(item, "nombre", None) or text_builder(item)[:80]}


def document_text(document):
    return f"{document.tipo_documento} {document.nombre} {document.resumen} {document.fuente_origen} {document.estado_validacion}"


def variable_text(variable):
    return f"{variable.variable_id} {variable.nombre} {variable.categoria} {variable.unidad} {variable.estado_cumplimiento}"


def humanize(value):
    return str(value).replace("_", " ").replace("mp2.5", "MP2.5").replace("mp10", "MP10").title()


def readiness_label(score):
    if score >= 85:
        return "Ingesta lista"
    if score >= 60:
        return "Ingesta util con brechas"
    return "Ingesta incompleta"
