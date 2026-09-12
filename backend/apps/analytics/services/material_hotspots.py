"""Material hotspot intelligence (MI-01F): which materials explain the most
A1-A3 impact in a work — reusing MATERIAL-DATA-01G's ledger
(CalculoAmbiental / material_ledger.py) as the sole source of truth. No
second ledger, no recalculation: this module only aggregates the same
already-computed, non-superseded results. Deterministic — no AI ranking,
no opaque score. Positive, negative and net contribution are always
reported separately; the V1 hotspot-share denominator is the total
POSITIVE contribution only, so a negative (carbon-storing) material is
never folded into — or mistaken for — an improvement opportunity by that
share alone.
"""

from collections import defaultdict
from decimal import Decimal

from .material_ledger import _group_value, ledger_entries


def _material_label(entry):
    info = (entry.snapshot_tecnico or {}).get("material") or {}
    return info.get("codigo") or info.get("nombre") or f"material-{entry.actividad_id}"


def material_hotspots(organization, *, work=None, start=None, end=None, categoria=None, standard=None, group_by=None):
    """Per unidad_resultado (never mixed), the material-level breakdown of
    positive/negative/net A1-A3 contribution and each material's hotspot
    share of the total positive contribution."""

    entries = list(
        ledger_entries(organization, work=work, start=start, end=end, categoria=categoria, standard=standard)
    )

    by_unit = defaultdict(lambda: defaultdict(lambda: {
        "positive_gwp": Decimal("0"), "negative_gwp": Decimal("0"), "net_gwp": Decimal("0"), "entradas": 0,
    }))
    labels = {}
    groups_by_unit_material = defaultdict(dict) if group_by else None

    for entry in entries:
        unit = entry.unidad_resultado or "sin_unidad"
        material_info = (entry.snapshot_tecnico or {}).get("material") or {}
        material_id = material_info.get("id")
        labels[material_id] = _material_label(entry)
        bucket = by_unit[unit][material_id]
        if entry.resultado > 0:
            bucket["positive_gwp"] += entry.resultado
        elif entry.resultado < 0:
            bucket["negative_gwp"] += entry.resultado
        bucket["net_gwp"] += entry.resultado
        bucket["entradas"] += 1
        if group_by:
            groups_by_unit_material[(unit, material_id)][_group_value(entry, group_by)] = True

    result = {}
    for unit, materials in by_unit.items():
        total_positive = sum(bucket["positive_gwp"] for bucket in materials.values())
        rows = []
        for material_id, bucket in materials.items():
            share = (bucket["positive_gwp"] / total_positive) if total_positive > 0 else None
            row = {
                "material_id": material_id,
                "material_label": labels.get(material_id),
                "positive_gwp": bucket["positive_gwp"],
                "negative_gwp": bucket["negative_gwp"],
                "net_gwp": bucket["net_gwp"],
                "hotspot_share": share,
                "entradas": bucket["entradas"],
            }
            if group_by:
                row["groups"] = sorted(groups_by_unit_material[(unit, material_id)].keys())
            rows.append(row)
        # Deterministic, explicit sort key (the raw positive contribution
        # itself) — never an opaque or AI-derived score.
        rows.sort(key=lambda r: (r["positive_gwp"], r["material_id"] or 0), reverse=True)
        result[unit] = {"materiales": rows, "total_positive": total_positive, "entradas_totales": len(entries)}
    return result
