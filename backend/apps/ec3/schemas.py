"""Strict consumed subset of the official openEPD OpenAPI; unknowns stay unknown.

Evidence keeps only identifiers, applicability metadata and declared GWP values.
No inferred scope, LCIA method, verification, geography or material equivalence.
"""
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_EVEN
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

LCIA_METHODS = {"TRACI 2.1", "TRACI 2.0", "TRACI 1.0", "IPCC AR5", "EF 3.0",
                "CML 2016", "CML 2012", "CML 2007", "CML 2001", "CML 1992",
                "ReCiPe 2016", "ReCiPe 2008", "EF 2.0, 2018", "EN 15978:2011", "USEtox 2.12"}


def external_id(value):
    if not isinstance(value, str) or len(value) > 80 or not re.fullmatch(r"[A-Za-z0-9-]+", value):
        raise ValidationError("Identificador openXPD inválido.")
    value = value.replace("-", "").lower()
    if len(value) not in (8, 10):
        raise ValidationError("Identificador openXPD requiere 8 o 10 caracteres.")
    return value


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise ValidationError("Valor numérico inválido.")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError("Valor numérico inválido.") from None
    if not result.is_finite() or (result and abs(result.adjusted()) > 100):
        raise ValidationError("Valor numérico fuera de rango.")
    return result


def text_field(data, key, maximum=2000):
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > maximum:
        raise ValidationError(f"Campo openEPD inválido: {key}.")
    return value


def safe_url(value):
    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("URL de evidencia openEPD inválida.") from None
    return value


def timestamp(value):
    if not isinstance(value, str):
        raise ValidationError("Fecha openEPD inválida.")
    try:
        parsed = parse_datetime(value)
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None:
        raise ValidationError("Fecha openEPD requiere datetime con zona horaria.")
    return parsed


def project_epd(data, *, detail=False):
    if not isinstance(data, dict):
        raise ValidationError("Respuesta openEPD debe ser un objeto.")
    result = {"id": external_id(data.get("id"))}
    for key, maximum in {"doctype": 20, "openepd_version": 30, "product_name": 200,
                         "program_operator_doc_id": 200, "program_operator_version": 200,
                         "product_usage_description": 2000}.items():
        result[key] = text_field(data, key, maximum)
    if result["doctype"] not in (None, "OpenEPD"):
        raise ValidationError("doctype openEPD no soportado.")
    if not result["product_name"]:
        raise ValidationError("Falta product_name.")
    version = data.get("version")
    if version is not None and (type(version) is not int or version < 0):
        raise ValidationError("Versión upstream inválida.")
    result["version"] = version
    private = data.get("private")
    if private is not None and type(private) is not bool:
        raise ValidationError("private debe ser booleano.")
    # Do not copy private/draft records to Carbono Zero.
    if private is True:
        raise ValidationError("Las EPD privadas no se importan.")
    result["private"] = private
    for key in ("declaration_url", "third_party_verification_url"):
        result[key] = safe_url(text_field(data, key, 255))
    for key in ("date_of_issue", "valid_until"):
        value = text_field(data, key, 80)
        if value is not None:
            timestamp(value)
        result[key] = value
    unit = data.get("declared_unit")
    if unit is not None:
        if not isinstance(unit, dict) or not isinstance(unit.get("unit"), str):
            raise ValidationError("Unidad declarada inválida.")
        if isinstance(unit.get("qty"), (str, bool)):
            raise ValidationError("qty upstream debe ser un número JSON.")
        unit = {"qty": str(number(unit.get("qty"))), "unit": unit["unit"]}
    result["declared_unit"] = unit
    for key in ("manufacturer", "program_operator", "third_party_verifier", "pcr"):
        value = data.get(key)
        if value is not None and not isinstance(value, dict):
            raise ValidationError(f"{key} debe ser objeto.")
        fields = ("id", "name", "ref") if key == "pcr" else ("web_domain", "name", "ref")
        result[key] = {field: text_field(value, field, 500) for field in fields if value.get(field) is not None} if value else None
    compliance = data.get("compliance")
    if compliance is not None:
        if not isinstance(compliance, list) or any(not isinstance(v, dict) for v in compliance):
            raise ValidationError("compliance debe ser lista de estándares.")
        compliance = [{"short_name": text_field(v, "short_name", 40), "link": safe_url(text_field(v, "link", 255))} for v in compliance]
    result["compliance"] = compliance
    geography = data.get("applicable_in")
    if geography is not None and (not isinstance(geography, list) or any(not isinstance(v, str) or len(v) > 80 for v in geography)):
        raise ValidationError("applicable_in inválido.")
    result["applicable_in"] = geography
    ec3 = data.get("ec3")
    if ec3 is not None and not isinstance(ec3, dict):
        raise ValidationError("ec3 debe ser objeto.")
    result["ec3"] = {}
    for key in ("category", "manufacturer_specific", "plant_specific", "product_specific", "batch_specific"):
        if ec3 and key in ec3:
            value = ec3[key]
            if (key == "category" and not isinstance(value, str)) or (key != "category" and type(value) is not bool):
                raise ValidationError("Metadata EC3 inválida.")
            result["ec3"][key] = value
    result["impacts"] = {}
    if detail:
        impacts = data.get("impacts")
        if not isinstance(impacts, dict):
            raise ValidationError("Falta objeto impacts en detalle openEPD.")
        for method, values in impacts.items():
            if not isinstance(values, dict):
                raise ValidationError("ImpactSet inválido.")
            gwp = values.get("gwp", {})
            if not isinstance(gwp, dict):
                raise ValidationError("ScopeSet inválido.")
            scope = gwp.get("A1A2A3")
            if scope is not None:
                if not isinstance(scope, dict) or isinstance(scope.get("mean"), (str, bool)):
                    raise ValidationError("Measurement inválida.")
                measurement = {"mean": str(number(scope.get("mean"))), "unit": text_field(scope, "unit", 40)}
                if scope.get("rsd") is not None:
                    measurement["rsd"] = str(number(scope["rsd"]))
                if scope.get("dist") is not None:
                    measurement["dist"] = text_field(scope, "dist", 80)
                result["impacts"][method] = {"gwp": {"A1A2A3": measurement}}
    return result


