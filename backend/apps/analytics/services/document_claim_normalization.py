import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation


def normalized_text(value):
    value = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(char for char in value if unicodedata.category(char) != "Mn").strip()


def normalize_date(value):
    raw = str(value or "").strip()
    for pattern in (r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b"):
        match = re.search(pattern, raw)
        if not match:
            continue
        first, second, third = match.groups()
        year, month, day = (int(first), int(second), int(third)) if len(first) == 4 else (int(third) + (2000 if len(third) == 2 else 0), int(second), int(first))
        try:
            return datetime(year, month, day).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_claim(field, original, suggested=None):
    raw = str(original if original not in (None, "") else suggested or "").strip()
    normalized = normalized_text(raw)
    if field == "cantidad":
        numeric = re.sub(r"[^0-9,.-]", "", raw)
        if "," in numeric:
            numeric = numeric.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"[1-9]\d{0,2}\.\d{3}", numeric):
            numeric = numeric.replace(".", "")
        try:
            return format(Decimal(numeric).normalize(), "f")
        except (InvalidOperation, ValueError):
            return None
    if field == "unidad":
        return {"l": "L", "lt": "L", "lts": "L", "litro": "L", "litros": "L", "litros diesel": "L", "m3": "m3", "kg": "kg", "t": "t", "ton": "t", "toneladas": "t"}.get(normalized)
    if field == "tipo_recurso":
        resources = {
            "diesel": ("diesel", "petroleo diesel"),
            "gasolina": ("gasolina", "bencina"),
            "gas_licuado": ("gas licuado", "glp"),
            "gas_natural": ("gas natural", "gnc"),
        }
        matches = [key for key, aliases in resources.items() if any(alias in normalized for alias in aliases)]
        return matches[0] if len(matches) == 1 else None
    if field == "fecha":
        return normalize_date(raw)
    if field == "identificador_documento":
        return raw[:120] or None
    return None


def normalize_provider_claims(raw_claims, origin):
    claims, trace = {}, {}
    for field, raw_claim in (raw_claims or {}).items():
        claim = raw_claim if isinstance(raw_claim, dict) else {"valor_original": raw_claim}
        original = claim.get("valor_original")
        normalized = normalize_claim(field, original, claim.get("valor_normalizado"))
        if normalized in (None, ""):
            continue
        claims[field] = normalized
        trace[field] = {
            "valor_original": original,
            "valor_normalizado": normalized,
            "confianza": claim.get("confianza"),
            "origen": origin,
        }
    return claims, trace
