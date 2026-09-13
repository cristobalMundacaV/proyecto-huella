"""AI-INTELLIGENCE-01/02 — read-only backend tools.

Every tool is a thin, tenant-checked adapter over an already-existing,
deterministic service (`ContextGateway`, `material_hotspots`,
`material_opportunities`, `material_ledger`, `material_quality`, the `ec3`
app, `apps.knowledge`, and — since AI-INTELLIGENCE-02 — `analytics_tools`,
`resolvers`, `periods`). No tool computes anything itself, no tool mutates
anything, and no tool ever returns more than a bounded number of rows. The
LLM never sees a raw queryset or a raw model instance — only these plain
dict payloads.

Every tool function has the signature `(organization, user, **arguments)`
and returns a plain JSON-serializable dict. A tool NEVER raises for an
authorization failure — it returns `{"ok": False, "error": "permission_denied", ...}`
so the orchestrator can feed that back to the model as a normal (non-fatal)
tool result and the conversation continues; the model then explains the
limitation to the user rather than the whole turn failing.
"""
from datetime import date as date_cls

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from apps.analytics.models import IndicadorAmbiental, MaterialOperacional, Obra, ProblematicaAmbiental
from apps.analytics.permissions import Permission, has_tenant_permission, require_work_access
from apps.analytics.selectors.environmental_flows import work_for_organization
from apps.analytics.services.context_gateway import ContextGateway
from apps.analytics.services.material_factor_selector import select_material_factor
from apps.analytics.services.material_hotspots import material_hotspots
from apps.analytics.services.material_ledger import (
    current_calculations_queryset, ledger_entry_provenance, material_ledger_totals,
)
from apps.analytics.services.material_quality import assess_factor_data_quality
from apps.ec3.models import Candidate
from apps.ec3.opportunity import material_candidate_opportunities
from apps.ec3.services import candidate_data
from apps.knowledge.models import EnvironmentalSource, ExternalRecord

from . import analytics_tools
from .resolvers import RESOLVERS

MAX_ROWS = 15
RIESGO_WEIGHT = {"critico": 3, "alto": 2, "medio": 1, "bajo": 0}
CLOSED_PROBLEM_STATES = {
    ProblematicaAmbiental.Estado.CERRADA, ProblematicaAmbiental.Estado.RESUELTA,
    ProblematicaAmbiental.Estado.NO_RESUELTA,
}


def _denied(reason):
    return {"ok": False, "error": "permission_denied", "reason": reason}


def _not_found(reason):
    return {"ok": False, "error": "not_found", "reason": reason}


def _guarded(user, organization, permission):
    if not has_tenant_permission(user, organization, permission):
        return _denied(f"El usuario no tiene el permiso '{permission}' requerido para esta consulta.")
    return None


def _resolve_material(organization, user, material_id):
    material = MaterialOperacional.objects.filter(organizacion=organization, pk=material_id).first()
    if material is None:
        return None, _not_found(f"No existe el material {material_id} en esta organización.")
    return material, None


def _resolve_obra(organization, user, obra_id):
    if not obra_id:
        return None, None
    obra = work_for_organization(organization, obra_id).first()
    if obra is None:
        return None, _not_found(f"No existe la obra {obra_id} en esta organización.")
    try:
        require_work_access(user, organization, obra)
    except Http404:
        return None, _not_found(f"No existe la obra {obra_id} en esta organización.")
    return obra, None


def _resolve_obra_arg(organization, user, obra_id, obra_name):
    """AI-INTELLIGENCE macrofase: shared obra resolution for every tool
    that accepts EITHER `obra_id` OR a free-text `obra` name — resolves
    the name via `resolvers.resolve_obra` (RBAC-aware) and never asks the
    caller to guess an id. Returns (obra, error_or_ambiguous_response,
    resolved_early). `resolved_early` is truthy when the caller should
    return `error_or_ambiguous_response` immediately (not_found/ambiguous
    are informational, ok=True, results — not fatal errors)."""
    from .resolvers import resolve_obra as resolve_obra_by_name

    if not obra_id and not obra_name:
        return None, {"ok": False, "error": "missing_argument", "reason": "Se requiere obra_id u obra (nombre)."}, True
    if obra_id:
        obra_obj, error = _resolve_obra(organization, user, obra_id)
        if error:
            return None, error, True
        return obra_obj, None, False
    resolution = resolve_obra_by_name(organization, user, obra_name)
    if resolution["status"] in ("not_found", "ambiguous"):
        return None, {"ok": True, "data": resolution}, True
    obra_obj, error = _resolve_obra(organization, user, resolution["match"]["id"])
    if error:
        return None, error, True
    return obra_obj, None, False


def _resolve_material_arg(organization, user, material_id, material_name):
    """Same pattern as `_resolve_obra_arg`, for material_id/material."""
    from .resolvers import resolve_material as resolve_material_by_name

    if not material_id and not material_name:
        return None, None, False
    if material_id:
        material_obj, error = _resolve_material(organization, user, material_id)
        if error:
            return None, error, True
        return material_obj, None, False
    resolution = resolve_material_by_name(organization, material_name)
    if resolution["status"] in ("not_found", "ambiguous"):
        return None, {"ok": True, "data": resolution}, True
    material_obj, error = _resolve_material(organization, user, resolution["match"]["id"])
    if error:
        return None, error, True
    return material_obj, None, False


def get_current_organization(organization, user, **_):
    return {"ok": True, "data": {
        "organizacion_id": organization.organizacion_id,
        "nombre": organization.nombre,
        "preset": organization.preset,
        "activa": organization.activa,
    }}


