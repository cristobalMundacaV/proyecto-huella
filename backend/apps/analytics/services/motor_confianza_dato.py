"""Pequeño adaptador para el motor de confianza (MotorConfianzaDato)."""
from .confianza import calcular_confianza_lote


class MotorConfianzaDato:
    @staticmethod
    def calcular(lote):
        return calcular_confianza_lote(lote)


__all__ = ["MotorConfianzaDato"]
