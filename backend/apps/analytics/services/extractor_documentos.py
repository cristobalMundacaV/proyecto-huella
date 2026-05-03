"""Wrapper para `services.documentos` proporcionando una interfaz `ExtractorDocumentos`."""
from .documentos import extraer_documento_estructurado, extraer_texto_archivo


class ExtractorDocumentos:
    @staticmethod
    def extraer_texto(archivo):
        return extraer_texto_archivo(archivo)

    @staticmethod
    def extraer_estructura_desde_texto(texto):
        return extraer_documento_estructurado(texto)


__all__ = ["ExtractorDocumentos"]