def list_projects(organization, user, **_):
    guard = _guarded(user, organization, Permission.WORK_VIEW)
    if guard:
        return guard
    from apps.analytics.permissions import filter_works_for_user
    from apps.analytics.models import Obra

    obras = filter_works_for_user(Obra.objects.filter(organizacion=organization), user, organization)
    rows = list(obras.order_by("-fecha_inicio").values(
        "id", "nombre", "estado", "fecha_inicio", "fecha_termino_estimada",
    )[:MAX_ROWS])
    return {"ok": True, "data": {"obras": rows, "total_mostrado": len(rows), "limite": MAX_ROWS}}


def get_project_summary(organization, user, obra_id=None, **_):
    guard = _guarded(user, organization, Permission.WORK_VIEW)
    if guard:
        return guard
    if not obra_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere obra_id."}
    obra, error = _resolve_obra(organization, user, obra_id)
    if error:
        return error
    return {"ok": True, "data": ContextGateway().work(obra, organization)}


def get_environmental_indicators(organization, user, obra_id=None, codigo=None, **_):
    guard = _guarded(user, organization, Permission.INDICATOR_VIEW)
    if guard:
        return guard
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    indicators = IndicadorAmbiental.objects.filter(organizacion=organization, activo=True)
    indicators = indicators.filter(obra=obra) if obra else indicators.filter(alcance=IndicadorAmbiental.Alcance.ORGANIZACION)
    if codigo:
        indicators = indicators.filter(codigo=codigo)
    rows = []
    for indicator in indicators.order_by("codigo")[:MAX_ROWS]:
        latest = indicator.valores.order_by("-periodo_fin", "-version").first()
        rows.append({
            "id": indicator.id, "codigo": indicator.codigo, "nombre": indicator.nombre,
            "tipo": indicator.tipo, "unidad": indicator.unidad, "alcance": indicator.alcance,
            "direccion_deseable": indicator.direccion_deseable,
            "ultimo_valor": latest.valor if latest else None,
            "ultimo_periodo_fin": latest.periodo_fin if latest else None,
        })
    return {"ok": True, "data": {"indicadores": rows, "total_mostrado": len(rows), "limite": MAX_ROWS}}


def get_emissions_summary(organization, user, obra_id=None, start=None, end=None, categoria=None, **_):
    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    totals = material_ledger_totals(
        organization, work=obra, start=_parse_date(start), end=_parse_date(end), categoria=categoria or None,
    )
    return {"ok": True, "data": totals}


def get_material_summary(organization, user, material_id=None, obra_id=None, **_):
    guard = _guarded(user, organization, Permission.MATERIAL_MAPPING_VIEW)
    if guard:
        return guard
    if not material_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere material_id."}
    material, error = _resolve_material(organization, user, material_id)
    if error:
        return error
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    return {"ok": True, "data": ContextGateway().material_intelligence(material, organization, work=obra)}


def get_material_hotspots(organization, user, obra_id=None, categoria=None, standard=None, **_):
    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    result = material_hotspots(organization, work=obra, categoria=categoria or None, standard=standard or None)
    trimmed = {}
    for unit, payload in result.items():
        trimmed[unit] = {**payload, "materiales": payload["materiales"][:MAX_ROWS]}
    return {"ok": True, "data": trimmed}


def get_evidence_quality(organization, user, material_id=None, material=None, obra_id=None,
                          date_from=None, date_to=None, relative_months=None, **_):
    """Reports four DISTINCT axes for a material — never conflated:
    (a) whether a consumption record (`EventoMaterial`) exists at all;
    (b) whether evidence (`EvidenciaObra`) is attached to those records;
    (c) the data-quality evaluation (`EvaluacionCalidadDato`) of the
        underlying observations, if any exist;
    (d) whether a governed environmental factor is mapped for the material
        (unchanged from AI-INTELLIGENCE-01 — `select_material_factor` +
        `assess_factor_data_quality`).
    "No hay evidencia" and "no hay factor ambiental" are different facts
    about different things and must never be reported as one.

    Accepts a material NAME (`material`, e.g. "agua") as an alternative to
    `material_id` — resolved internally via `resolvers.resolve_material` —
    so the model never has to ask the user for an id when it already has a
    name to work with."""
    from .diagnostics.evidence import gather_evidence_stats
    from .periods import resolve_period
    from .resolvers import resolve_material as resolve_material_by_name

    guard = _guarded(user, organization, Permission.EVIDENCE_VIEW)
    if guard:
        return guard
    if not material_id and not material:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere material_id o material (nombre/categoría)."}
    if material_id:
        material_obj, error = _resolve_material(organization, user, material_id)
        if error:
            return error
    else:
        resolution = resolve_material_by_name(organization, material)
        if resolution["status"] == "not_found":
            return _not_found(f"No se encontró ningún material que coincida con '{material}' en esta organización.")
        if resolution["status"] == "ambiguous":
            return {"ok": True, "data": {"status": "ambiguous", "candidates": resolution["candidates"]}}
        material_obj, error = _resolve_material(organization, user, resolution["match"]["id"])
        if error:
            return error
    material = material_obj
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    start, end = resolve_period(date_from=date_from, date_to=date_to, relative_months=relative_months)

    stats = gather_evidence_stats(organization, materials=[material], obra=obra, start=start, end=end)

    registro_consumo = {
        "existe": stats["total_eventos"] > 0,
        "cantidad_eventos": stats["total_eventos"],
        "ultimo_evento": stats["ultimo_evento"],
    }
    evidencia_operacional = {
        "existe": stats["con_evidencia"] > 0,
        "eventos_con_evidencia": stats["con_evidencia"],
        "eventos_totales": stats["total_eventos"],
        "cobertura": (stats["con_evidencia"] / stats["total_eventos"]) if stats["total_eventos"] else None,
    }
    calidad_dato = {
        "evaluado": stats["evaluated_count"] > 0,
        "distribucion_estados": stats["estado_counts"],
        "observaciones_sin_evaluar": stats["observaciones_sin_evaluar"],
    }

    selection = select_material_factor(organization, material, material.unidad_base, date_cls.today())
    if selection["status"] != "calculable":
        factor_ambiental = {"mapeado": False, "razon": selection["reason"]}
    else:
        factor_ambiental = {"mapeado": True, "calidad": assess_factor_data_quality(selection["factor_version"].factor)}

    return {"ok": True, "data": {
        "material_id": material.pk,
        "registro_consumo": registro_consumo,
        "evidencia_operacional": evidencia_operacional,
        "calidad_dato": calidad_dato,
        "factor_ambiental": factor_ambiental,
    }}