def project_search(data, page_number, page_size):
    if not isinstance(data, dict) or not isinstance(data.get("payload"), list):
        raise ValidationError("Respuesta de búsqueda openEPD inválida.")
    meta = data.get("meta")
    paging = meta.get("paging") if isinstance(meta, dict) else None
    if not isinstance(paging, dict) or any(type(paging.get(k)) is not int or paging[k] < 0 for k in ("total_count", "total_pages", "page_size")):
        raise ValidationError("Paginación openEPD inválida.")
    if paging["page_size"] != page_size or len(data["payload"]) > page_size:
        raise ValidationError("Tamaño de página openEPD inconsistente.")
    return {"payload": [project_epd(v) for v in data["payload"]],
            "paging": paging, "next_page": page_number + 1 if page_number < paging["total_pages"] else None}


def normalize(evidence, method):
    reasons = []
    if method not in LCIA_METHODS:
        reasons.append("unsupported_lcia_method")
    unit = evidence.get("declared_unit") or {}
    measurement = evidence.get("impacts", {}).get(method, {}).get("gwp", {}).get("A1A2A3", {})
    if unit.get("unit") not in {"kg", "t", "m3", "L", "unidad"}:
        reasons.append("unsupported_declared_unit")
    if measurement.get("unit") != "kgCO2e" or measurement.get("mean") is None:
        reasons.append("missing_explicit_gwp_a1a3_kgco2e")
    quantity = number(unit.get("qty", 0))
    if quantity <= 0:
        reasons.append("nonpositive_declared_quantity")
    if reasons:
        return {"compatible": False, "reasons": reasons}
    with localcontext() as ctx:
        ctx.prec = 100
        raw = number(measurement["mean"]) / quantity
        if raw < 0:
            return {"compatible": False, "reasons": ["carbon_removals_require_extended_evidence"]}
        if abs(raw) >= Decimal("10000000000"):
            return {"compatible": False, "reasons": ["engine_numeric_range"]}
        rounded = raw.quantize(Decimal("0.0000000001"), rounding=ROUND_HALF_EVEN)
        if raw != 0 and rounded == 0:
            return {"compatible": False, "reasons": ["engine_precision_underflow"]}
    return {"compatible": True, "reasons": [], "lcia_method": method, "indicator": "gwp",
            "lifecycle_scope": "A1-A3", "upstream_scope": "A1A2A3", "declared_unit": unit,
            "measurement": measurement, "normalized_value": str(raw), "version_value": str(rounded),
            "input_unit": unit["unit"], "result_unit": "kgCO2e", "rounding": "ROUND_HALF_EVEN/10dp"}
