import re
import unicodedata
from datetime import datetime

from .document_extractors import select_document_extractor

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

    if filename.lower().endswith((".pdf", ".docx")):
        from .documentos_obra import extraer_texto_archivo

        try:
            return extraer_texto_archivo(upload)["texto_extraido"]
        except (ValueError, OSError):
            return ""

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

    return ""


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
    detected = detect_document_type(text)
    document_hint = detect_document_type(filename)
    quantity = extract_number_near_units(text)

    confidence = min(0.95, 0.35 + (detected.get("score", 0) * 0.15))
    if not text:
        confidence = min(confidence, 0.55)

    document_date = extract_date(text)
    heuristic_claims = extract_operational_claims(
        text,
        detected["tipo_documento"],
        quantity,
        document_date,
    )
    def heuristic_contract(_text):
        if detected["tipo_documento"] != "otro" and confidence >= 0.75:
            relevance = "pertinente"
        elif detected["tipo_documento"] != "otro" or text:
            relevance = "parcialmente_pertinente"
        else:
            relevance = "indeterminado"
        return {
            "tipo_documento": detected["tipo_documento"],
            "relevancia_detectada": relevance,
            "confianza": round(confidence, 2),
            "claims": heuristic_claims,
        }

    empty_file = getattr(upload, "size", None) == 0
    extractor = select_document_extractor(upload=upload, text=text) if not empty_file else None
    if empty_file:
        from .document_claims import safe_document_claims

        document_claims = safe_document_claims(
            text=text,
            origin="archivo_vacio",
            status="empty",
            extractor="selector",
            failure_code="empty_file",
        ).to_dict()
    elif extractor is None:
        from .document_claims import safe_document_claims

        document_claims = safe_document_claims(
            text=text,
            origin="formato_no_soportado",
            status="unsupported",
            extractor="selector",
            failure_code="unsupported_mime",
        ).to_dict()
    else:
        document_claims = extractor.extract(
            upload,
            text=text[:8000],
            heuristic=heuristic_contract,
        ).to_dict()
    observed_claims = document_claims["claims"]
    payload = {
        "filename": filename,
        "content_type": content_type,
        "preset": preset,
        "tipo_documento": document_claims["tipo_documento"],
        "tipo_documento_label": detected["label"],
        "proveedor": extract_provider(text, filename),
        "fecha": observed_claims.get("fecha", ""),
        "categoria_sugerida": detected["categoria_sugerida"],
        "fuente_emision_sugerida": detected["fuente_emision_sugerida"],
        "cantidad_sugerida": observed_claims.get("cantidad", ""),
        "unidad_sugerida": observed_claims.get("unidad", ""),
        "factor_sugerido": "",
        "confianza": document_claims["confianza"],
        "texto_extraido": document_claims["texto_extraido"],
        "claims": document_claims["claims"],
        "claims_trazables": document_claims["claims_trazables"],
        "relevancia_detectada": document_claims["relevancia_detectada"],
        "origen_extraccion": document_claims["origen_extraccion"],
        "motivo_relevancia": document_claims["motivo_relevancia"],
        "legibilidad": document_claims["legibilidad"],
        "confianza_extraccion": document_claims["confianza_extraccion"],
        "execution_status": document_claims["execution_status"],
        "extractor_used": document_claims["extractor_used"],
        "provider_used": document_claims["provider_used"],
        "failure_code": document_claims["failure_code"],
        "claims_count": document_claims["claims_count"],
        "campos_faltantes": [],
        "expected": {},
        "document_hint": {
            "tipo_documento": document_hint["tipo_documento"],
            "tipo_documento_label": document_hint["label"],
            "origen": "nombre_archivo",
        },
        "metadata": {
            "extraction_engine": document_claims["extractor_used"],
            "provider": document_claims["provider_used"],
            "detected_by": "observed_content",
            "score": detected.get("score", 0),
            "requires_human_review": confidence < 0.75,
            **document_claims["extraction_metadata"],
        },
    }

    payload["campos_faltantes"] = build_missing_fields(payload)
    return payload
