"""AI-INTELLIGENCE-01 — read-only backend tools.

Every tool is a thin, tenant-checked adapter over an already-existing,
deterministic service (`ContextGateway`, `material_hotspots`,
`material_opportunities`, `material_ledger`, `material_quality`, the `ec3`
app, `apps.knowledge`). No tool computes anything itself, no tool mutates
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

from apps.analytics.models import IndicadorAmbiental, MaterialOperacional, ProblematicaAmbiental
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


def get_evidence_quality(organization, user, material_id=None, **_):
    guard = _guarded(user, organization, Permission.EVIDENCE_VIEW)
    if guard:
        return guard
    if not material_id:
        return {"ok": False, "error": "missing_argument", "reason": "Se requiere material_id."}
    material, error = _resolve_material(organization, user, material_id)
    if error:
        return error
    selection = select_material_factor(organization, material, material.unidad_base, date_cls.today())
    if selection["status"] != "calculable":
        return {"ok": True, "data": {"material_id": material.pk, "factor_disponible": False, "razon": selection["reason"]}}
    quality = assess_factor_data_quality(selection["factor_version"].factor)
    return {"ok": True, "data": {"material_id": material.pk, "factor_disponible": True, "calidad": quality}}


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
        "description": "Calidad de la evidencia/factor ambiental que respalda un material: qué se sabe, qué falta, y advertencias.",
        "parameters": {"type": "object", "properties": {
            "material_id": {"type": "integer", "description": "ID del material operacional."},
        }, "required": ["material_id"], "additionalProperties": False},
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


def execute_tool(name, *, organization, user, arguments):
    spec = TOOLS.get(name)
    if spec is None:
        return {"ok": False, "error": "unknown_tool", "reason": f"Herramienta '{name}' no existe."}
    try:
        return spec["function"](organization, user, **(arguments or {}))
    except (PermissionDenied, DjangoPermissionDenied):
        return _denied("Permiso denegado para esta consulta.")
    except Http404:
        return _not_found("Recurso no encontrado en esta organización.")
    except TypeError as exc:
        return {"ok": False, "error": "invalid_arguments", "reason": str(exc)}
