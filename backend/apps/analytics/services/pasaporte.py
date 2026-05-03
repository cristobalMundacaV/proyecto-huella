from decimal import Decimal

from .carbono import calcular_balance_lote, calcular_carbono_almacenado


def _is_present(value):
    if value is None:
        return False

    if isinstance(value, Decimal):
        return value > 0

    if isinstance(value, str):
        return bool(value.strip())

    return bool(value)


def _score(items):
    if not items:
        return 0

    completed = sum(1 for item in items if item)
    return round((completed / len(items)) * 100)


def calcular_trazabilidad_score(lote):
    return _score(
        [
            _is_present(lote.id_lote),
            _is_present(lote.empresa_aserradero),
            _is_present(lote.fecha),
            _is_present(lote.especie),
            _is_present(lote.volumen_m3),
            _is_present(lote.origen),
        ]
    )


def calcular_completitud_score(lote):
    actividades = list(lote.actividades.all())
    lote_items = [
        _is_present(lote.id_lote),
        _is_present(lote.empresa_aserradero),
        _is_present(lote.fecha),
        _is_present(lote.especie),
        _is_present(lote.volumen_m3),
        _is_present(lote.origen),
        bool(actividades),
    ]
    actividad_items = []

    for actividad in actividades:
        actividad_items.extend(
            [
                _is_present(actividad.actividad),
                _is_present(actividad.cantidad),
                _is_present(actividad.unidad),
                _is_present(actividad.factor_emision),
            ]
        )

    return _score([*lote_items, *actividad_items])


def calcular_factor_score(lote):
    actividades = list(lote.actividades.all())

    if not actividades:
        return 0

    return _score([_is_present(actividad.factor_emision) for actividad in actividades])


def clasificar_estado_pasaporte(score, balance_calculado):
    if not balance_calculado or score < 50:
        return "Sin pasaporte"

    if score < 80:
        return "Pasaporte Base"

    if score < 90:
        return "Pasaporte Verde"

    return "Pasaporte Verde Plus"


def calcular_pasaporte_lote(lote):
    trazabilidad_score = calcular_trazabilidad_score(lote)
    completitud_score = calcular_completitud_score(lote)
    factor_score = calcular_factor_score(lote)
    carbono = calcular_carbono_almacenado(lote)
    balance = calcular_balance_lote(lote)
    balance_calculado = carbono["densidad_kg_m3"] is not None
    pasaporte_score = min(
        trazabilidad_score,
        completitud_score,
        factor_score,
        100 if balance_calculado else 0,
    )
    estado_pasaporte = clasificar_estado_pasaporte(
        pasaporte_score,
        balance_calculado,
    )

    if estado_pasaporte in {"Pasaporte Verde", "Pasaporte Verde Plus"}:
        razon = (
            f"Este lote califica para {estado_pasaporte} porque tiene "
            "trazabilidad suficiente, datos completos, factores encontrados "
            "y balance de carbono calculado."
        )
    elif estado_pasaporte == "Pasaporte Base":
        razon = (
            "Este lote tiene informacion suficiente para Pasaporte Base, "
            "pero aun no alcanza los umbrales de Pasaporte Verde."
        )
    else:
        razon = (
            "Este lote aun no califica porque faltan datos, factores de emision "
            "o balance de carbono calculado."
        )

    return {
        "id_lote": lote.id_lote,
        "trazabilidad_score": trazabilidad_score,
        "completitud_score": completitud_score,
        "factor_score": factor_score,
        "balance_neto": balance["balance_neto_kg_co2e"],
        "balance_calculado": balance_calculado,
        "pasaporte_score": pasaporte_score,
        "estado_pasaporte": estado_pasaporte,
        "razon_pasaporte": razon,
    }
