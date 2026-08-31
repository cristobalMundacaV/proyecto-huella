from typing import Protocol

from .document_claim_normalization import normalize_provider_claims
from .document_claims import DocumentClaims, safe_document_claims
from .openai_document_provider import OpenAIDocumentProvider


class DocumentExtractor(Protocol):
    def extract(self, upload, *, text="", heuristic=None) -> DocumentClaims: ...


class TextHeuristicExtractor:
    origin = "texto_heuristico"

    def extract(self, upload, *, text="", heuristic=None):
        raw = heuristic(text) if heuristic else {}
        claims, trace = normalize_provider_claims(raw.get("claims") or {}, self.origin)
        for item in trace.values():
            if item["confianza"] is None:
                item["confianza"] = raw.get("confianza")
        return DocumentClaims(
            tipo_documento=raw.get("tipo_documento") or "otro",
            relevancia_detectada=raw.get("relevancia_detectada") or ("parcialmente_pertinente" if text else "indeterminado"),
            confianza=float(raw.get("confianza") or 0),
            texto_extraido=text or "",
            claims=claims,
            claims_trazables=trace,
            origen_extraccion=self.origin,
            motivo_relevancia=raw.get("motivo_relevancia") or "",
        )


class VisualAIExtractor:
    origin = "openai_visual"

    def __init__(self, provider=None):
        self.provider = provider or OpenAIDocumentProvider()

    def extract(self, upload, *, text="", heuristic=None):
        try:
            raw = self.provider.extract_visual(upload)
        except Exception:
            raw = None
        if not raw:
            return safe_document_claims(origin="visual_no_disponible")
        claims, trace = normalize_provider_claims(raw.get("claims") or {}, self.origin)
        return DocumentClaims(
            tipo_documento=raw.get("tipo_documento") or "otro",
            relevancia_detectada=raw.get("relevancia_detectada") or "indeterminado",
            confianza=float(raw.get("confianza_clasificacion") or raw.get("confianza") or 0),
            texto_extraido=text or "",
            claims=claims,
            claims_trazables=trace,
            origen_extraccion=self.origin,
            motivo_relevancia=raw.get("motivo_relevancia") or "",
            legibilidad=raw.get("legibilidad") or "",
            confianza_extraccion=raw.get("confianza_extraccion"),
        )


def select_document_extractor(*, text, provider=None):
    if text:
        return TextHeuristicExtractor()
    return VisualAIExtractor(provider=provider)
