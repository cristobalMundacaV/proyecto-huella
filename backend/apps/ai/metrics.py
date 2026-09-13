"""AI-INTELLIGENCE-02 — metric-keyword resolution.

The model expresses a metric in free text ("agua", "combustible",
"hormigón"). Audit finding: in this codebase, physical operational
consumption (agua, combustible, energía, residuos, materiales) is tracked
as `MaterialOperacional.categoria` via `EventoMaterial`/`Observacion` — the
same ledger already used for A1-A3 impact accounting. So the *primary*
path for a consumption question maps free text to that `categoria` field
(`CATEGORY_METRICS`/`resolve_metric_keyword`) — never to a tenant-specific
material name or id; a user asking about one specific material instead
goes through `resolvers.resolve_material`, which resolves against real
tenant data.

Per-asset/machinery attribution is a second, separate domain
(`ASSET_FLOW_METRICS`/`resolve_asset_flow_metric`), backed by
`RegistroFlujoAmbiental.activo` — the only place in the schema with
reliable per-asset attribution (confirmed by audit: `ActividadOperacional
.activos` is an optional, non-exclusive M2M, and `EventoMaterial` has no
asset link at all). Used only for machinery/asset ranking.
"""
from datetime import date as date_cls, timedelta

from apps.analytics.models.environmental_flows import RegistroFlujoAmbiental

Flujo = RegistroFlujoAmbiental.Flujo

# Domain vocabulary (fixed concepts this app already models), never a
# tenant-specific instance name — matches `MaterialOperacional.categoria`.
CATEGORY_METRICS = {
    "agua": {"categoria": "agua", "etiqueta": "agua"},
    "combustible": {"categoria": "combustible", "etiqueta": "combustible"},
    "energia": {"categoria": "energia", "etiqueta": "energía"},
    "residuo": {"categoria": "residuos", "etiqueta": "residuos"},
    "materiales": {"categoria": "materiales", "etiqueta": "materiales"},
}

_ALIASES = {
    "agua": "agua", "water": "agua", "consumo de agua": "agua", "consumo_agua": "agua",
    "energia": "energia", "energía": "energia", "electricidad": "energia", "kwh": "energia",
    "combustible": "combustible", "fuel": "combustible", "diesel": "combustible", "diésel": "combustible",
    "petroleo": "combustible", "petróleo": "combustible", "bencina": "combustible", "gasolina": "combustible",
    "residuo": "residuo", "residuos": "residuo", "basura": "residuo", "escombros": "residuo", "waste": "residuo",
    "material": "materiales", "materiales": "materiales", "hormigon": "materiales", "hormigón": "materiales",
    "acero": "materiales",
}


def resolve_metric_keyword(text):
    """Best-effort match of free text to a known consumption category.

    Returns the matching `CATEGORY_METRICS` entry (with its `key`), or
    `None` — not an error, just "not a recognized category keyword", so the
    caller should try a specific material/categoria argument instead."""
    if not text:
        return None
    normalized = str(text).strip().lower()
    key = _ALIASES.get(normalized)
    if key is None:
        for alias, mapped in _ALIASES.items():
            if alias in normalized:
                key = mapped
                break
    if key is None:
        return None
    return {"key": key, **CATEGORY_METRICS[key]}


ASSET_FLOW_METRICS = {
    "agua": {"flujos": [Flujo.AGUA], "concepto": "consumo_agua"},
    "energia": {"flujos": [Flujo.ENERGIA], "concepto": "consumo_energia"},
    "combustible": {
        "flujos": [Flujo.COMBUSTIBLE, Flujo.COMBUSTIBLE_ESTACIONARIO, Flujo.COMBUSTIBLE_MOVIL],
        "concepto": "combustible_consumido",
    },
    "residuo": {"flujos": [Flujo.RESIDUO], "concepto": "cantidad_residuo"},
}


def resolve_asset_flow_metric(text):
    """Same keyword match as `resolve_metric_keyword`, but only for the
    metrics that can be attributed to a specific `ActivoOperacional` via
    `RegistroFlujoAmbiental`. Returns `None` for "materiales" (no asset
    granularity exists for that path) or for unrecognized text."""
    match = resolve_metric_keyword(text)
    if match is None or match["key"] not in ASSET_FLOW_METRICS:
        return None
    return {"key": match["key"], **ASSET_FLOW_METRICS[match["key"]]}


MAX_PERIOD_BUCKETS = 36


def month_bounds(period_start, period_end):
    """Yield (bucket_start, bucket_end, "YYYY-MM") for each calendar month
    that [period_start, period_end] touches, inclusive, oldest first.
    Bounded to MAX_PERIOD_BUCKETS — a defensive cap, never expected to bind
    for a real "últimos N meses" question."""
    if period_start is None or period_end is None:
        return
    cursor = period_start.replace(day=1)
    count = 0
    while cursor <= period_end and count < MAX_PERIOD_BUCKETS:
        if cursor.month == 12:
            next_month = date_cls(cursor.year + 1, 1, 1)
        else:
            next_month = date_cls(cursor.year, cursor.month + 1, 1)
        bucket_start = max(cursor, period_start)
        bucket_end = min(next_month - timedelta(days=1), period_end)
        yield bucket_start, bucket_end, cursor.isoformat()[:7]
        cursor = next_month
        count += 1
