"""Clasificacion deterministica para factores de emision."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


FACTOR_CATEGORIES = [
    "Combustible",
    "Electricidad",
    "Transporte",
    "Agua",
    "Materiales",
    "Residuos",
    "Refrigerantes",
    "Otros",
]

CATEGORY_RULES = [
    (
        "Residuos",
        [
            "residuo",
            "residuos",
            "relleno sanitario",
            "compostaje",
            "reciclaje",
            "waste disposal",
            "disposicion residuos",
            "tratamiento disposicion",
        ],
    ),
    (
        "Refrigerantes",
        ["refrigerante", "r507", "r407", "r407a", "r410", "r410a"],
    ),
    (
        "Transporte",
        [
            "camion",
            "tren",
            "barco",
            "avion",
            "vehiculo",
            "bus",
            "metro",
            "t km",
            "tkm",
            "km pasajero",
            "transporte",
            "carga",
        ],
    ),
    (
        "Combustible",
        [
            "diesel",
            "glp",
            "gas natural",
            "gas licuado",
            "combustion movil",
            "combustion estacionaria",
            "combustible",
        ],
    ),
    (
        "Electricidad",
        [
            "electricidad",
            "electrico",
            "sen",
            "los lagos",
            "aysen",
            "magallanes",
            "kwh",
        ],
    ),
    ("Agua", ["agua", "suministro agua", "tratamiento agua"]),
    (
        "Materiales",
        [
            "carton",
            "papel",
            "plastico",
            "vidrio",
            "aluminio",
            "notebook",
        ],
    ),
]

CLASSIFICATION_STOPWORDS = {"de", "del", "la", "el"}


def normalize_text(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    value = without_accents.strip().lower()
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_classification_text(*values: Any) -> str:
    text = normalize_text(" ".join(str(value or "") for value in values))
    tokens = [token for token in text.split() if token not in CLASSIFICATION_STOPWORDS]
    return " ".join(tokens)


def _contains_pattern(text: str, pattern: str) -> bool:
    return re.search(rf"(^|\s){re.escape(pattern)}($|\s)", text) is not None


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(_contains_pattern(text, normalize_classification_text(pattern)) for pattern in patterns)


LEGACY_CATEGORY_RULES = {
    "Residuos": [
        "residuo",
        "residuos",
        "relleno_sanitario",
        "compostaje",
        "reciclaje",
        "disposicion",
        "tratamiento_disposicion",
    ],
    "Refrigerantes": ["refrigerante", "r507", "r407", "r410", "fuga"],
    "Transporte": [
        "camion",
        "tren",
        "barco",
        "avion",
        "vehiculo",
        "bus",
        "metro",
        "t_km",
        "tkm",
        "km_pasajero",
        "transporte",
        "carga",
    ],
    "Combustible": [
        "diesel",
        "glp",
        "gas_natural",
        "gas_licuado",
        "combustion",
        "combustible",
    ],
    "Electricidad": [
        "electricidad",
        "electrico",
        "sen",
        "los_lagos",
        "aysen",
        "magallanes",
        "kwh",
    ],
    "Agua": ["agua", "suministro_de_agua", "tratamiento_de_agua"],
    "Materiales": [
        "carton",
        "papel",
        "plastico",
        "vidrio",
        "aluminio",
        "notebook",
        "material",
    ],
}

ACTIVITY_KEY_ALIASES = {
    "diesel_movil": "diesel_combustion_movil",
    "diesel_combustion_movil": "diesel_combustion_movil",
    "diesel_estacionario": "diesel_combustion_estacionaria",
    "diesel_combustion_estacionaria": "diesel_combustion_estacionaria",
    "camion_diesel_rigido_promedio": "camion_diesel_rigido_promedio",
    "carton_virgen": "carton_virgen",
    "carton_reciclado": "carton_reciclado",
}

def normalize_key(text: Any) -> str:
    value = normalize_text(text)
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    tokens = [token for token in value.split("_") if token not in CLASSIFICATION_STOPWORDS]
    value = "_".join(tokens)
    return ACTIVITY_KEY_ALIASES.get(value, value)


def normalize_categoria(value: Any) -> str | None:
    incoming = normalize_text(value)
    if not incoming:
        return None

    for category in FACTOR_CATEGORIES:
        if incoming == normalize_text(category):
            return category

    return None


def infer_categoria(actividad, unidad=None, fuente=None) -> str:
    text = normalize_classification_text(actividad, unidad, fuente)

    if _matches_any(text, ["tratamiento agua", "suministro agua"]):
        return "Agua"

    for category, patterns in CATEGORY_RULES:
        if _matches_any(text, patterns):
            return category
    return "Otros"


def classify_factor(row: dict) -> dict:
    actividad = row.get("actividad")
    unidad = row.get("unidad")
    fuente = row.get("fuente")
    observaciones = []

    actividad_key = normalize_key(row.get("actividad_key") or actividad)
    categoria_detectada = infer_categoria(actividad, unidad, fuente)
    categoria_archivo = normalize_categoria(row.get("categoria"))

    invalid_categoria = bool(row.get("categoria") and not categoria_archivo)
    if invalid_categoria:
        observaciones.append("Categoria invalida en archivo, se reemplazo por Otros.")
        categoria = "Otros"
    elif categoria_archivo and categoria_archivo != "Otros":
        categoria = categoria_archivo
    else:
        categoria = categoria_detectada

    if categoria == "Otros":
        observaciones.append(
            "Categoria no detectada automaticamente, revisar antes de confirmar."
        )

    return {
        "categoria": categoria,
        "categoria_detectada": categoria_detectada,
        "actividad_key": actividad_key,
        "descripcion": str(row.get("descripcion") or "").strip(),
        "confianza_categoria": 1.0 if categoria != "Otros" else 0.0,
        "observaciones": observaciones,
        "metadata_clasificacion": {
            "metodo": "rules",
            "categoria_detectada": categoria_detectada,
            "categoria_archivo": categoria_archivo or "",
            "categoria_invalida": invalid_categoria,
        },
    }
