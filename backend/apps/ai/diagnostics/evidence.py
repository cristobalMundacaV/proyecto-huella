"""AI-INTELLIGENCE-03 — shared evidence/quality/factor aggregation.

Extracted so `apps.ai.tools.get_evidence_quality` (one material) and the
diagnostics rules (DIAG-05/06/07/08 — many materials in one categoria/obra
scope) share exactly one query path over `EventoMaterial`/`Observacion`/
`EvaluacionCalidadDato` — never two independent implementations of the
same "does this consumption record have evidence/quality/factor" question.

Three axes stay explicitly separate, same as `get_evidence_quality`:
registro de consumo, evidencia operacional, calidad del dato — plus, for
diagnostics, factor ambiental mapeado per material.
"""
from datetime import date as date_cls

from apps.analytics.models.materials import EventoMaterial
from apps.analytics.models.quality import EvaluacionCalidadDato
from apps.analytics.services.material_factor_selector import select_material_factor

from .rules import DATA_QUALITY_POOR_STATES


def events_for_scope(organization, *, materials, obra=None, start=None, end=None):
    events = EventoMaterial.objects.filter(
        organizacion=organization, material__in=materials, estado=EventoMaterial.Estado.REGISTRADO,
    ).select_related("observacion_cantidad", "material")
    if obra is not None:
        events = events.filter(obra=obra)
    if start:
        events = events.filter(fecha_hora__date__gte=start)
    if end:
        events = events.filter(fecha_hora__date__lte=end)
    return list(events.order_by("-fecha_hora"))


def _has_evidence(event):
    return bool(event.evidencia_id or (event.observacion_cantidad_id and event.observacion_cantidad.evidencia_id))


def gather_evidence_stats(organization, *, materials, obra=None, start=None, end=None):
    """Aggregated evidence/quality/factor coverage across every
    `EventoMaterial` reception for `materials` in scope. Returns a plain
    dict — never a queryset — so both `get_evidence_quality` and the
    diagnostics rules can consume it without touching the ORM again."""
    events = events_for_scope(organization, materials=materials, obra=obra, start=start, end=end)
    total_eventos = len(events)
    con_evidencia = sum(1 for event in events if _has_evidence(event))

    observacion_ids = [event.observacion_cantidad_id for event in events if event.observacion_cantidad_id]
    evaluaciones = list(
        EvaluacionCalidadDato.objects.filter(organizacion=organization, observacion_id__in=observacion_ids)
        .values_list("observacion_id", "estado")
    ) if observacion_ids else []
    estado_by_observacion = dict(evaluaciones)
    estado_counts = {}
    for _, estado in evaluaciones:
        estado_counts[estado] = estado_counts.get(estado, 0) + 1
    evaluated_observacion_ids = set(estado_by_observacion.keys())
    poor_observacion_ids = {
        observacion_id for observacion_id, estado in estado_by_observacion.items()
        if estado in DATA_QUALITY_POOR_STATES
    }

    unsupported_count = sum(
        1 for event in events
        if not _has_evidence(event) and event.observacion_cantidad_id in poor_observacion_ids
    )

    today = date_cls.today()
    unmapped_materials = []
    per_material_events = {}
    for event in events:
        per_material_events.setdefault(event.material_id, []).append(event)
    for material in materials:
        material_events = per_material_events.get(material.id)
        if not material_events:
            continue
        selection = select_material_factor(organization, material, material.unidad_base, today)
        if selection["status"] != "calculable":
            unmapped_materials.append({
                "material_id": material.id, "nombre": material.nombre, "eventos": len(material_events),
                "razon": selection.get("reason"),
            })

    return {
        "total_eventos": total_eventos,
        "con_evidencia": con_evidencia,
        "estado_counts": estado_counts,
        "evaluated_count": len(evaluated_observacion_ids),
        "poor_count": len(poor_observacion_ids),
        "unsupported_count": unsupported_count,
        "unmapped_materials": unmapped_materials,
        "observaciones_sin_evaluar": len(observacion_ids) - len(evaluated_observacion_ids),
        "ultimo_evento": events[0].fecha_hora if events else None,
    }
