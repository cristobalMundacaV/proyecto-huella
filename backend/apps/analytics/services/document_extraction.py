import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation

DOCUMENT_RULES = [
    {
        "tipo_documento": "factura_combustible",
        "label": "Factura de combustible",
        "keywords": [
            "combustible",
            "diesel",
            "diésel",
            "bencina",
            "gasolina",
            "copec",
            "shell",
            "petrobras",
            "litros",
        ],
        "categoria_sugerida": "Transporte",
        "fuente_emision_sugerida": "Consumo de combustible",
        "unidad_sugerida": "litros diesel",
    },
    {
        "tipo_documento": "factura_material",
        "label": "Factura de materiales",
        "keywords": [
            "hormigon",
            "hormigón",
            "cemento",
            "acero",
            "arido",
            "árido",
            "material",
            "madera",
            "yeso",
        ],
        "categoria_sugerida": "Materiales",
        "fuente_emision_sugerida": "Materiales de construcción",
        "unidad_sugerida": "unidad",
    },
    {
        "tipo_documento": "boleta_electrica",
        "label": "Boleta eléctrica",
        "keywords": [
            "electricidad",
            "energia",
            "energía",
            "kwh",
            "cge",
            "enel",
            "saesa",
            "consumo electrico",
        ],
        "categoria_sugerida": "Energia",
        "fuente_emision_sugerida": "Consumo eléctrico",
        "unidad_sugerida": "kWh",
    },
    {
        "tipo_documento": "factura_agua",
        "label": "Factura de agua",
        "keywords": [
            "agua",
            "essbio",
            "essal",
            "aguas",
            "m3",
            "metros cubicos",
            "metros cúbicos",
        ],
        "categoria_sugerida": "Agua",
        "fuente_emision_sugerida": "Consumo de agua",
        "unidad_sugerida": "m3",
    },
    {
        "tipo_documento": "guia_despacho",
        "label": "Guía de despacho",
        "keywords": [
            "guia de despacho",
            "guía de despacho",
            "despacho",
            "traslado",
            "remision",
            "remisión",
        ],
        "categoria_sugerida": "Transporte",
        "fuente_emision_sugerida": "Despacho / transporte",
        "unidad_sugerida": "km",
    },
    {
        "tipo_documento": "ticket_pesaje",
        "label": "Ticket de pesaje",
        "keywords": [
            "ticket pesaje",
            "pesaje",
            "peso neto",
            "toneladas",
            "kg",
            "bascula",
            "báscula",
        ],
        "categoria_sugerida": "Residuos",
        "fuente_emision_sugerida": "Retiro de residuos",
        "unidad_sugerida": "kg",
    },
    {
        "tipo_documento": "certificado_residuos",
        "label": "Certificado de residuos",
        "keywords": [
            "residuo",
            "residuos",
            "gestor",
            "disposicion",
            "disposición",
            "valorizacion",
            "valorización",
            "certificado",
        ],
        "categoria_sugerida": "Residuos",
        "fuente_emision_sugerida": "Gestión de residuos",
        "unidad_sugerida": "kg",
    },
    {
        "tipo_documento": "registro_maquinaria",
        "label": "Registro de maquinaria",
        "keywords": [
            "maquinaria",
            "excavadora",
            "retroexcavadora",
            "grua",
            "grúa",
            "horometro",
            "horómetro",
            "horas maquina",
        ],
        "categoria_sugerida": "Maquinaria",
        "fuente_emision_sugerida": "Uso de maquinaria",
        "unidad_sugerida": "horas",
    },
    {
        "tipo_documento": "documento_transporte",
        "label": "Documento de transporte",
        "keywords": [
            "ruta",
            "viaje",
            "origen",
            "destino",
            "patente",
            "camion",
            "camión",
            "conductor",
        ],
        "categoria_sugerida": "Transporte",
        "fuente_emision_sugerida": "Transporte operativo",
        "unidad_sugerida": "km",
    },
]