def get_open_alerts(organization, user, obra_id=None, **_):
    guard = _guarded(user, organization, Permission.PROBLEM_VIEW)
    if guard:
        return guard
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    problems = ProblematicaAmbiental.objects.filter(organizacion=organization).exclude(estado__in=CLOSED_PROBLEM_STATES)
    if obra:
        problems = problems.filter(obra=obra)
    rows = [
        {
            "id": row.id, "titulo": row.titulo, "categoria": row.categoria,
            "estado": row.estado, "riesgo": row.nivel_riesgo, "obra_id": row.obra_id,
        }
        for row in problems.order_by("-created_at")[:MAX_ROWS]
    ]
    rows.sort(key=lambda row: RIESGO_WEIGHT.get(row["riesgo"], -1), reverse=True)
    return {"ok": True, "data": {"alertas": rows, "total_mostrado": len(rows), "limite": MAX_ROWS}}


def get_ec3_mapping_status(organization, user, material_id=None, **_):
    guard = _guarded(user, organization, Permission.MATERIAL_MAPPING_VIEW)
    if guard:
        return guard
    if not material_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere material_id."}
    material, error = _resolve_material(organization, user, material_id)
    if error:
        return error
    candidates = Candidate.objects.filter(material=material).order_by("pk")[:MAX_ROWS]
    rows = [candidate_data(candidate) for candidate in candidates]
    return {"ok": True, "data": {"material_id": material.pk, "candidatos_ec3": rows}}


def get_ec3_opportunities(organization, user, material_id=None, lcia_method="EF 3.0", **_):
    guard = _guarded(user, organization, Permission.MATERIAL_MAPPING_VIEW)
    if guard:
        return guard
    if not material_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere material_id."}
    material, error = _resolve_material(organization, user, material_id)
    if error:
        return error
    preview = material_candidate_opportunities(organization, material, lcia_method)
    return {"ok": True, "data": preview}


def get_factor_provenance(organization, user, calculo_id=None, **_):
    guard = _guarded(user, organization, Permission.FACTOR_VIEW)
    if guard:
        return guard
    if not calculo_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere calculo_id."}
    calculo = current_calculations_queryset().filter(organizacion=organization, pk=calculo_id).first()
    if calculo is None:
        return _not_found(f"No existe el cálculo {calculo_id} vigente en esta organización.")
    return {"ok": True, "data": ledger_entry_provenance(calculo)}


def get_historical_trends(organization, user, indicador_id=None, **_):
    guard = _guarded(user, organization, Permission.INDICATOR_VIEW)
    if guard:
        return guard
    if not indicador_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere indicador_id."}
    indicator = IndicadorAmbiental.objects.filter(organizacion=organization, pk=indicador_id).first()
    if indicator is None:
        return _not_found(f"No existe el indicador {indicador_id} en esta organización.")
    return {"ok": True, "data": ContextGateway().indicator_history(indicator, organization)}


def resolve_entity(organization, user, entity_type=None, query=None, **_):
    """Resolves a free-text reference ("agua", "hormigón", an obra's name,
    an asset's name) against the tenant's REAL data — never an internal
    id guessed by the model. Returns exactly one match, several candidates
    (ambiguous), or none — the model must never ask the user for an id or
    a full list when this can resolve it directly."""
    if entity_type not in RESOLVERS:
        return {"ok": False, "error": "invalid_argument", "reason": f"entity_type debe ser uno de: {sorted(RESOLVERS)}."}
    if not query or not query.strip():
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere query."}
    result = RESOLVERS[entity_type](organization, user, query)
    return {"ok": True, "data": result}


def get_operational_timeseries(organization, user, obra_id=None, material_id=None, metric=None, categoria=None,
                                date_from=None, date_to=None, relative_months=None, **_):
    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    if not metric and not categoria and not material_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere metric (agua/energia/combustible/residuo/materiales), categoria o material_id."}
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    material, error = _resolve_material(organization, user, material_id) if material_id else (None, None)
    if error:
        return error
    result = analytics_tools.operational_timeseries(
        organization, user, obra=obra, material=material, metric=metric, categoria=categoria,
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )
    return result


def get_operational_aggregate(organization, user, obra_id=None, material_id=None, metric=None, categoria=None,
                               date_from=None, date_to=None, relative_months=None, **_):
    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    if not metric and not categoria and not material_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere metric (agua/energia/combustible/residuo/materiales), categoria o material_id."}
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    material, error = _resolve_material(organization, user, material_id) if material_id else (None, None)
    if error:
        return error
    result = analytics_tools.operational_aggregate(
        organization, user, obra=obra, material=material, metric=metric, categoria=categoria,
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )
    return result


