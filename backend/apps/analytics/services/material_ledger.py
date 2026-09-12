"""MATERIAL-DATA-01G — material A1-A3 accounting ledger.

No new ledger model: ``CalculoAmbiental`` (already append-only/immutable,
already carries ``recalculo_de`` lineage) *is* the ledger. This module only
adds the selectors needed to consume it correctly for material A1-A3
accounting: which entry is the *current* representation for a reception
(never the superseded ones, so totals are never double-counted), and how to
aggregate/walk its provenance without inventing a second authority.
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import OuterRef, Subquery

from ..models import CalculoAmbiental, EventoMaterial, FormulaAmbiental


def _material_calculos():
    return CalculoAmbiental.objects.filter(formula__tipo=FormulaAmbiental.Tipo.MATERIAL_CANTIDAD)


def current_calculations_queryset(base=None):
    """Only the non-superseded (leaf) calculation per actividad: the one no
    other calculation's ``recalculo_de`` points at."""
    base = _material_calculos() if base is None else base
    superseded_ids = CalculoAmbiental.objects.filter(
        recalculo_de__isnull=False
    ).values_list("recalculo_de_id", flat=True)
    return base.exclude(pk__in=Subquery(superseded_ids))


def current_calculation_for_activity(actividad):
    return current_calculations_queryset(
        CalculoAmbiental.objects.filter(actividad=actividad)
    ).order_by("-version_interna").first()


def ledger_entries(organization, *, work=None, material=None, start=None, end=None, categoria=None, standard=None, include_superseded=False):
    base = _material_calculos().filter(organizacion=organization).select_related(
        "actividad", "actividad__obra", "version_factor__factor", "recalculo_de"
    )
    if not include_superseded:
        base = current_calculations_queryset(base)
    receptions = EventoMaterial.objects.filter(
        organizacion=organization, tipo=EventoMaterial.Tipo.RECEPCION,
    ).select_related("material", "obra")
    if work is not None:
        receptions = receptions.filter(obra=work)
    if material is not None:
        receptions = receptions.filter(material=material)
    if categoria:
        receptions = receptions.filter(material__categoria=categoria)
    activity_ids = set(receptions.values_list("actividad_id", flat=True))
    base = base.filter(actividad_id__in=activity_ids)
    if start:
        base = base.filter(fecha_calculo__date__gte=start)
    if end:
        base = base.filter(fecha_calculo__date__lte=end)
    if standard:
        base = base.filter(snapshot_tecnico__factor_contexto__standard=standard)
    return base.order_by("-fecha_calculo")


def ledger_entry_provenance(calculo):
    """Full auditable trail for one ledger entry, reconstructed only from
    already-persisted, immutable data (the calculation's own snapshot plus
    the mapping/candidate rows it references by id)."""
    from ..models import EventoMaterial
    from ..models.material_factor_mapping import MaterialFactorMapping
    from .material_quality import assess_factor_data_quality

    snapshot = calculo.snapshot_tecnico or {}
    material_info = snapshot.get("material") or {}
    mapping_info = snapshot.get("mapeo_material_factor") or {}
    mapping = None
    if mapping_info.get("mapping_id"):
        mapping = MaterialFactorMapping.objects.filter(pk=mapping_info["mapping_id"]).select_related("material", "factor").first()
    event = EventoMaterial.objects.filter(actividad_id=calculo.actividad_id).select_related("material").first()
    factor = calculo.version_factor.factor
    quality = assess_factor_data_quality(factor)
    candidate = getattr(factor, "material_source_candidate", None)
    return {
        "calculo_id": calculo.id,
        "actividad_id": calculo.actividad_id,
        "evento_recepcion_id": event.id if event else None,
        "material": material_info or ({"id": event.material_id, "codigo": event.material.codigo} if event else None),
        "resultado": calculo.resultado,
        "unidad_resultado": calculo.unidad_resultado,
        "tipo_resultado": calculo.tipo_resultado,
        "standard": snapshot.get("factor_contexto", {}).get("standard"),
        "boundary": snapshot.get("factor_contexto", {}).get("boundary", "A1-A3"),
        "mapping": (
            {
                "id": mapping.id,
                "estado": mapping.estado,
                "vigencia_desde": mapping.vigencia_desde,
                "vigencia_hasta": mapping.vigencia_hasta,
            }
            if mapping
            else mapping_info or None
        ),
        "factor_id": factor.id,
        "version_factor_id": calculo.version_factor_id,
        "candidate_id": candidate.id if candidate else snapshot.get("factor_contexto", {}).get("source_candidate_id"),
        "process_uuid": snapshot.get("factor_contexto", {}).get("process_uuid"),
        "dataset_version": snapshot.get("factor_contexto", {}).get("dataset_version"),
        "quality": quality,
        "recalculo_de_id": calculo.recalculo_de_id,
        "es_recalculo": calculo.recalculo_de_id is not None,
        "fue_recalculado": CalculoAmbiental.objects.filter(recalculo_de_id=calculo.id).exists(),
        "version_interna": calculo.version_interna,
        "fecha_calculo": calculo.fecha_calculo,
    }


def _dimension_key(unidad):
    return unidad or "sin_unidad"


def material_ledger_totals(organization, *, work=None, material=None, start=None, end=None, categoria=None, standard=None, group_by=None):
    """Sum current (non-superseded) A1-A3 results, grouped by
    unidad_resultado (never mixed) and optionally by one grouping key.
    Negative values are preserved exactly as computed (Decimal, no abs/clamp)."""
    entries = list(ledger_entries(
        organization, work=work, material=material, start=start, end=end,
        categoria=categoria, standard=standard,
    ))
    totals = defaultdict(lambda: {"total": Decimal("0"), "entradas": 0})
    groups = defaultdict(lambda: defaultdict(lambda: {"total": Decimal("0"), "entradas": 0}))
    for entry in entries:
        unit_key = _dimension_key(entry.unidad_resultado)
        totals[unit_key]["total"] += entry.resultado
        totals[unit_key]["entradas"] += 1
        if group_by:
            group_value = _group_value(entry, group_by)
            bucket = groups[group_value][unit_key]
            bucket["total"] += entry.resultado
            bucket["entradas"] += 1
    result = {
        "totales_por_unidad": dict(totals),
        "entradas_totales": len(entries),
    }
    if group_by:
        result["por_grupo"] = {
            key: dict(value) for key, value in groups.items()
        }
    return result


def _group_value(entry, group_by):
    if group_by == "obra":
        return entry.actividad.obra_id
    if group_by == "material":
        return (entry.snapshot_tecnico or {}).get("material", {}).get("id")
    if group_by == "categoria":
        return (entry.snapshot_tecnico or {}).get("material", {}).get("categoria")
    if group_by == "standard":
        return (entry.snapshot_tecnico or {}).get("factor_contexto", {}).get("standard")
    if group_by == "periodo":
        return entry.fecha_calculo.date().isoformat()[:7]
    raise ValueError(f"Agrupación no soportada: {group_by}")
