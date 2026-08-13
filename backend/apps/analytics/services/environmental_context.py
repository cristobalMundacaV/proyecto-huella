from django.db.models import Count, Sum

from apps.analytics.models import (
    DatoACV, DocumentoAmbiental, EvidenciaObra,
)
from apps.analytics.services.environmental_engine import calculate_environmental_metrics, calculate_partial_lca
from apps.analytics.services.environmental_normative import applicable_validated_rules


MAX_ITEMS = 10


def organization_kpis(organization):
    return calculate_environmental_metrics(organization)


def organization_context(organization):
    metrics = organization_kpis(organization)
    return {
        "organizacion": {"id": organization.organizacion_id, "preset": organization.preset},
        "kpis": {
            "co2e_total_kg": metrics["co2e_total_kg"],
            "registros_contabilizados": metrics["registros_contabilizados"],
            "por_categoria": metrics["por_categoria"],
            "tendencia": metrics["tendencia"],
            "meta": metrics["meta"],
            "cobertura_datos_pct": metrics["cobertura_datos_pct"],
        },
        "problematicas": dict(organization.problematicas_ambientales.values_list("estado").annotate(total=Count("id"))),
        "acv": calculate_partial_lca(organization),
        "reglas_normativas_validadas": organization.limites_ambientales.filter(activo=True, validado=True).count(),
    }


def problem_context(problem):
    return {
        "id": problem.id, "titulo": problem.titulo, "descripcion": problem.descripcion[:500],
        "categoria": problem.categoria, "indicador": problem.indicador,
        "valor_inicial": problem.valor_inicial, "objetivo_meta": problem.objetivo_meta,
        "valor_posterior": problem.valor_posterior, "unidad": problem.unidad_indicador,
        "estado": problem.estado, "riesgo": problem.nivel_riesgo,
        "resultado_evaluacion": problem.resultado_evaluacion,
        "area": problem.area_operacional, "unidad_operacional": problem.unidad_operacional,
        "kpi_actual": _indicator_from_metrics(problem, organization_kpis(problem.organizacion)),
    }


def _indicator_from_metrics(problem, metrics):
    if problem.indicador == "co2e_total_kg":
        return metrics["co2e_total_kg"]
    if problem.indicador.startswith("categoria:"):
        return metrics["por_categoria"].get(problem.indicador.split(":", 1)[1])
    if problem.indicador.startswith("actividad:"):
        return metrics["por_actividad"].get(problem.indicador.split(":", 1)[1])
    return None


def problem_history(problem):
    rows = problem.historial.order_by("-created_at")[:MAX_ITEMS]
    return {"items": [{"evento": row.evento, "estado_anterior": row.estado_anterior, "estado_nuevo": row.estado_nuevo, "detalle": row.detalle[:240], "fecha": row.created_at} for row in rows], "limit": MAX_ITEMS, "total": problem.historial.count()}


def problem_sources(problem):
    records = problem.organizacion.registros_emision.filter(contabilizable=True, estado_validacion="validado")
    if problem.categoria:
        records = records.filter(categoria__iexact=problem.categoria)
    return {"resumen": list(records.values("tipo_ingreso", "unidad").annotate(registros=Count("id"), cantidad=Sum("cantidad"), co2e_kg=Sum("emisiones_kg_co2e")).order_by("tipo_ingreso", "unidad")[:MAX_ITEMS]), "total_registros": records.count(), "limit": MAX_ITEMS}


def previous_actions(problem):
    return {"items": [{"id": row.id, "titulo": row.titulo, "responsable": row.responsable, "implementada": bool(row.implementada_at), "fecha_objetivo": row.fecha_objetivo} for row in problem.acciones.all()[:MAX_ITEMS]], "total": problem.acciones.count(), "limit": MAX_ITEMS}


def evidence_summary(problem):
    records = problem.organizacion.registros_emision.filter(categoria__iexact=problem.categoria)
    evidences = EvidenciaObra.objects.filter(organizacion=problem.organizacion, registros_emision__in=records).distinct()
    documents = DocumentoAmbiental.objects.filter(organizacion=problem.organizacion, registros_emision__in=records).distinct()
    return {
        "evidencias": list(evidences.values("tipo_evidencia", "estado_documental").annotate(total=Count("id"))[:MAX_ITEMS]),
        "documentos": list(documents.values("tipo_documento", "estado_validacion").annotate(total=Count("id"))[:MAX_ITEMS]),
        "totales": {"evidencias": evidences.count(), "documentos": documents.count()},
        "contenido_excluido": ["archivo", "texto_extraido", "metadata_extraccion", "metadata"],
    }


def normative_context(problem):
    rules = applicable_validated_rules(
        problem.organizacion, problem.indicador,
        installation_type=(problem.metadata or {}).get("tipo_instalacion", ""),
    )[:MAX_ITEMS]
    return {"reglas_validadas": [{"id": row.id, "nombre": row.nombre, "normativa": row.normativa, "limite": row.limite, "unidad": row.unidad, "comparador": row.comparador, "fuente_normativa": row.fuente_normativa, "vigencia_desde": row.vigencia_desde, "vigencia_hasta": row.vigencia_hasta} for row in rules], "puede_afirmar_cumplimiento": bool(rules), "limit": MAX_ITEMS}


def material_lifecycle(organization, material):
    result = calculate_partial_lca(organization, material_producto=material.nombre)
    result["material"] = {"id": material.id, "nombre": material.nombre, "categoria": material.categoria}
    result["fuentes_resumen"] = list(DatoACV.objects.filter(organizacion=organization, material_producto__iexact=material.nombre).values("calidad_dato", "origen_dato").annotate(total=Count("id"))[:MAX_ITEMS])
    return result


def minimal_agent_context(problem):
    return {
        "problematica": problem_context(problem),
        "fuentes": problem_sources(problem),
        "acciones_previas": previous_actions(problem),
        "evidencias": evidence_summary(problem),
        "normativa": normative_context(problem),
        "historial_reciente": problem_history(problem),
    }
