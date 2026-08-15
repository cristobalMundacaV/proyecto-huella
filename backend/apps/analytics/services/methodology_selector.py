from django.db.models import Q
from django.utils import timezone

from ..models import VersionMetodologia
from .eligibility_v2 import evaluate_formula


TRANSPORT_PRIORITY = ["transporte_tkm", "transporte_vehiculo_km", "transporte_combustible"]


def _applicability_reasons(version, activity):
    rules = version.aplicabilidad or {}
    reasons = []
    activity_types = rules.get("tipos_actividad")
    if activity_types and activity.tipo not in activity_types:
        reasons.append("El tipo de actividad no está incluido en la aplicabilidad.")
    flows = rules.get("flujos")
    if flows and version.metodologia.flujo not in flows:
        reasons.append("El flujo metodológico no está incluido en la aplicabilidad.")
    unit_ids = rules.get("unidad_operacional_ids")
    if unit_ids and activity.unidad_operacional_id not in unit_ids:
        reasons.append("La unidad operacional no está incluida en la aplicabilidad.")
    for field, expected in rules.get("atributos", {}).items():
        if getattr(activity, field, None) != expected:
            reasons.append(f"El atributo {field} no cumple la aplicabilidad.")
    return reasons


def _candidate_status(eligibility):
    if eligibility["estado"] == "no_calculable":
        if any("requiere revision" in reason.lower() for reason in eligibility["motivos"]):
            return "requiere_revision"
        return "no_calculable"
    return "aplicable"


def select_methodology(actividad):
    today = timezone.localdate()
    versions = VersionMetodologia.objects.filter(
        estado=VersionMetodologia.Estado.ACTIVA, metodologia__activa=True,
    ).filter(
        Q(metodologia__organizacion__isnull=True) | Q(metodologia__organizacion=actividad.organizacion),
        Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=today),
        Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=today),
    ).select_related("metodologia", "formula__factor_ambiental").prefetch_related("formula__variables")

    candidates = []
    for version in versions:
        applicability_reasons = _applicability_reasons(version, actividad)
        legacy_match = actividad.tipo == "transporte" and version.metodologia.flujo in TRANSPORT_PRIORITY
        configured_match = bool(version.aplicabilidad) and not applicability_reasons
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
        flow_rank = TRANSPORT_PRIORITY.index(item["metodo"]) if item["metodo"] in TRANSPORT_PRIORITY else 999
        tenant_rank = 0 if version.metodologia.organizacion_id == actividad.organizacion_id else 1
        return (version.prioridad, flow_rank, tenant_rank, -version.version, version.pk)

    candidates.sort(key=rank)
    available = [item for item in candidates if item["estado"] == "aplicable"]
    selected = available[0] if available else None
    discarded = [{"metodo": item["metodo"], "estado": item["estado"], "motivos": item["motivos"]}
                 for item in candidates if item is not selected and item["estado"] != "aplicable"]
    return {
        "seleccion": selected,
        "razon": (f"Seleccionado {selected['metodo']} por aplicabilidad y prioridad explícita."
                  if selected else "Ningún método aplicable es calculable."),
        "alternativos": [item for item in available if item is not selected],
        "descartados": discarded,
        "candidatos": candidates,
    }
