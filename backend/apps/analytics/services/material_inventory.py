"""MATERIAL-DATA-01E — read-only material environmental inventory & coverage.

No new authority: this module only reads MaterialOperacional, EventoMaterial
(recepcion), MaterialFactorMapping, FactorAmbiental/VersionFactorAmbiental
and CalculoAmbiental, and delegates the terminal calculable/no_calculable
verdict to the existing material_factor_selector. It exists purely to make
that verdict's structured reasons observable in aggregate, per material and
per reception, without duplicating the selection authority.
"""

from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from ..models import CalculoAmbiental, EventoMaterial, VersionFactorAmbiental
from ..models.material_factor_mapping import MaterialFactorMapping
from .material_factor_mapping import approved_mapping_for_date
from .material_factor_selector import select_material_factor
from .quality_v2 import evaluate_observation_quality
from .unit_conversion import (
    UNIT_DIMENSIONS,
    UnitConversionError,
    canonicalize_unit,
    convert_value,
)

INSUFFICIENT_QUALITY_STATES = {"requiere_revision", "no_confiable", "no_calculable"}


def _operational_date(value):
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def reception_coverage(event):
    """Structured, deterministic coverage diagnostic for one RECEPCION event."""
    material = event.material
    organization = event.organizacion
    effective_date = _operational_date(event.fecha_hora)
    observation = event.observacion_cantidad

    diagnostic = {
        "evento_id": event.id,
        "material_id": material.id,
        "material_codigo": material.codigo,
        "fecha_efectiva": effective_date,
        "recibido": True,
        "observacion_presente": bool(
            observation and observation.valor_numerico is not None and observation.unidad
        ),
        "mapeado": False,
        "mapping_aprobado_vigente": False,
        "factor_disponible": False,
        "factor_activo": False,
        "unidad_compatible": False,
        "calidad_suficiente": None,
        "calculable": False,
        "calculado": CalculoAmbiental.objects.filter(actividad_id=event.actividad_id).exists(),
        "razones": [],
        "cantidad_declarada": None,
        "unidad_declarada": None,
    }

    if not diagnostic["observacion_presente"]:
        diagnostic["razones"].append("observacion_faltante")
        return diagnostic

    diagnostic["cantidad_declarada"] = observation.valor_numerico
    diagnostic["unidad_declarada"] = observation.unidad

    any_mapping = MaterialFactorMapping.objects.filter(
        organizacion=organization, material=material
    ).exists()
    diagnostic["mapeado"] = any_mapping
    approved_at_date = None
    if not any_mapping:
        diagnostic["razones"].append("sin_mapping")
    else:
        approved_at_date = approved_mapping_for_date(
            organization, material, effective_date
        ).first()
        if approved_at_date:
            diagnostic["mapping_aprobado_vigente"] = True
        elif MaterialFactorMapping.objects.filter(
            organizacion=organization,
            material=material,
            estado=MaterialFactorMapping.Estado.APROBADO,
        ).exists():
            diagnostic["razones"].append("mapping_fuera_vigencia")
        else:
            diagnostic["razones"].append("mapping_no_aprobado")

    factor = approved_at_date.factor if approved_at_date else None
    if factor is not None:
        diagnostic["factor_disponible"] = True
        active_now = VersionFactorAmbiental.objects.filter(
            factor=factor, estado=VersionFactorAmbiental.Estado.ACTIVO
        )
        has_active_ever = active_now.exists()
        active_and_vigente = [
            v
            for v in active_now
            if (v.vigencia_desde is None or v.vigencia_desde <= effective_date)
            and (v.vigencia_hasta is None or v.vigencia_hasta >= effective_date)
        ]
        if active_and_vigente:
            diagnostic["factor_activo"] = True
        elif has_active_ever:
            diagnostic["razones"].append("factor_fuera_vigencia")
        else:
            diagnostic["razones"].append("sin_version_factor_activa")

    if diagnostic["factor_activo"]:
        try:
            convert_value(1, observation.unidad, factor.unidad_entrada)
            diagnostic["unidad_compatible"] = True
        except UnitConversionError:
            diagnostic["razones"].append("unidad_incompatible")

    quality = evaluate_observation_quality(observation, persist=False)
    diagnostic["calidad_suficiente"] = quality["estado"] not in INSUFFICIENT_QUALITY_STATES
    if not diagnostic["calidad_suficiente"]:
        diagnostic["razones"].append("dato_calidad_insuficiente")

    if diagnostic["razones"]:
        diagnostic["calculable"] = False
    else:
        selection = select_material_factor(
            organization, material, observation.unidad, effective_date
        )
        diagnostic["calculable"] = selection["status"] == "calculable"
        if not diagnostic["calculable"] and selection["reason"]:
            diagnostic["razones"].append(selection["reason"])

    diagnostic["razones"] = list(dict.fromkeys(diagnostic["razones"]))
    return diagnostic


