from __future__ import annotations

import json
import base64
import mimetypes
import re
from datetime import datetime
from pathlib import Path

from django.conf import settings
from openai import APIConnectionError, APIStatusError, OpenAI

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


def _read_bytes(file_obj):
    try:
        file_obj.seek(0)
    except Exception:
        pass

    content = file_obj.read()

    try:
        file_obj.seek(0)
    except Exception:
        pass

    return content


def _decode_text(content):
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    return ""


def _extract_pdf_text(file_obj):
    if PdfReader is None:
        raise ValueError("pypdf no esta instalado para leer PDF digital")

    try:
        file_obj.seek(0)
    except Exception:
        pass

    reader = PdfReader(file_obj)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx_text(file_obj):
    if Document is None:
        raise ValueError("python-docx no esta instalado para leer DOCX")

    try:
        file_obj.seek(0)
    except Exception:
        pass

    document = Document(file_obj)
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()


def extraer_texto_archivo(archivo):
    nombre = (getattr(archivo, "name", "") or "").lower()
    extension = Path(nombre).suffix
    try:
        if extension == ".pdf":
            texto = _extract_pdf_text(archivo)
            formato = "pdf"
        elif extension == ".docx":
            texto = _extract_docx_text(archivo)
            formato = "docx"
        else:
            texto = _decode_text(_read_bytes(archivo))
            formato = "texto" if texto else "binario"

        return {
            "texto_extraido": texto,
            "formato": formato,
            "requiere_ocr": formato in {"pdf", "binario"} and not texto.strip(),
        }
    finally:
        close_method = getattr(archivo, "close", None)
        if callable(close_method):
            try:
                close_method()
            except Exception:
                pass


