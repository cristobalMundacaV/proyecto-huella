import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify

from ..models import (
    CasoConocimientoAmbiental,
    EvaluacionCalidadDato,
    HitoDecisionIA,
    RevisionProfesionalAmbiental,
)
from ..policies.knowledge import validate_knowledge_result
from ..selectors.knowledge import knowledge_counts, usable_knowledge

RESULT_MAP = {
    "positiva": "exitoso",
    "parcial": "parcialmente_exitoso",
    "implementada_sin_efecto": "sin_efecto",
    "negativa": "negativo",
    "no_viable": "no_viable",
    "no_implementada": "no_implementado",
    "inconclusa": "inconcluso",
}


def _abstract_slug(value, fallback):
    return slugify(str(value or ""))[:120] or fallback


def _implementation(result):
    if result.estado == "no_implementada":
        return "no_implementado", "no_evaluada"
    if result.estado == "no_viable":
        return "no_implementado", "no_viable"
    if result.estado == "inconclusa":
        return "implementacion_no_verificable", "indeterminada"
    return "implementado", "viable"


def _evidence(result):
    problem = result.problematica
    activity_ids = list(
        problem.alcances_v2.exclude(actividad_operacional=None).values_list(
            "actividad_operacional_id", flat=True
        )
    )
    observations = problem.organizacion.observaciones_operacionales.filter(
        actividad_id__in=activity_ids
    )
    signals = []
    if result.snapshot_base_id:
        signals.append("snapshot_base")
    if result.snapshot_resultado_id:
        signals.append("snapshot_resultado")
    if result.metricas_comparadas:
        signals.append("indicadores_comparables")
    if observations.filter(evidencia__isnull=False).exists():
        signals.append("evidencia_documental")
    if result.accion.implementada_at or result.accion.estado in {
        "en_implementacion",
        "seguimiento",
        "evaluada",
    }:
        signals.append("implementacion_registrada")
    if RevisionProfesionalAmbiental.objects.filter(
        organizacion=problem.organizacion,
        problematica=problem,
        estado__in=["validada", "validada_con_observaciones"],
    ).exists():
        signals.append("revision_profesional")
    if EvaluacionCalidadDato.objects.filter(
        observacion__in=observations,
        estado__in=["confiable", "confiable_con_observaciones"],
    ).exists():
        signals.append("calidad_dato")
    strength = (
        "alta" if len(signals) >= 5 else ("media" if len(signals) >= 3 else "baja")
    )
    return strength, signals


def _payload(result, origin):
    problem, action = result.problematica, result.accion
    implementation, viability = _implementation(result)
    strength, reasons = _evidence(result)
    scopes = problem.alcances_v2.all()
    indicators = [
        {
            "tipo": link.indicador.tipo,
            "unidad": link.indicador.unidad,
            "direccion": link.direccion_deseada,
            "rol": link.rol,
        }
        for link in problem.indicadores_v2.select_related("indicador")
    ]
    metrics = [
        {
            key: item.get(key)
            for key in (
                "base",
                "resultado",
                "diferencia",
                "porcentaje",
                "estado",
                "meta_cumplida",
            )
        }
        for item in result.metricas_comparadas
    ]
    return {
        "preset": problem.organizacion.preset,
        "tipo_problematica": _abstract_slug(
            problem.metadata.get("tipo_problematica"),
            _abstract_slug(problem.categoria, "problematica_ambiental"),
        ),
        "categoria_ambiental": _abstract_slug(problem.categoria, "ambiental"),
        "tipo_accion": _abstract_slug(
            action.metadata.get("tipo_accion"), "accion_ambiental"
        ),
        "contexto_operacional": {
            "preset": problem.organizacion.preset,
            "categoria": _abstract_slug(problem.categoria, "ambiental"),
            "alcance": {
                "unidades": scopes.exclude(unidad_operacional=None).count(),
                "procesos": scopes.exclude(proceso_operacional=None).count(),
                "activos": scopes.exclude(activo_operacional=None).count(),
                "actividades": scopes.exclude(actividad_operacional=None).count(),
            },
        },
        "indicadores": indicators,
        "resultado": RESULT_MAP[result.estado],
        "metricas_comparadas": metrics,
        "grado_implementacion": implementation,
        "viabilidad": viability,
        "fuerza_evidencia": strength,
        "fundamento_evidencia": reasons,
        "origen_conocimiento": origin,
        "fecha_caso": result.fecha_evaluacion,
    }