def rank_operational_entities(organization, user, entity_type=None, metric=None, obra_id=None,
                               categoria=None, date_from=None, date_to=None,
                               relative_months=None, top_n=10, **_):
    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    if entity_type not in {"obra", "material", "categoria", "standard", "activo", "periodo"}:
        return {"ok": False, "error": "invalid_argument", "reason": "entity_type debe ser uno de: obra, material, categoria, standard, activo, periodo."}
    obra, error = _resolve_obra(organization, user, obra_id) if obra_id else (None, None)
    if error:
        return error
    result = analytics_tools.rank_operational_entities(
        organization, user, entity_type=entity_type, metric=metric, obra=obra, categoria=categoria,
        date_from=date_from, date_to=date_to, relative_months=relative_months, top_n=top_n,
    )
    return result


def compare_projects(organization, user, metric=None, categoria=None, date_from=None,
                      date_to=None, relative_months=None, top_n=5, **_):
    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    result = analytics_tools.compare_projects(
        organization, user, metric=metric, categoria=categoria,
        date_from=date_from, date_to=date_to, relative_months=relative_months, top_n=top_n,
    )
    return result


def diagnose_environmental_performance(organization, user, obra_id=None, obra=None, date_from=None,
                                        date_to=None, relative_months=None, metrics=None, max_findings=None, **_):
    """AI-INTELLIGENCE-03 — thin adapter. Every finding is produced by
    `apps.ai.diagnostics.engine.run_environmental_diagnostics`, which only
    ever reads through already-guarded AI-INTELLIGENCE-02 analytics
    functions; this function's only job is obra resolution + RBAC, exactly
    like every other obra-scoped tool in this file."""
    from .diagnostics import run_environmental_diagnostics

    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra)
    if resolved_early:
        return response
    if metrics is not None and not isinstance(metrics, list):
        return {"ok": False, "error": "invalid_arguments", "reason": "metrics debe ser una lista de strings."}
    data = run_environmental_diagnostics(
        organization, user, obra=obra_obj, date_from=date_from, date_to=date_to,
        relative_months=relative_months, metrics=metrics, max_findings=max_findings or 20,
    )
    return {"ok": True, "data": data}


def forecast_environmental_metric(organization, user, obra_id=None, obra=None, material_id=None, material=None,
                                   metric=None, categoria=None, periods_back=6, periods_ahead=3, **_):
    """AI INTELLIGENCE macrofase — deterministic trend + projection
    (`forecasting.forecast_metric`). Never presented as certain: every
    result carries `confidence` (nivel/r_squared/n_points)."""
    from . import forecasting

    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    if not metric and not categoria and not material_id and not material:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere metric, categoria o material_id/material."}
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra)
    if resolved_early:
        return response
    material_obj, response, resolved_early = _resolve_material_arg(organization, user, material_id, material)
    if resolved_early:
        return response
    return forecasting.forecast_metric(
        organization, user, obra=obra_obj, material=material_obj, metric=metric, categoria=categoria,
        periods_back=periods_back, periods_ahead=periods_ahead,
    )


def detect_environmental_anomalies(organization, user, obra_id=None, obra=None, material_id=None, material=None,
                                    metric=None, categoria=None, periods_back=6, threshold=None, **_):
    """AI INTELLIGENCE macrofase — deterministic outlier detection
    (`anomalies.detect_anomalies`, z-score). Always reports method,
    threshold and observed deviation — never "this looks anomalous"
    without a number."""
    from . import anomalies

    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    if not metric and not categoria and not material_id and not material:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere metric, categoria o material_id/material."}
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra)
    if resolved_early:
        return response
    material_obj, response, resolved_early = _resolve_material_arg(organization, user, material_id, material)
    if resolved_early:
        return response
    return anomalies.detect_anomalies(
        organization, user, obra=obra_obj, material=material_obj, metric=metric, categoria=categoria,
        periods_back=periods_back, threshold=threshold,
    )


def score_environmental_risk(organization, user, obra_id=None, obra=None, date_from=None, date_to=None,
                              relative_months=None, metrics=None, **_):
    """AI INTELLIGENCE macrofase — risk score built EXCLUSIVELY from real
    `diagnose_environmental_performance` findings (`risk.score_environmental_risk`)
    — never the LLM's own judgment."""
    from . import risk

    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra)
    if resolved_early:
        return response
    if metrics is not None and not isinstance(metrics, list):
        return {"ok": False, "error": "invalid_arguments", "reason": "metrics debe ser una lista de strings."}
    return risk.score_environmental_risk(
        organization, user, obra=obra_obj, date_from=date_from, date_to=date_to,
        relative_months=relative_months, metrics=metrics,
    )


def prioritize_environmental_actions(organization, user, obra_id=None, obra=None, date_from=None, date_to=None,
                                      relative_months=None, metrics=None, max_actions=10, **_):
    """AI INTELLIGENCE macrofase — deduplicated, ordered action list built
    from real diagnostics findings (`prioritization.prioritize_actions`).
    Every action's `accion` text comes from the controlled recommendations
    catalog — never invented here or by the model."""
    from . import prioritization

    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra)
    if resolved_early:
        return response
    if metrics is not None and not isinstance(metrics, list):
        return {"ok": False, "error": "invalid_arguments", "reason": "metrics debe ser una lista de strings."}
    return prioritization.prioritize_actions(
        organization, user, obra=obra_obj, date_from=date_from, date_to=date_to,
        relative_months=relative_months, metrics=metrics, max_actions=max_actions,
    )