def _first_match(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    if not match:
        return ""
    for group in match.groups():
        if group:
            return group.strip()
    return ""


def _normalize_number(value):
    if not value:
        return None
    cleaned = value.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def inferir_evidencia_desde_texto(texto):
    cleaned_text = texto or ""
    lower_text = cleaned_text.lower()
    tipo_evidencia = "otro"

    if "factura" in lower_text and ("diesel" in lower_text or "combustible" in lower_text):
        tipo_evidencia = "factura_combustible"
    elif "factura" in lower_text:
        tipo_evidencia = "factura_material"
    elif "guia" in lower_text or "guia de despacho" in lower_text:
        tipo_evidencia = "guia_despacho"
    elif "orden de compra" in lower_text:
        tipo_evidencia = "orden_compra"
    elif "boleta" in lower_text and "electric" in lower_text:
        tipo_evidencia = "boleta_electrica"
    elif "ticket" in lower_text or "pesaje" in lower_text:
        tipo_evidencia = "ticket_pesaje"

    fecha = _normalize_date(
        _first_match(r"(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4}|\d{2}[/-]\d{2}[/-]\d{2})", cleaned_text)
    )
    litros_match = _first_match(
        r"(?:litros(?:\s+diesel)?|lts|l)\s*:?\s*(\d+(?:[.,]\d+)?)",
        cleaned_text,
    ) or _first_match(
        r"(\d+(?:[.,]\d+)?)\s*(?:litros(?:\s+diesel)?|lts|l\b)",
        cleaned_text,
    )
    cantidad_match = _first_match(
        r"(?:cantidad|total|volumen)\s*:?\s*(\d+(?:[.,]\d+)?)",
        cleaned_text,
    )

    litros_combustible = _normalize_number(litros_match)
    cantidad = _normalize_number(cantidad_match) or litros_combustible
    patente = _first_match(r"(?:patente)\s*:?\s*([A-Z0-9-]{5,10})", cleaned_text)
    codigo_obra = _first_match(r"(OBRA-[A-Z0-9-]+)", cleaned_text)
    proveedor = _first_match(r"(?:proveedor|emisor)\s*:?\s*([^\n\r]+)", cleaned_text)

    matched_fields = sum(
        1
        for value in [fecha, cantidad, patente, codigo_obra, proveedor]
        if value not in (None, "")
    )
    confianza = round(min(0.45 + matched_fields * 0.12, 0.96), 2)

    return {
        "tipo_evidencia": tipo_evidencia,
        "fecha": fecha,
        "cantidad": cantidad,
        "litros_combustible": litros_combustible,
        "patente": patente,
        "codigo_obra": codigo_obra,
        "proveedor": proveedor,
        "confianza": confianza,
        "fuente": "heuristica",
    }


def _parse_json_blob(raw_text):
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _normalize_ai_output(data, fallback):
    normalized = {
        "tipo_evidencia": data.get("tipo_evidencia") or fallback["tipo_evidencia"],
        "fecha": _normalize_date(data.get("fecha") or fallback["fecha"]),
        "cantidad": data.get("cantidad", fallback["cantidad"]),
        "litros_combustible": data.get("litros_combustible", fallback["litros_combustible"]),
        "patente": data.get("patente") or fallback["patente"],
        "codigo_obra": data.get("codigo_obra") or fallback["codigo_obra"],
        "proveedor": data.get("proveedor") or fallback["proveedor"],
        "confianza": data.get("confianza", fallback["confianza"]),
        "fuente": data.get("fuente") or fallback["fuente"],
    }
    try:
        normalized["confianza"] = float(normalized["confianza"])
    except (TypeError, ValueError):
        normalized["confianza"] = fallback["confianza"]
    return normalized


def extraer_evidencia_estructurada(texto):
    fallback = inferir_evidencia_desde_texto(texto)
    if not settings.OPENAI_API_KEY:
        return fallback

    prompt = f"""
Eres un extractor de datos documentales para obras de construccion.

Devuelve SOLO JSON valido, sin markdown ni explicaciones, con estas claves exactas:
- tipo_evidencia
- fecha
- cantidad
- litros_combustible
- patente
- codigo_obra
- proveedor
- confianza

Reglas:
- Si un dato no aparece, usa null.
- fecha debe ir en formato ISO YYYY-MM-DD si puedes inferirla.
- confianza debe ser un numero entre 0 y 1.
- Los tipos de evidencia validos son factura_material, guia_despacho, orden_compra, factura_combustible, boleta_electrica, ticket_pesaje, ficha_tecnica_material, certificado_proveedor, registro_maquinaria, registro_retiro_residuos, documento_transporte u otro.

Texto del documento:
{texto}
"""

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(model="gpt-5-mini", input=prompt)
        normalized = _normalize_ai_output(_parse_json_blob(response.output_text), fallback)
        normalized["fuente"] = "ia"
        return normalized
    except (APIConnectionError, APIStatusError, ValueError, json.JSONDecodeError):
        return fallback


def extraer_evidencia_desde_archivo(archivo):
    resultado_texto = extraer_texto_archivo(archivo)
    texto = resultado_texto["texto_extraido"]
    structured = extraer_evidencia_estructurada(texto)

    return {
        **resultado_texto,
        **structured,
        "texto_extraido": texto,
    }


def analizar_archivo_visual(archivo):
    """Analiza imágenes/PDF sin usar los datos declarados como contexto."""
    if not settings.OPENAI_API_KEY:
        return None
    filename = getattr(archivo, "name", "documento") or "documento"
    content_type = getattr(archivo, "content_type", "") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    content = _read_bytes(archivo)
    if not content:
        return None
    encoded = base64.b64encode(content).decode("ascii")
    if content_type.startswith("image/"):
        attachment = {"type": "input_image", "image_url": f"data:{content_type};base64,{encoded}"}
    elif content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        attachment = {"type": "input_file", "filename": filename, "file_data": f"data:application/pdf;base64,{encoded}"}
    else:
        return None
    prompt = """
Analiza exclusivamente el archivo adjunto como evidencia operacional. No inventes datos.
Devuelve SOLO JSON válido con:
tipo_documento, relevancia_detectada, motivo_relevancia, confianza_clasificacion,
legibilidad, confianza_extraccion y claims.
claims puede contener tipo_recurso, cantidad, unidad, fecha, identificador_documento.
Cada claim debe tener valor_original, valor_normalizado y confianza.
Para combustible normaliza Diésel Grado B a diesel y Litros a L. Fechas a YYYY-MM-DD.
Relevancia: pertinente, parcialmente_pertinente, no_pertinente o indeterminado.
Si el campo no es visible, omítelo. Una imagen irrelevante puede ser no_pertinente;
un documento pertinente pero ilegible debe ser indeterminado.
"""
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model="gpt-5-mini",
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, attachment]}],
        )
        return _parse_json_blob(response.output_text)
    except (APIConnectionError, APIStatusError, ValueError, json.JSONDecodeError):
        return None