def normalize_text(value):
    value = str(value or "").lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def read_upload_text(upload):
    """
    Primera versión segura:
    - Lee TXT, CSV, HTML o archivos textuales.
    - Para PDF/imagen/Excel conserva análisis por nombre de archivo.
    - Deja preparada la estructura para OCR/IA posterior.
    """
    filename = getattr(upload, "name", "") or ""
    content_type = getattr(upload, "content_type", "") or ""

    if hasattr(upload, "seek"):
        upload.seek(0)

    raw = b""
    try:
        raw = upload.read(120_000)
    except Exception:
        raw = b""
    finally:
        if hasattr(upload, "seek"):
            upload.seek(0)

    can_decode = content_type.startswith("text/") or filename.lower().endswith(
        (".txt", ".csv", ".html", ".htm", ".xml")
    )

    if not can_decode:
        return ""

    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def detect_document_type(text):
    normalized = normalize_text(text)
    best_rule = None
    best_score = 0

    for rule in DOCUMENT_RULES:
        score = sum(
            1 for keyword in rule["keywords"] if normalize_text(keyword) in normalized
        )
        if score > best_score:
            best_score = score
            best_rule = rule

    if not best_rule:
        return {
            "tipo_documento": "otro",
            "label": "Documento ambiental",
            "categoria_sugerida": "Otros",
            "fuente_emision_sugerida": "Documento ambiental",
            "unidad_sugerida": "unidad",
            "score": 0,
        }

    return {**best_rule, "score": best_score}


