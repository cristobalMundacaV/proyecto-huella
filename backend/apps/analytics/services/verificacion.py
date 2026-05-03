from django.utils import timezone

from .carbono import calcular_balance_lote
from .confianza import calcular_confianza_lote
from .pasaporte import calcular_pasaporte_lote


def generar_resumen_verificacion(lote):
    balance = calcular_balance_lote(lote)
    pasaporte = calcular_pasaporte_lote(lote)
    confianza = calcular_confianza_lote(lote)

    return {
        "id_lote": lote.id_lote,
        "estado_pasaporte": pasaporte["estado_pasaporte"],
        "fecha_emision": timezone.now(),
        "aserradero": lote.empresa_aserradero,
        "especie": lote.especie,
        "volumen_m3": lote.volumen_m3,
        "emisiones_generadas_kg_co2e": balance["emisiones_generadas_kg_co2e"],
        "co2_almacenado_kg": balance["co2_almacenado_kg"],
        "balance_neto_kg_co2e": balance["balance_neto_kg_co2e"],
        "estado_balance": balance["estado_balance"],
        "descripcion_balance": balance["descripcion_balance"],
        "confianza_score": confianza["confianza_score"],
        "estado_confianza": confianza["estado_confianza"],
        "verificado": True,
    }