def _verified_origin(result, ia_provenance, professional_review):
    if ia_provenance is not None:
        valid_ia = (
            isinstance(ia_provenance, HitoDecisionIA)
            and ia_provenance.organizacion_id == result.problematica.organizacion_id
            and ia_provenance.problematica_id == result.problematica_id
            and ia_provenance.tipo == HitoDecisionIA.Tipo.RESULTADO
        )
        if not valid_ia:
            raise ValidationError(
                "La procedencia IA no es verificable para esta intervencion."
            )
    if professional_review is not None:
        valid_professional = (
            isinstance(professional_review, RevisionProfesionalAmbiental)
            and professional_review.organizacion_id
            == result.problematica.organizacion_id
            and professional_review.tipo
            == RevisionProfesionalAmbiental.Tipo.INTERVENCION
            and professional_review.intervencion_id == result.id
            and professional_review.estado
            in {
                RevisionProfesionalAmbiental.Estado.VALIDADA,
                RevisionProfesionalAmbiental.Estado.VALIDADA_OBSERVACIONES,
            }
        )
        if not valid_professional:
            raise ValidationError(
                "La procedencia profesional no es verificable para esta intervencion."
            )
    if ia_provenance and professional_review:
        return CasoConocimientoAmbiental.Origen.MIXTO
    if ia_provenance:
        return CasoConocimientoAmbiental.Origen.IA
    if professional_review:
        return CasoConocimientoAmbiental.Origen.PROFESIONAL
    return CasoConocimientoAmbiental.Origen.USUARIO


@transaction.atomic
def create_knowledge_case(
    result, organization, *, ia_provenance=None, professional_review=None
):
    validate_knowledge_result(result, organization, RESULT_MAP)
    origin = _verified_origin(result, ia_provenance, professional_review)
    payload = _payload(result, origin)
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    latest = result.casos_conocimiento.order_by("-version").first()
    if latest and latest.fingerprint == fingerprint:
        return latest, False
    version = (latest.version if latest else 0) + 1
    state = (
        "utilizable"
        if payload["fuerza_evidencia"] in {"media", "alta"}
        else "candidato"
    )
    case = CasoConocimientoAmbiental.objects.create(
        organizacion=organization,
        resultado_origen=result,
        version=version,
        estado=state,
        fingerprint=fingerprint,
        metadata={},
        **payload,
    )
    return case, True


def aggregate_knowledge(**filters):
    rows = usable_knowledge(**filters)
    counts = knowledge_counts(rows, "resultado")
    strengths = knowledge_counts(rows, "fuerza_evidencia")
    return {
        "criterios": {key: value for key, value in filters.items() if value},
        "casos_comparables": rows.count(),
        "resultados": counts,
        "fuerza_evidencia": strengths,
    }


def compact_knowledge(problem):
    summary = aggregate_knowledge(
        preset=problem.organizacion.preset,
        categoria_ambiental=_abstract_slug(problem.categoria, "ambiental"),
        tipo_problematica=_abstract_slug(
            problem.metadata.get("tipo_problematica"),
            _abstract_slug(problem.categoria, "problematica_ambiental"),
        ),
    )
    return {
        "casos_comparables": summary["casos_comparables"],
        "resultados": summary["resultados"],
        "fuerza_evidencia": summary["fuerza_evidencia"],
        "mensaje": f"En casos comparables registrados se observaron {summary['resultados']}; esto no garantiza el resultado futuro.",
    }
