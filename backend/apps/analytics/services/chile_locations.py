import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def chile_locations():
    path = Path(__file__).resolve().parent.parent / "data" / "chile_locations.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_chile_location(region, comuna):
    region = str(region or "").strip()
    comuna = str(comuna or "").strip()
    if comuna and not region:
        return "Selecciona una región antes de indicar la comuna."
    if not region:
        return None
    selected = next((item for item in chile_locations() if item["nombre"] == region), None)
    if not selected:
        return "Selecciona una región disponible en el catálogo de Chile."
    if comuna and comuna not in selected["comunas"]:
        return "La comuna seleccionada no pertenece a la región indicada."
    return None
