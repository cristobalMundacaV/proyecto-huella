import base64
import json
import mimetypes
import re

from django.conf import settings
from openai import APIConnectionError, APIStatusError, OpenAI


def _parse_json(raw):
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1] if start >= 0 and end >= 0 else text)


class OpenAIDocumentProvider:
    def __init__(self, api_key=None, model="gpt-5-mini"):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model

    @property
    def available(self):
        return bool(self.api_key)

    def extract_visual(self, upload):
        if not self.available:
            return None
        filename = getattr(upload, "name", "documento") or "documento"
        content_type = getattr(upload, "content_type", "") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            upload.seek(0)
        except Exception:
            pass
        content = upload.read()
        try:
            upload.seek(0)
        except Exception:
            pass
        if not content:
            return None
        encoded = base64.b64encode(content).decode("ascii")
        if content_type.startswith("image/"):
            attachment = {"type": "input_image", "image_url": f"data:{content_type};base64,{encoded}"}
        elif content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            attachment = {"type": "input_file", "filename": filename, "file_data": f"data:application/pdf;base64,{encoded}"}
        else:
            return None
        prompt = """Extrae solo datos visibles del archivo. Devuelve JSON con tipo_documento,
relevancia_detectada, motivo_relevancia, confianza_clasificacion, legibilidad,
confianza_extraccion y claims. Cada claim observado usa valor_original y confianza;
puede incluir tipo_recurso, cantidad, unidad, fecha e identificador_documento.
No normalices, no compares con formularios y no decidas calidad ambiental. Omite lo no visible."""
        try:
            response = OpenAI(api_key=self.api_key).responses.create(
                model=self.model,
                input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, attachment]}],
            )
            return _parse_json(response.output_text)
        except (APIConnectionError, APIStatusError, ValueError, json.JSONDecodeError, OSError):
            return None
        except Exception:
            return None

    def extract_text(self, text):
        if not self.available:
            return None
        prompt = f"""Extrae únicamente datos visibles del texto documental. Devuelve JSON con
tipo_evidencia, fecha, cantidad, litros_combustible, patente, codigo_obra, proveedor y confianza.
Usa null para datos ausentes. No decidas calidad ni cálculo ambiental. Texto:\n{text}"""
        try:
            response = OpenAI(api_key=self.api_key).responses.create(model=self.model, input=prompt)
            return _parse_json(response.output_text)
        except (APIConnectionError, APIStatusError, ValueError, json.JSONDecodeError, OSError):
            return None
        except Exception:
            return None
