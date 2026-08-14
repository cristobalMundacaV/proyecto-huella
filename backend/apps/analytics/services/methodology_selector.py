from ..models import VersionMetodologia
from .eligibility_v2 import evaluate_formula


TRANSPORT_PRIORITY = ["transporte_tkm", "transporte_vehiculo_km", "transporte_combustible"]


def select_methodology(actividad):
    if actividad.tipo != "transporte":
        return {"seleccion": None, "razon": "No hay metodologias v2 configuradas para este tipo de actividad.", "alternativos": [], "descartados": []}
    versions = VersionMetodologia.objects.filter(
        estado=VersionMetodologia.Estado.ACTIVA,
        metodologia__activa=True,
        metodologia__flujo__in=TRANSPORT_PRIORITY,
        metodologia__organizacion__in=[None, actividad.organizacion],
    ).select_related("metodologia", "formula__factor_ambiental").prefetch_related("formula__variables")
    by_flow = {}
    for version in versions.order_by("-version"):
        by_flow.setdefault(version.metodologia.flujo, version)
    available, discarded = [], []
    for flow in TRANSPORT_PRIORITY:
        version = by_flow.get(flow)
        if not version:
            discarded.append({"metodo": flow, "motivos": ["Metodologia activa no disponible."]})
            continue
        result = evaluate_formula(actividad, version.formula)
        item = {"metodo": flow, "version_metodologia": version, "formula": version.formula, "elegibilidad": result}
        if result["estado"] != "no_calculable":
            available.append(item)
        else:
            discarded.append({"metodo": flow, "motivos": result["motivos"]})
    selected = available[0] if available else None
    return {"seleccion": selected, "razon": f"Seleccionado {selected['metodo']} por prioridad deterministica." if selected else "Ningun metodo es calculable.",
            "alternativos": available[1:], "descartados": discarded}
