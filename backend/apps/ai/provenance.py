"""AI INTELLIGENCE macrofase — full dato -> evidencia -> factor -> cálculo
provenance trail for a material's ledger entries in a period.

Answers "¿de dónde salió este número?" for an aggregate/finding, by
walking every underlying `CalculoAmbiental` entry and reusing
`material_ledger.ledger_entry_provenance` (AI-INTELLIGENCE-01) — already
the single source of truth for one entry's chain (fuente, factor,
versión, mapping, calidad, recálculo). This module only fans that out
across every entry in scope and tags each one with its
`knowledge_grounding` category — it never recomputes a provenance fact
itself.
"""
from apps.analytics.services.material_ledger import ledger_entries, ledger_entry_provenance

from .knowledge_grounding import classify_provenance_entry
from .periods import resolve_period

MAX_ENTRIES = 20


def trace_metric_provenance(organization, user, *, obra=None, material, date_from=None,
                             date_to=None, relative_months=None, limit=10):
    """Full provenance chain for every ledger entry of `material` (in
    `obra`, if given) within the period — bounded, tenant-scoped (via the
    already-guarded `material`/`obra` objects the caller resolved)."""
    limit = max(1, min(int(limit or 10), MAX_ENTRIES))
    start, end = resolve_period(date_from=date_from, date_to=date_to, relative_months=relative_months)
    entries = list(ledger_entries(organization, work=obra, material=material, start=start, end=end).order_by("-fecha_calculo")[:limit])
    if not entries:
        return {
            "ok": True, "material_id": material.id, "material_nombre": material.nombre,
            "obra_id": obra.id if obra else None, "periodo": {"start": start, "end": end},
            "entradas": 0, "cadena": [],
            "advertencia": "No hay cálculos ambientales registrados para este material en este período.",
        }
    chain = []
    for entry in entries:
        trail = ledger_entry_provenance(entry)
        chain.append({**trail, "grounding": classify_provenance_entry(trail)})
    return {
        "ok": True, "material_id": material.id, "material_nombre": material.nombre,
        "obra_id": obra.id if obra else None, "periodo": {"start": start, "end": end},
        "entradas": len(chain), "cadena": chain,
    }
