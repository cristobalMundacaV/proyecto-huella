from django.db.models import Q
from django.utils import timezone

from ..models import VersionMetodologia
from .eligibility_v2 import evaluate_formula


def _applicability_reasons(version, activity):
    rules = version.aplicabilidad or {}
    reasons = []
    record = getattr(activity, "registro_flujo_ambiental", None)
    activity_types = rules.get("tipos_actividad")
    if activity_types and activity.tipo not in activity_types:
        reasons.append("El tipo de actividad no está incluido en la aplicabilidad.")
    flows = rules.get("flujos")
    if flows and (not record or record.flujo not in flows):
        reasons.append("El flujo metodológico no está incluido en la aplicabilidad.")
    resource_types = rules.get("tipos_recurso")
    if resource_types and (not record or record.tipo_recurso not in resource_types):
        reasons.append("El tipo de recurso no esta incluido en la aplicabilidad.")
    material_event_types = rules.get("tipos_evento_material")
    if material_event_types:
        material_event = getattr(activity, "evento_material", None)
        if not material_event or material_event.tipo not in material_event_types:
            reasons.append(
                "Este movimiento no es un punto contable de la metodologia de material recibido."
            )
    unit_ids = rules.get("unidad_operacional_ids")
    if unit_ids and activity.unidad_operacional_id not in unit_ids:
        reasons.append("La unidad operacional no está incluida en la aplicabilidad.")
    for field, expected in rules.get("atributos", {}).items():
        if getattr(activity, field, None) != expected:
            reasons.append(f"El atributo {field} no cumple la aplicabilidad.")
    return reasons


def _candidate_status(eligibility):
    if eligibility["estado"] == "no_calculable":
        factor_selection = eligibility.get("seleccion_factor_combustible") or {}
        if factor_selection.get("estado") == "requiere_revision":
            return "requiere_revision"
        if any("requiere revision" in reason.lower() for reason in eligibility["motivos"]):
            return "requiere_revision"
        return "no_calculable"
    return "aplicable"


def _implicit_flow_match(version, activity):
    record = getattr(activity, "registro_flujo_ambiental", None)
    if record:
        methodology_flow = version.metodologia.flujo
        if methodology_flow == record.flujo:
            return True
        if methodology_flow == "combustible" and record.flujo.startswith("combustible"):
            return True
    return activity.tipo == "transporte" and version.formula.tipo.startswith("transporte_")


def select_methodology(actividad):
    record = getattr(actividad, "registro_flujo_ambiental", None)
    operational_timestamp = (
        record.periodo_inicio if record else actividad.timestamp_inicio
    )
    if timezone.is_aware(operational_timestamp):
        operational_timestamp = timezone.localtime(operational_timestamp)
    effective_date = operational_timestamp.date()
    versions = VersionMetodologia.objects.filter(
        estado=VersionMetodologia.Estado.ACTIVA, metodologia__activa=True,
    ).filter(
        Q(metodologia__organizacion__isnull=True) | Q(metodologia__organizacion=actividad.organizacion),
        Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=effective_date),
        Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=effective_date),
    ).select_related("metodologia", "formula__factor_ambiental").prefetch_related("formula__variables")

    candidates = []
    for version in versions:
        applicability_reasons = _applicability_reasons(version, actividad)
        legacy_match = _implicit_flow_match(version, actividad)
        if (version.aplicabilidad and applicability_reasons) or (not version.aplicabilidad and not legacy_match):
            candidates.append({"metodo": version.metodologia.flujo, "version_metodologia": version,
                               "estado": "no_aplicable", "motivos": applicability_reasons or ["Flujo no aplicable a la actividad."]})
            continue
        eligibility = evaluate_formula(actividad, version.formula)
        candidates.append({"metodo": version.metodologia.flujo, "version_metodologia": version,
                           "formula": version.formula, "elegibilidad": eligibility,
                           "estado": _candidate_status(eligibility), "motivos": eligibility["motivos"]})

    def rank(item):
        version = item["version_metodologia"]
        return (version.prioridad, item["estado"] == "no_aplicable", version.pk)

    candidates.sort(key=rank)
    available = [item for item in candidates if item["estado"] == "aplicable"]
    best = [item for item in available if item["version_metodologia"].prioridad == available[0]["version_metodologia"].prioridad] if available else []
    ambiguous = len(best) > 1
    selected = best[0] if len(best) == 1 else None
    applicable_candidates = [
        item for item in candidates if item["estado"] != "no_aplicable"
    ]
    best_candidates = (
        [
            item
            for item in applicable_candidates
            if item["version_metodologia"].prioridad
            == applicable_candidates[0]["version_metodologia"].prioridad
        ]
        if applicable_candidates
        else []
    )
    methodology_ambiguous = ambiguous or len(best_candidates) > 1
    if methodology_ambiguous:
        selected = None
    candidate = best_candidates[0] if not selected and len(best_candidates) == 1 else None
    if selected:
        reason = (
            f"Seleccionado {selected['metodo']} por aplicabilidad y prioridad explícita."
        )
    elif methodology_ambiguous:
        reason = "Existen múltiples metodologías aplicables con igual prioridad."
    else:
        reason = "Ningún método aplicable es calculable."
    discarded = [{"metodo": item["metodo"], "estado": item["estado"], "motivos": item["motivos"]}
                 for item in candidates if item is not selected and item["estado"] != "aplicable"]
    only_not_applicable = bool(candidates) and all(item["estado"] == "no_aplicable" for item in candidates)
    return {
        "seleccion": selected,
        "candidata": candidate,
        "requiere_revision_metodologica": methodology_ambiguous,
        "razon": reason,
        "estado": "requiere_revision" if methodology_ambiguous else (selected["elegibilidad"]["estado"] if selected else ("no_aplicable" if only_not_applicable else "no_calculable")),
        "alternativos": [item for item in available if item is not selected],
        "descartados": discarded,
        "candidatos": candidates,
    }
