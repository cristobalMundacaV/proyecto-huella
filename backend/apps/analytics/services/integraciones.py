from decimal import Decimal

from .carbono import calcular_balance_lote, calcular_carbono_almacenado
from .confianza import calcular_confianza_lote
from .pasaporte import calcular_pasaporte_lote


def to_float(value):
    if isinstance(value, Decimal):
        return float(value)

    return value


def normalizar_pasaporte(estado):
    return estado.replace("Pasaporte ", "")


def construir_payload_lote_bim(lote):
    carbono = calcular_carbono_almacenado(lote)
    balance = calcular_balance_lote(lote)
    pasaporte = calcular_pasaporte_lote(lote)
    confianza = calcular_confianza_lote(lote)
    producto = f"{lote.especie} dimensionado"

    return {
        "lote": lote.id_lote,
        "producto": producto,
        "aserradero": lote.empresa_aserradero,
        "especie": lote.especie,
        "volumen_m3": to_float(lote.volumen_m3),
        "origen": lote.origen,
        "emisiones_kgco2e": to_float(balance["emisiones_generadas_kg_co2e"]),
        "co2_almacenado": to_float(balance["co2_almacenado_kg"]),
        "balance_neto": to_float(balance["balance_neto_kg_co2e"]),
        "pasaporte": normalizar_pasaporte(pasaporte["estado_pasaporte"]),
        "estado_pasaporte": pasaporte["estado_pasaporte"],
        "confianza_score": confianza["confianza_score"],
        "estado_confianza": confianza["estado_confianza"],
        "bim": {
            "material_name": producto,
            "classification": "wood.product.passport",
            "ifc_material": lote.especie,
            "property_set": "Pset_HuellaPasaporteVerde",
            "properties": {
                "LoteId": lote.id_lote,
                "Aserradero": lote.empresa_aserradero,
                "VolumenM3": to_float(lote.volumen_m3),
                "EmisionesKgCO2e": to_float(balance["emisiones_generadas_kg_co2e"]),
                "CO2AlmacenadoKg": to_float(balance["co2_almacenado_kg"]),
                "BalanceNetoKgCO2e": to_float(balance["balance_neto_kg_co2e"]),
                "EstadoPasaporte": pasaporte["estado_pasaporte"],
                "ConfianzaDato": confianza["estado_confianza"],
            },
        },
        "ficha_tecnica": {
            "densidad_kg_m3": to_float(carbono["densidad_kg_m3"]),
            "porcentaje_carbono": to_float(carbono["porcentaje_carbono"]),
            "masa_madera_kg": to_float(carbono["masa_madera_kg"]),
            "carbono_almacenado_kg": to_float(carbono["carbono_almacenado_kg"]),
            "co2_almacenado_kg": to_float(carbono["co2_almacenado_kg"]),
            "documentos_respaldo": lote.documentos.count(),
            "rutas_transporte": lote.transportes.count(),
        },
    }