def simulate_environmental_scenario(organization, user, obra_id=None, obra=None, material_id=None, material=None,
                                     metric=None, categoria=None, percent_change=None, absolute_value=None,
                                     date_from=None, date_to=None, relative_months=None, **_):
    """AI INTELLIGENCE macrofase — hypothetical what-if
    (`scenarios.simulate_scenario`). Never writes to the database; the
    hypothetical number is classified with the SAME rules diagnostics uses
    for real data — never a separate, looser judgment."""
    from . import scenarios

    guard = _guarded(user, organization, Permission.DATA_VIEW)
    if guard:
        return guard
    if not metric and not categoria and not material_id and not material:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere metric, categoria o material_id/material."}
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra)
    if resolved_early:
        return response
    if obra_obj is None:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere obra_id u obra para simular un escenario."}
    material_obj, response, resolved_early = _resolve_material_arg(organization, user, material_id, material)
    if resolved_early:
        return response
    return scenarios.simulate_scenario(
        organization, user, obra=obra_obj, material=material_obj, metric=metric, categoria=categoria,
        percent_change=percent_change, absolute_value=absolute_value,
        date_from=date_from, date_to=date_to, relative_months=relative_months,
    )


def trace_metric_provenance(organization, user, obra_id=None, obra=None, material_id=None, material=None,
                             date_from=None, date_to=None, relative_months=None, limit=10, **_):
    """AI INTELLIGENCE macrofase — full dato -> evidencia -> factor ->
    cálculo chain for a material's ledger entries
    (`provenance.trace_metric_provenance`), reusing
    `material_ledger.ledger_entry_provenance` (AI-INTELLIGENCE-01)."""
    from . import provenance as provenance_module

    guard = _guarded(user, organization, Permission.FACTOR_VIEW)
    if guard:
        return guard
    material_obj, response, resolved_early = _resolve_material_arg(organization, user, material_id, material)
    if resolved_early:
        return response
    if material_obj is None:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere material_id o material (nombre)."}
    obra_obj, response, resolved_early = _resolve_obra_arg(organization, user, obra_id, obra) if (obra_id or obra) else (None, None, False)
    if resolved_early:
        return response
    return provenance_module.trace_metric_provenance(
        organization, user, obra=obra_obj, material=material_obj,
        date_from=date_from, date_to=date_to, relative_months=relative_months, limit=limit,
    )


def get_conversation_context(organization, user, conversation=None, **_):
    """AI INTELLIGENCE macrofase — multi-turn recall: the last obra/metric/
    period actually used in THIS conversation's own tool history (never a
    guess — see `apps.ai.context.infer_conversation_context`). Use this
    instead of asking the user to repeat the obra/period/metric they
    already gave in an earlier turn."""
    from .context import infer_conversation_context

    if conversation is None:
        return {"ok": True, "data": {"obra_id": None, "obra_nombre": None, "metric": None, "period": None}}
    return {"ok": True, "data": infer_conversation_context(conversation)}


def search_environmental_knowledge(organization, user, query=None, **_):
    # The knowledge base (SOURCE-WATCH sources) is shared reference data,
    # not tenant-owned — there is nothing to tenant-check here, only bound
    # the result size and never expose raw upstream payloads.
    if not query or not query.strip():
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere query."}
    query = query.strip()[:200]
    sources = EnvironmentalSource.objects.filter(nombre__icontains=query, activa=True).values(
        "codigo", "nombre", "organismo", "documentation_url",
    )[:MAX_ROWS]
    records = ExternalRecord.objects.filter(title__icontains=query).select_related("source").values(
        "source__codigo", "external_id", "title", "estado", "source_url",
    )[:MAX_ROWS]
    return {"ok": True, "data": {"fuentes": list(sources), "registros": list(records), "limite": MAX_ROWS}}


def _parse_date(value):
    if not value:
        return None
    try:
        return date_cls.fromisoformat(value)
    except (TypeError, ValueError):
        return None


