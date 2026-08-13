from collections import defaultdict
from decimal import Decimal

from django.db.models import Q

from ..models import EspecieMadera, RegistroEmision


def _to_decimal(value):
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _to_float(value):
    return float(value or Decimal("0"))


def _normalizar_porcentaje(value):
    value = _to_decimal(value)
    if value is not None and value > 1:
        return value / Decimal("100")
    return value


def _datos_carbono_lote(lote):
    densidad = _to_decimal(lote.densidad_kg_m3)
    porcentaje = _normalizar_porcentaje(lote.porcentaje_carbono)
    especie_ref = None

    if not densidad or not porcentaje:
        especie_ref = EspecieMadera.objects.filter(nombre__iexact=lote.especie).first()

    if not densidad and especie_ref:
        densidad = _to_decimal(especie_ref.densidad_kg_m3)
    if not porcentaje and especie_ref:
        porcentaje = _normalizar_porcentaje(especie_ref.porcentaje_carbono)

    faltantes = []
    if not densidad:
        faltantes.append("densidad_kg_m3")
    if not porcentaje:
        faltantes.append("porcentaje_carbono")
    if not lote.volumen_m3:
        faltantes.append("volumen_m3")

    return densidad, porcentaje, faltantes


def calcular_carbono_almacenado_lote(lote):
    densidad, porcentaje, faltantes = _datos_carbono_lote(lote)
    calculo_completo = not faltantes

    if not calculo_completo:
        return {
            "masa_madera_kg": 0,
            "carbono_almacenado_kg": 0,
            "co2_almacenado_kg": 0,
            "calculo_completo": False,
            "campos_faltantes": faltantes,
        }

    masa_madera_kg = _to_decimal(lote.volumen_m3) * densidad
    carbono_almacenado_kg = masa_madera_kg * porcentaje
    co2_almacenado_kg = carbono_almacenado_kg * Decimal("3.67")

    return {
        "masa_madera_kg": round(_to_float(masa_madera_kg), 3),
        "carbono_almacenado_kg": round(_to_float(carbono_almacenado_kg), 3),
        "co2_almacenado_kg": round(_to_float(co2_almacenado_kg), 3),
        "calculo_completo": True,
        "campos_faltantes": [],
    }


def registros_emision_lote(lote):
    metadata_filter = (
        Q(metadata__lote=lote.lote_id)
        | Q(metadata__lote_id=lote.lote_id)
        | Q(metadata__lote_forestal=lote.lote_id)
    )
    return (
        RegistroEmision.objects.filter(
            Q(lote_forestal=lote) | Q(organizacion=lote.organizacion) & metadata_filter
        )
        .select_related("organizacion", "obra", "etapa", "lote_forestal")
        .distinct()
    )


def calcular_emisiones_generadas_lote(lote):
    registros = registros_emision_lote(lote)
    por_categoria = defaultdict(float)
    por_modulo = defaultdict(float)
    total = Decimal("0")

    for registro in registros:
        emisiones = registro.emisiones_kg_co2e or Decimal("0")
        total += emisiones
        por_categoria[registro.categoria or "Otros"] += _to_float(emisiones)
        metadata = registro.metadata if isinstance(registro.metadata, dict) else {}
        modulo = metadata.get("module") or "sin_modulo"
        por_modulo[modulo] += _to_float(emisiones)

    return {
        "emisiones_generadas_kg_co2e": round(_to_float(total), 3),
        "cantidad_registros_emision": registros.count(),
        "resumen_por_categoria": dict(sorted(por_categoria.items(), key=lambda item: item[1], reverse=True)),
        "resumen_por_modulo": dict(sorted(por_modulo.items(), key=lambda item: item[1], reverse=True)),
    }


def calcular_balance_neto_lote(lote):
    carbono = calcular_carbono_almacenado_lote(lote)
    emisiones = calcular_emisiones_generadas_lote(lote)
    balance = Decimal(str(emisiones["emisiones_generadas_kg_co2e"])) - Decimal(str(carbono["co2_almacenado_kg"]))

    if not carbono["calculo_completo"]:
        estado = "incompleto"
        descripcion = "Faltan datos para calcular correctamente el balance del lote."
    elif balance < 0:
        estado = "favorable"
        descripcion = "El lote almacena mas CO2 del que genero en sus procesos asociados."
    elif balance <= Decimal("500"):
        estado = "intermedio"
        descripcion = "El lote tiene un balance cercano al equilibrio, pero aun puede optimizar transporte, energia o produccion."
    else:
        estado = "critico"
        descripcion = "El lote genero mas CO2 del que almacena segun los datos disponibles."

    return {
        **emisiones,
        "co2_almacenado_kg": carbono["co2_almacenado_kg"],
        "balance_neto_kg_co2e": round(_to_float(balance), 3),
        "estado_balance": estado,
        "descripcion_balance": descripcion,
        "calculo_completo": carbono["calculo_completo"],
        "campos_faltantes": carbono["campos_faltantes"],
    }