def extract_date(text):
    patterns = [
        r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",
        r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        groups = match.groups()

        try:
            if len(groups[0]) == 4:
                parsed = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
            else:
                parsed = datetime(int(groups[2]), int(groups[1]), int(groups[0]))

            return parsed.date().isoformat()
        except ValueError:
            continue

    return ""


def extract_number_near_units(text):
    normalized = normalize_text(text)

    unit_patterns = [
        ("litros diesel", r"(\d+(?:[.,]\d+)?)\s*(?:litros|lts|lt|l)\b"),
        ("kWh", r"(\d+(?:[.,]\d+)?)\s*(?:kwh)\b"),
        ("m3", r"(\d+(?:[.,]\d+)?)\s*(?:m3|m\^3|metros cubicos|metros cúbicos)\b"),
        ("kg", r"(\d+(?:[.,]\d+)?)\s*(?:kg|kilos)\b"),
        ("ton", r"(\d+(?:[.,]\d+)?)\s*(?:ton|toneladas)\b"),
        ("km", r"(\d+(?:[.,]\d+)?)\s*(?:km|kilometros|kilómetros)\b"),
        ("horas", r"(\d+(?:[.,]\d+)?)\s*(?:horas|hrs|hr)\b"),
    ]

    for unit, pattern in unit_patterns:
        match = re.search(pattern, normalized)
        if match:
            raw_number = match.group(1)
            separator_match = re.fullmatch(r"([1-9]\d{0,2})[.,](\d{3})", raw_number)
            normalized_number = (
                "".join(separator_match.groups())
                if separator_match
                else raw_number.replace(",", ".")
            )
            return {
                "cantidad_sugerida": normalized_number,
                "unidad_sugerida": unit,
            }

    return {
        "cantidad_sugerida": "",
        "unidad_sugerida": "",
    }


def extract_provider(text, filename):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    provider_keywords = [
        "razon social",
        "razón social",
        "proveedor",
        "emisor",
        "empresa",
    ]

    for line in lines[:30]:
        normalized_line = normalize_text(line)
        if any(keyword in normalized_line for keyword in provider_keywords):
            cleaned = re.sub(
                r"(?i)(raz[oó]n social|proveedor|emisor|empresa)\s*[:\-]?\s*", "", line
            ).strip()
            if cleaned:
                return cleaned[:120]

    filename_without_ext = re.sub(r"\.[a-zA-Z0-9]+$", "", filename or "")
    return filename_without_ext.replace("_", " ").replace("-", " ").strip()[:120]


def extract_operational_claims(text, detected_type, quantity, document_date):
    normalized = normalize_text(text)
    claims = {}
    if quantity.get("cantidad_sugerida"):
        claims["cantidad"] = quantity["cantidad_sugerida"]
        claims["unidad"] = quantity.get("unidad_sugerida", "")
    if document_date:
        claims["fecha"] = document_date
    if detected_type == "factura_combustible":
        fuels = {
            "diesel": ("diesel", "diésel", "petroleo diesel", "petróleo diésel"),
            "gasolina": ("gasolina", "bencina"),
            "gas_licuado": ("gas licuado", "glp"),
            "gas_natural": ("gas natural", "gnc"),
        }
        matches = [key for key, aliases in fuels.items() if any(normalize_text(alias) in normalized for alias in aliases)]
        if len(matches) == 1:
            claims["tipo_recurso"] = matches[0]
    identifier = re.search(r"\b(?:factura|folio|documento|n[°ºo])\s*[:#-]?\s*([a-z0-9-]{3,30})", normalized)
    if identifier:
        claims["identificador_documento"] = identifier.group(1)
    return claims


def _normalize_visual_claims(payload):
    def deterministic(field, original, suggested):
        raw = str(original if original not in (None, "") else suggested or "").strip()
        normalized = normalize_text(raw)
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
            aliases = {"l": "L", "lt": "L", "lts": "L", "litro": "L", "litros": "L", "m3": "m3", "kg": "kg", "t": "t", "ton": "t", "toneladas": "t"}
            return aliases.get(normalized)
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
            return extract_date(raw)
        if field == "identificador_documento":
            return raw[:120] or None
        return None

    simple = {}
    trace = {}
    for field, claim in (payload.get("claims") or {}).items():
        if not isinstance(claim, dict):
            continue
        original = claim.get("valor_original")
        normalized = deterministic(field, original, claim.get("valor_normalizado"))
        if normalized in (None, ""):
            continue
        simple[field] = normalized
        trace[field] = {
            "valor_original": original,
            "valor_normalizado": normalized,
            "confianza": claim.get("confianza"),
            "origen": "analisis_visual_archivo",
        }
    return simple, trace


def build_missing_fields(payload):
    missing = []

    if not payload.get("fecha"):
        missing.append("fecha_documento")

    if not payload.get("cantidad_sugerida"):
        missing.append("cantidad")

    if not payload.get("unidad_sugerida"):
        missing.append("unidad")

    if payload.get("tipo_documento") == "otro":
        missing.append("tipo_documento")

    return missing


def extract_environmental_document(upload, preset="construccion"):
    filename = getattr(upload, "name", "") or "documento"
    content_type = getattr(upload, "content_type", "") or ""
    text = read_upload_text(upload)
    combined_text = f"{filename}\n{text}"
    detected = detect_document_type(combined_text)
    quantity = extract_number_near_units(combined_text)
    visual = None
    if not text:
        from .documentos_obra import analizar_archivo_visual

        visual = analizar_archivo_visual(upload)

    unidad = (
        quantity.get("unidad_sugerida") or detected.get("unidad_sugerida") or "unidad"
    )
    confidence = min(0.95, 0.35 + (detected.get("score", 0) * 0.15))
    if not text:
        confidence = min(confidence, 0.55)

    document_date = extract_date(combined_text)
    visual_claims, visual_trace = _normalize_visual_claims(visual or {})
    heuristic_claims = extract_operational_claims(
        combined_text,
        detected["tipo_documento"],
        quantity,
        document_date,
    )
    claims = visual_claims or heuristic_claims
    payload = {
        "filename": filename,
        "content_type": content_type,
        "preset": preset,
        "tipo_documento": (visual or {}).get("tipo_documento") or detected["tipo_documento"],
        "tipo_documento_label": detected["label"],
        "proveedor": extract_provider(text, filename),
        "fecha": document_date,
        "categoria_sugerida": detected["categoria_sugerida"],
        "fuente_emision_sugerida": detected["fuente_emision_sugerida"],
        "cantidad_sugerida": quantity.get("cantidad_sugerida", ""),
        "unidad_sugerida": unidad,
        "factor_sugerido": "",
        "confianza": (visual or {}).get("confianza_clasificacion") or round(confidence, 2),
        "texto_extraido": text[:8000],
        "claims": claims,
        "claims_trazables": visual_trace or {
            field: {
                "valor_original": value,
                "valor_normalizado": value,
                "confianza": round(confidence, 2),
                "origen": "extraccion_textual_archivo",
            }
            for field, value in heuristic_claims.items()
        },
        "relevancia_detectada": (visual or {}).get("relevancia_detectada"),
        "motivo_relevancia": (visual or {}).get("motivo_relevancia"),
        "legibilidad": (visual or {}).get("legibilidad"),
        "confianza_extraccion": (visual or {}).get("confianza_extraccion"),
        "campos_faltantes": [],
        "metadata": {
            "extraction_engine": "heuristic_v1",
            "detected_by": "filename_and_text",
            "score": detected.get("score", 0),
            "requires_human_review": confidence < 0.75,
        },
    }

    payload["campos_faltantes"] = build_missing_fields(payload)
    return payload
