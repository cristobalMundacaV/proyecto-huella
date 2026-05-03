from decimal import Decimal

from apps.analytics.models import EspecieMadera

CO2_CONVERSION_FACTOR = Decimal("3.67")


def calcular_carbono_almacenado(lote):
    especie = EspecieMadera.objects.filter(nombre__iexact=lote.especie).first()
    densidad = lote.densidad_kg_m3 or getattr(especie, "densidad_kg_m3", None)
    porcentaje_carbono = lote.porcentaje_carbono or getattr(
        especie,
        "porcentaje_carbono",
        None,
    )

    if densidad is None or porcentaje_carbono is None:
        return {
            "densidad_kg_m3": None,
            "porcentaje_carbono": None,
            "masa_madera_kg": Decimal("0"),
            "carbono_almacenado_kg": Decimal("0"),
            "co2_almacenado_kg": Decimal("0"),
        }

    masa_madera = lote.volumen_m3 * densidad
    carbono_almacenado = masa_madera * porcentaje_carbono
    co2_almacenado = carbono_almacenado * CO2_CONVERSION_FACTOR

    return {
        "densidad_kg_m3": densidad,
        "porcentaje_carbono": porcentaje_carbono,
        "masa_madera_kg": masa_madera,
        "carbono_almacenado_kg": carbono_almacenado,
        "co2_almacenado_kg": co2_almacenado,
    }


def interpretar_balance(balance_neto):
    if balance_neto < 0:
        return {
            "estado": "favorable",
            "descripcion": "Almacena mas CO2 del que emitio en el proceso.",
        }

    if balance_neto <= Decimal("500"):
        return {
            "estado": "medio",
            "descripcion": "Tiene un balance bajo, con desempeno ambiental intermedio.",
        }

    return {
        "estado": "critico",
        "descripcion": "Emitio mas CO2 del que almacena en la madera.",
    }


def calcular_balance_lote(lote):
    carbono = calcular_carbono_almacenado(lote)
    emisiones_generadas = Decimal(str(lote.emisiones_kg_co2e))
    co2_almacenado = Decimal(str(carbono["co2_almacenado_kg"]))
    balance_neto = emisiones_generadas - co2_almacenado
    interpretacion = interpretar_balance(balance_neto)

    return {
        "id_lote": lote.id_lote,
        "emisiones_generadas_kg_co2e": emisiones_generadas,
        "co2_almacenado_kg": co2_almacenado,
        "balance_neto_kg_co2e": balance_neto,
        "estado_balance": interpretacion["estado"],
        "descripcion_balance": interpretacion["descripcion"],
    }