TOOLS = {
    "get_current_organization": {
        "function": get_current_organization,
        "description": "Devuelve el tenant/organización actual de la conversación: id, nombre, preset del rubro y si está activa.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "list_projects": {
        "function": list_projects,
        "description": "Lista las obras/proyectos visibles para el usuario en la organización actual.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "get_project_summary": {
        "function": get_project_summary,
        "description": "Resumen operacional de una obra específica (etapas, actividades recientes).",
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "ID de la obra."},
        }, "required": ["obra_id"], "additionalProperties": False},
    },
    "get_environmental_indicators": {
        "function": get_environmental_indicators,
        "description": "Lista indicadores ambientales activos (organización u obra) con su último valor conocido.",
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a los indicadores de esta obra."},
            "codigo": {"type": "string", "description": "Opcional: código exacto de un indicador."},
        }, "additionalProperties": False},
    },
    "get_emissions_summary": {
        "function": get_emissions_summary,
        "description": "Totales de impacto A1-A3 (kgCO2e u otra unidad) agregados por unidad de resultado, para la organización o una obra, en un rango de fechas opcional.",
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "start": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de inicio, opcional."},
            "end": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de fin, opcional."},
            "categoria": {"type": "string", "description": "Opcional: categoría de material."},
        }, "additionalProperties": False},
    },
    "get_material_summary": {
        "function": get_material_summary,
        "description": "Estado de MATERIAL-INTELLIGENCE para un material: propiedades técnicas aprobadas, usos funcionales aprobados y cadena de comparabilidad.",
        "parameters": {"type": "object", "properties": {
            "material_id": {"type": "integer", "description": "ID del material operacional."},
            "obra_id": {"type": "integer", "description": "Opcional: contexto de obra."},
        }, "required": ["material_id"], "additionalProperties": False},
    },
    "get_material_hotspots": {
        "function": get_material_hotspots,
        "description": "Materiales con mayor contribución de impacto positivo (hotspots), determinista, sin ranking de IA.",
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "categoria": {"type": "string", "description": "Opcional: categoría de material."},
            "standard": {"type": "string", "description": "Opcional: generación EN 15804 (A1/A2)."},
        }, "additionalProperties": False},
    },
    "get_evidence_quality": {
        "function": get_evidence_quality,
        "description": (
            "Estado de evidencia y calidad de un material, en CUATRO ejes SIEMPRE distintos: "
            "(1) si existe un registro de consumo, (2) si ese registro tiene evidencia adjunta, "
            "(3) la calidad/trazabilidad de la observación, y (4) si hay un factor ambiental mapeado. "
            "Nunca combinar 'no hay evidencia' con 'no hay factor ambiental': son hechos distintos. "
            "Acepta el nombre del material directamente (p.ej. 'agua') — no es obligatorio tener el ID."
        ),
        "parameters": {"type": "object", "properties": {
            "material_id": {"type": "integer", "description": "ID del material operacional, si ya se conoce."},
            "material": {"type": "string", "description": "Alternativa a material_id: nombre o categoría del material (p.ej. 'agua', 'hormigón')."},
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "date_from": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses en vez de date_from/date_to."},
        }, "additionalProperties": False},
    },
    "get_open_alerts": {
        "function": get_open_alerts,
        "description": "Problemáticas ambientales abiertas (no cerradas/resueltas), ordenadas por nivel de riesgo.",
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
        }, "additionalProperties": False},
    },
    "get_ec3_mapping_status": {
        "function": get_ec3_mapping_status,
        "description": "Estado de gobernanza EC3/openEPD para un material: candidatos propuestos, su estado (CANDIDATES_FOUND/REVIEW_REQUIRED/MAPPED/REJECTED/STALE) y revisión humana.",
        "parameters": {"type": "object", "properties": {
            "material_id": {"type": "integer", "description": "ID del material operacional."},
        }, "required": ["material_id"], "additionalProperties": False},
    },
    "get_ec3_opportunities": {
        "function": get_ec3_opportunities,
        "description": "Previsualiza si algún candidato EC3 ya propuesto (pero aún no aplicado) para un material podría reducir su impacto frente al factor activo actual. Nunca decide adopción; siempre requiere revisión humana.",
        "parameters": {"type": "object", "properties": {
            "material_id": {"type": "integer", "description": "ID del material operacional."},
            "lcia_method": {"type": "string", "description": "Método LCIA a evaluar (por defecto 'EF 3.0')."},
        }, "required": ["material_id"], "additionalProperties": False},
    },
    "get_factor_provenance": {
        "function": get_factor_provenance,
        "description": "Trazabilidad completa de un cálculo ambiental ya realizado: fuente, factor, versión, mapping, calidad y si fue recalculado.",
        "parameters": {"type": "object", "properties": {
            "calculo_id": {"type": "integer", "description": "ID del cálculo ambiental (CalculoAmbiental)."},
        }, "required": ["calculo_id"], "additionalProperties": False},
    },
    "get_historical_trends": {
        "function": get_historical_trends,
        "description": "Serie histórica de valores de un indicador ambiental (hasta 12 períodos más recientes).",
        "parameters": {"type": "object", "properties": {
            "indicador_id": {"type": "integer", "description": "ID del indicador ambiental."},
        }, "required": ["indicador_id"], "additionalProperties": False},
    },
    "resolve_entity": {
        "function": resolve_entity,
        "description": (
            "Resuelve una referencia en lenguaje natural (nombre de obra, nombre/categoría de material, "
            "nombre de activo/maquinaria) contra los datos REALES de este tenant. Úsalo SIEMPRE antes de "
            "pedirle un ID al usuario o antes de listar todas las obras/materiales para que el usuario elija: "
            "si el sistema puede resolverlo, nunca preguntes 'dame el ID' ni 'dime cuáles obras existen'."
        ),
        "parameters": {"type": "object", "properties": {
            "entity_type": {"type": "string", "enum": ["obra", "material", "activo"], "description": "Tipo de entidad a resolver."},
            "query": {"type": "string", "description": "Texto libre a resolver (nombre completo o parcial)."},
        }, "required": ["entity_type", "query"], "additionalProperties": False},
    },
    "get_operational_timeseries": {
        "function": get_operational_timeseries,
        "description": (
            "Serie temporal mensual de una métrica operacional (agua, energia, combustible, residuo) o de un "
            "material/categoria, para la organización o una obra, en un rango de fechas o 'últimos N meses'. "
            "Cada valor es una suma real ya calculada por el backend — nunca la calcules tú."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra (usa resolve_entity para obtenerlo desde un nombre)."},
            "metric": {"type": "string", "description": "Categoría de consumo: agua, combustible, energia, residuo, materiales."},
            "categoria": {"type": "string", "description": "Alternativa a metric: categoría de material tal cual está en el sistema."},
            "material_id": {"type": "integer", "description": "Alternativa a metric/categoria: un material específico (usa resolve_entity si el usuario dio un nombre)."},
            "date_from": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses en vez de date_from/date_to."},
        }, "additionalProperties": False},
    },
    "get_operational_aggregate": {
        "function": get_operational_aggregate,
        "description": (
            "Total/promedio/máximo/mínimo/variación/cobertura de una métrica operacional o material en un "
            "período — agregación calculada íntegramente en el backend, nunca por el modelo."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "metric": {"type": "string", "description": "Categoría de consumo: agua, combustible, energia, residuo, materiales."},
            "categoria": {"type": "string", "description": "Alternativa a metric: categoría de material tal cual está en el sistema."},
            "material_id": {"type": "integer", "description": "Alternativa a metric/categoria: un material específico."},
            "date_from": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO (YYYY-MM-DD) de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses en vez de date_from/date_to."},
        }, "additionalProperties": False},
    },
    "rank_operational_entities": {
        "function": rank_operational_entities,
        "description": (
            "Ranking determinista (ordenado y calculado por el backend) de obras, materiales, categorías, "
            "activos/maquinaria o períodos por consumo/impacto de una métrica. Úsalo para '¿cuál obra/material/"
            "maquinaria tiene mayor...?' — nunca pidas al usuario que elija entre obras si esto puede resolverlo."
        ),
        "parameters": {"type": "object", "properties": {
            "entity_type": {"type": "string", "enum": ["obra", "material", "categoria", "standard", "activo", "periodo"], "description": "Qué se está rankeando."},
            "metric": {"type": "string", "description": "Métrica de flujo operacional (agua/energia/combustible/residuo) — requerida para entity_type='activo'."},
            "obra_id": {"type": "integer", "description": "Opcional: acota el ranking a una obra (irrelevante si entity_type='obra')."},
            "categoria": {"type": "string", "description": "Opcional: acota por categoría de material."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses."},
            "top_n": {"type": "integer", "description": "Cuántas filas devolver (por defecto 10)."},
        }, "required": ["entity_type"], "additionalProperties": False},
    },
    "compare_projects": {
        "function": compare_projects,
        "description": (
            "Compara TODAS las obras accesibles del tenant por impacto/consumo y devuelve la de mayor valor "
            "más una razón (principal contribuyente). Resuelve las obras automáticamente — nunca pidas IDs "
            "ni le pidas al usuario que enumere las obras."
        ),
        "parameters": {"type": "object", "properties": {
            "metric": {"type": "string", "description": "Métrica de flujo operacional (agua/energia/combustible/residuo); si se omite, compara impacto A1-A3 total."},
            "categoria": {"type": "string", "description": "Opcional: acota por categoría de material."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses."},
            "top_n": {"type": "integer", "description": "Cuántas obras devolver (por defecto 5)."},
        }, "additionalProperties": False},
    },
    "diagnose_environmental_performance": {
        "function": diagnose_environmental_performance,
        "description": (
            "Diagnóstico ambiental determinista de una obra: qué cambió respecto del período anterior, "
            "qué entidad concentra el consumo/impacto, y qué datos tienen evidencia/calidad/factor "
            "insuficientes — todo calculado por el backend (nunca por el modelo), ordenado por prioridad. "
            "Úsalo para preguntas como '¿qué debería preocuparme de esta obra?', '¿qué cambió más?', "
            "'¿cuál es la principal fuente de impacto?', '¿hay problemas de evidencia?', '¿qué debería "
            "revisar primero?'. Resuelve la obra por nombre — nunca pidas un ID si el usuario ya dio un nombre."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "ID de la obra, si ya se conoce."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio del período actual, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin del período actual, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses en vez de date_from/date_to."},
            "metrics": {"type": "array", "items": {"type": "string"}, "description": "Opcional: subconjunto de métricas a analizar (agua, combustible, energia, residuos, materiales). Por defecto analiza todas."},
            "max_findings": {"type": "integer", "description": "Máximo de hallazgos a devolver, ordenados por prioridad (por defecto 20)."},
        }, "additionalProperties": False},
    },
    "forecast_environmental_metric": {
        "function": forecast_environmental_metric,
        "description": (
            "Proyección determinista (tendencia lineal + confianza) de una métrica/material hacia adelante, "
            "a partir del histórico real. Incluye SIEMPRE 'confidence' (nivel/r_squared/n_points) — nunca "
            "presentes una proyección como un hecho cierto."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "material_id": {"type": "integer", "description": "Opcional: un material específico."},
            "material": {"type": "string", "description": "Alternativa a material_id: nombre del material."},
            "metric": {"type": "string", "description": "Categoría de consumo: agua, combustible, energia, residuos, materiales."},
            "categoria": {"type": "string", "description": "Alternativa a metric: categoría tal cual está en el sistema."},
            "periods_back": {"type": "integer", "description": "Meses históricos a usar para ajustar la tendencia (por defecto 6)."},
            "periods_ahead": {"type": "integer", "description": "Meses a proyectar hacia adelante (por defecto 3)."},
        }, "additionalProperties": False},
    },
    "detect_environmental_anomalies": {
        "function": detect_environmental_anomalies,
        "description": (
            "Detección determinista de valores atípicos (z-score) en el histórico mensual de una métrica/material. "
            "Cada anomalía reportada incluye método, umbral y desviación observada — nunca 'esto parece raro' sin número."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "material_id": {"type": "integer", "description": "Opcional: un material específico."},
            "material": {"type": "string", "description": "Alternativa a material_id: nombre del material."},
            "metric": {"type": "string", "description": "Categoría de consumo: agua, combustible, energia, residuos, materiales."},
            "categoria": {"type": "string", "description": "Alternativa a metric: categoría tal cual está en el sistema."},
            "periods_back": {"type": "integer", "description": "Meses históricos a analizar (por defecto 6)."},
            "threshold": {"type": "number", "description": "Umbral de z-score (por defecto 2.0)."},
        }, "additionalProperties": False},
    },
    "score_environmental_risk": {
        "function": score_environmental_risk,
        "description": (
            "Puntaje de riesgo ambiental-operacional (0-100) de una obra, construido EXCLUSIVAMENTE a partir de "
            "los hallazgos reales de diagnose_environmental_performance — nunca una opinión del modelo."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "ID de la obra, si ya se conoce."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio del período actual, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin del período actual, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses."},
            "metrics": {"type": "array", "items": {"type": "string"}, "description": "Opcional: subconjunto de métricas a considerar."},
        }, "additionalProperties": False},
    },
    "prioritize_environmental_actions": {
        "function": prioritize_environmental_actions,
        "description": (
            "Lista de acciones ordenada por prioridad determinista, derivada de los hallazgos reales de "
            "diagnose_environmental_performance — cada acción viene del catálogo controlado de recomendaciones, "
            "nunca inventada por el modelo."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "ID de la obra, si ya se conoce."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses."},
            "metrics": {"type": "array", "items": {"type": "string"}, "description": "Opcional: subconjunto de métricas a considerar."},
            "max_actions": {"type": "integer", "description": "Máximo de acciones a devolver (por defecto 10)."},
        }, "additionalProperties": False},
    },
    "simulate_environmental_scenario": {
        "function": simulate_environmental_scenario,
        "description": (
            "Simulación hipotética 'qué pasaría si': aplica un cambio porcentual o un valor absoluto hipotético "
            "sobre el total real de una métrica/material y lo clasifica con las MISMAS reglas del diagnóstico real. "
            "NUNCA modifica datos reales ni se persiste — es puramente hipotético."
        ),
        "parameters": {"type": "object", "properties": {
            "obra_id": {"type": "integer", "description": "ID de la obra (requerido)."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "material_id": {"type": "integer", "description": "Opcional: un material específico."},
            "material": {"type": "string", "description": "Alternativa a material_id: nombre del material."},
            "metric": {"type": "string", "description": "Categoría de consumo: agua, combustible, energia, residuos, materiales."},
            "categoria": {"type": "string", "description": "Alternativa a metric."},
            "percent_change": {"type": "number", "description": "Cambio porcentual hipotético sobre el valor real actual (p.ej. 20 para +20%, -15 para -15%)."},
            "absolute_value": {"type": "number", "description": "Alternativa a percent_change: un valor hipotético absoluto."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio del período actual, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin del período actual, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses."},
        }, "required": ["obra_id"], "additionalProperties": False},
    },
    "trace_metric_provenance": {
        "function": trace_metric_provenance,
        "description": (
            "Cadena de trazabilidad completa dato -> evidencia -> factor -> cálculo para un material (y opcionalmente "
            "una obra) en un período: responde '¿de dónde salió este número?' citando cada cálculo ambiental real, "
            "su fuente, su factor/versión y su calidad."
        ),
        "parameters": {"type": "object", "properties": {
            "material_id": {"type": "integer", "description": "ID del material, si ya se conoce."},
            "material": {"type": "string", "description": "Alternativa a material_id: nombre o categoría del material."},
            "obra_id": {"type": "integer", "description": "Opcional: acota a una obra."},
            "obra": {"type": "string", "description": "Alternativa a obra_id: nombre de la obra."},
            "date_from": {"type": "string", "description": "Fecha ISO de inicio, opcional."},
            "date_to": {"type": "string", "description": "Fecha ISO de fin, opcional."},
            "relative_months": {"type": "integer", "description": "Opcional: últimos N meses."},
            "limit": {"type": "integer", "description": "Máximo de cálculos a devolver (por defecto 10)."},
        }, "additionalProperties": False},
    },
    "get_conversation_context": {
        "function": get_conversation_context,
        "description": (
            "Recupera la obra/métrica/período usados más recientemente EN ESTA MISMA conversación — úsalo antes "
            "de volver a preguntarle al usuario algo que ya dijo en un turno anterior."
        ),
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "search_environmental_knowledge": {
        "function": search_environmental_knowledge,
        "description": "Busca por palabra clave en las fuentes y registros ya conocidos de la base de conocimiento ambiental (SOURCE-WATCH: RETC, HuellaChile, BCN/LeyChile, SNIFA, SEA, SIMBIO, IDE-MMA, ÖKOBAUDAT). Nunca inventa una fuente no encontrada.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Palabra o frase a buscar."},
        }, "required": ["query"], "additionalProperties": False},
    },
}


def openai_tool_schemas():
    return [
        {"type": "function", "function": {
            "name": name, "description": spec["description"], "parameters": spec["parameters"],
        }}
        for name, spec in TOOLS.items()
    ]


def execute_tool(name, *, organization, user, arguments, conversation=None):
    spec = TOOLS.get(name)
    if spec is None:
        return {"ok": False, "error": "unknown_tool", "reason": f"Herramienta '{name}' no existe."}
    try:
        return spec["function"](organization, user, conversation=conversation, **(arguments or {}))
    except (PermissionDenied, DjangoPermissionDenied):
        return _denied("Permiso denegado para esta consulta.")
    except Http404:
        return _not_found("Recurso no encontrado en esta organización.")
    except TypeError as exc:
        return {"ok": False, "error": "invalid_arguments", "reason": str(exc)}
