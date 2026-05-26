"""Interfaz para extraer datos desde evidencias documentales de obra."""
from .documentos_obra import extraer_evidencia_estructurada, extraer_texto_archivo


class ExtractorDocumentos:
    @staticmethod
    def extraer_texto(archivo):
        return extraer_texto_archivo(archivo)

    @staticmethod
    def extraer_estructura_desde_texto(texto):
        return extraer_evidencia_estructurada(texto)


__all__ = ["ExtractorDocumentos"]
