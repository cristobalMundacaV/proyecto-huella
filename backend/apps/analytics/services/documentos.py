from __future__ import annotations

import json
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
    parts = []

    for page in reader.pages:
        parts.append(page.extract_text() or "")

    return "\n".join(parts).strip()


def _extract_docx_text(file_obj):
    if Document is None:
        raise ValueError("python-docx no esta instalado para leer DOCX")

    try:
        file_obj.seek(0)
    except Exception:
        pass

    document = Document(file_obj)
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    return "\n".join(parts).strip()


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


def inferir_documento_desde_texto(texto):
    cleaned_text = texto or ""
    lower_text = cleaned_text.lower()
    tipo_documento = "documento_generico"

    if "factura" in lower_text and ("diesel" in lower_text or "combustible" in lower_text):
        tipo_documento = "factura_combustible"
    elif "guia" in lower_text or "guía" in lower_text:
        tipo_documento = "guia_despacho"
    elif "docx" in lower_text:
        tipo_documento = "documento_oficina"

    fecha = _normalize_date(
        _first_match(r"(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4}|\d{2}[/-]\d{2}[/-]\d{2})", cleaned_text)
    )
    litros_match = _first_match(
        r"(?:litros(?:\s+diesel)?|lts|l)\s*:?\s*(\d+(?:[.,]\d+)?)",
        cleaned_text,
    )

    if not litros_match:
        litros_match = _first_match(
            r"(\d+(?:[.,]\d+)?)\s*(?:litros(?:\s+diesel)?|lts|l\b)",
            cleaned_text,
        )

    litros_diesel = _normalize_number(litros_match)
    patente = _first_match(r"(?:patente)\s*:?\s*([A-Z0-9-]{5,10})", cleaned_text)
    id_lote = _first_match(r"(LOTE-[A-Z0-9-]+)", cleaned_text)

    matched_fields = sum(
        1
        for value in [fecha, litros_diesel, patente, id_lote]
        if value not in (None, "")
    )
    confianza = round(min(0.45 + matched_fields * 0.12, 0.96), 2)

    return {
        "tipo_documento": tipo_documento,
        "fecha": fecha,
        "litros_diesel": litros_diesel,
        "patente": patente,
        "id_lote": id_lote,
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
        "tipo_documento": data.get("tipo_documento") or fallback["tipo_documento"],
        "fecha": _normalize_date(data.get("fecha") or fallback["fecha"]),
        "litros_diesel": data.get("litros_diesel", data.get("litros_combustible")),
        "patente": data.get("patente") or fallback["patente"],
        "id_lote": data.get("id_lote") or fallback["id_lote"],
        "confianza": data.get("confianza", fallback["confianza"]),
        "fuente": data.get("fuente") or fallback["fuente"],
    }

    if normalized["litros_diesel"] is None:
        normalized["litros_diesel"] = fallback["litros_diesel"]

    try:
        normalized["confianza"] = float(normalized["confianza"])
    except (TypeError, ValueError):
        normalized["confianza"] = fallback["confianza"]

    return normalized


def extraer_documento_estructurado(texto):
    fallback = inferir_documento_desde_texto(texto)

    if not settings.OPENAI_API_KEY:
        return fallback

    prompt = f"""
Eres un extractor de datos documentales para una plataforma de trazabilidad ambiental.

Devuelve SOLO JSON valido, sin markdown ni explicaciones, con estas claves exactas:
- tipo_documento
- fecha
- litros_diesel
- patente
- id_lote
- confianza

Reglas:
- Si un dato no aparece, usa null.
- fecha debe ir en formato ISO YYYY-MM-DD si puedes inferirla.
- confianza debe ser un numero entre 0 y 1.

Texto del documento:
{texto}
"""

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )
        parsed = _parse_json_blob(response.output_text)
        normalized = _normalize_ai_output(parsed, fallback)
        normalized["fuente"] = "ia"
        return normalized
    except (APIConnectionError, APIStatusError, ValueError, json.JSONDecodeError):
        return fallback


def extraer_documento_desde_archivo(archivo):
    resultado_texto = extraer_texto_archivo(archivo)
    texto = resultado_texto["texto_extraido"]
    structured = extraer_documento_estructurado(texto)

    return {
        **resultado_texto,
        **structured,
        "texto_extraido": texto,
    }
