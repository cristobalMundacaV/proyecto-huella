"""Calculadora de transporte: funciones para estimar litros y emisiones desde datos de ruta."""
from decimal import Decimal
from ..models import TransporteLote


class CalculadoraTransporte:
    @staticmethod
    def estimar_litros(distancia_km: Decimal, consumo_litro_km: Decimal) -> Decimal:
        return distancia_km * consumo_litro_km

    @staticmethod
    def crear_transporte(lote, vehiculo, patente, distancia_km, consumo_estimado_litro_km=Decimal("0.3")):
        t = TransporteLote.objects.create(
            lote=lote,
            vehiculo=vehiculo,
            patente=patente,
            latitud=0,
            longitud=0,
            fecha_hora=None,
            ruta="",
            distancia_km=distancia_km,
            consumo_estimado_litro_km=consumo_estimado_litro_km,
        )
        return t


__all__ = ["CalculadoraTransporte"]