def _receptions_queryset(organization, *, work=None, start=None, end=None, material=None, categoria=None):
    rows = EventoMaterial.objects.filter(
        organizacion=organization,
        tipo=EventoMaterial.Tipo.RECEPCION,
        estado=EventoMaterial.Estado.REGISTRADO,
    ).select_related("material", "observacion_cantidad", "obra", "actividad")
    if work is not None:
        rows = rows.filter(obra=work)
    if start:
        rows = rows.filter(fecha_hora__date__gte=start)
    if end:
        rows = rows.filter(fecha_hora__date__lte=end)
    if material is not None:
        rows = rows.filter(material=material)
    if categoria:
        rows = rows.filter(material__categoria=categoria)
    return rows.order_by("fecha_hora", "id")


def material_environmental_coverage(organization, *, work=None, start=None, end=None, material=None, categoria=None):
    """Deterministic coverage summary. Quantities are grouped by physical
    dimension (never summed across incompatible units)."""
    receptions = list(_receptions_queryset(
        organization, work=work, start=start, end=end, material=material, categoria=categoria
    ))
    diagnostics = [reception_coverage(event) for event in receptions]

    materials_seen = {event.material_id for event in receptions}
    materials_mapped = {
        diag["material_id"] for diag in diagnostics if diag["mapeado"]
    }

    reason_counts = defaultdict(int)
    for diag in diagnostics:
        if not diag["calculable"]:
            for reason in diag["razones"]:
                reason_counts[reason] += 1

    # Governed reference unit per known physical dimension (never inferred
    # density: mass and volume never merge; kg/t and L/m3/kWh/MWh do, because
    # unit_conversion already governs those conversions explicitly).
    dimension_reference_unit = {"masa": "kg", "volumen": "m3", "energia": "kWh"}
    dimensions = defaultdict(lambda: {"unidad": None, "total": Decimal("0"), "recepciones": 0})
    unrecognized_units = 0
    for diag in diagnostics:
        if diag["cantidad_declarada"] is None or not diag["unidad_declarada"]:
            continue
        try:
            canonical = canonicalize_unit(diag["unidad_declarada"])
        except UnitConversionError:
            unrecognized_units += 1
            continue
        dimension = UNIT_DIMENSIONS.get(canonical)
        if dimension and dimension in dimension_reference_unit:
            reference_unit = dimension_reference_unit[dimension]
            dimension_key = dimension
            try:
                normalized = convert_value(
                    diag["cantidad_declarada"], canonical, reference_unit
                )["valor_normalizado"]
            except UnitConversionError:
                unrecognized_units += 1
                continue
        else:
            # No governed cross-unit conversion for this unit (e.g. discrete
            # "unidad" counts): keep it in its own exact-unit bucket only.
            dimension_key = f"unidad:{canonical}"
            reference_unit = canonical
            normalized = diag["cantidad_declarada"]
        bucket = dimensions[dimension_key]
        bucket["unidad"] = reference_unit
        bucket["total"] += normalized
        bucket["recepciones"] += 1

    return {
        "materiales_totales": len(materials_seen),
        "materiales_mapeados": len(materials_mapped),
        "materiales_sin_mapping": len(materials_seen - materials_mapped),
        "recepciones_totales": len(diagnostics),
        "recepciones_calculables": sum(1 for d in diagnostics if d["calculable"]),
        "recepciones_no_calculables": sum(1 for d in diagnostics if not d["calculable"]),
        "recepciones_calculadas": sum(1 for d in diagnostics if d["calculado"]),
        "razones_no_calculable": dict(reason_counts),
        "cantidades_por_dimension": {
            key: {
                "unidad": bucket["unidad"],
                "total": bucket["total"],
                "recepciones": bucket["recepciones"],
            }
            for key, bucket in dimensions.items()
        },
        "unidades_no_reconocidas": unrecognized_units,
    }


def material_coverage_detail(organization, material, *, work=None, start=None, end=None):
    receptions = list(_receptions_queryset(
        organization, work=work, start=start, end=end, material=material
    ))
    diagnostics = [reception_coverage(event) for event in receptions]
    return {
        "material_id": material.id,
        "material_codigo": material.codigo,
        "material_nombre": material.nombre,
        "recepciones": diagnostics,
    }
