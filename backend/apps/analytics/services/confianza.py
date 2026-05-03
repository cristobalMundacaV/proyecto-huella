from .pasaporte import (
    calcular_completitud_score,
    calcular_factor_score,
    calcular_trazabilidad_score,
)


def calcular_documentos_score(lote):
    documentos = list(lote.documentos.all())

    if not documentos:
        return 0

    if any(documento.estado_validacion == "validado" for documento in documentos):
        return 100

    if any(documento.estado_validacion == "pendiente" for documento in documentos):
        return 75

    return 40


def clasificar_confianza(score):
    if score >= 80:
        return "Alta confianza"

    if score >= 50:
        return "Media confianza"

    return "Baja confianza"


def calcular_confianza_lote(lote):
    datos_completos_score = calcular_completitud_score(lote)
    documentos_score = calcular_documentos_score(lote)
    factores_validos_score = calcular_factor_score(lote)
    trazabilidad_score = calcular_trazabilidad_score(lote)
    confianza_score = round(
        (datos_completos_score * 0.30)
        + (documentos_score * 0.25)
        + (factores_validos_score * 0.25)
        + (trazabilidad_score * 0.20)
    )

    return {
        "id_lote": lote.id_lote,
        "datos_completos_score": datos_completos_score,
        "documentos_adjuntos_score": documentos_score,
        "factores_validos_score": factores_validos_score,
        "trazabilidad_confianza_score": trazabilidad_score,
        "confianza_score": confianza_score,
        "estado_confianza": clasificar_confianza(confianza_score),
        "descripcion_confianza": (
            "La confianza del dato mide la calidad del respaldo usado para "
            "defender el calculo; no representa la viabilidad de una recomendacion."
        ),
    }
