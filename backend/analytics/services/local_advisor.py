def generar_analisis_local(payload):
    total = float(payload.get("total_emisiones", 0) or 0)
    empresa = payload.get("empresa_critica", "la empresa critica")
    actividad = payload.get("actividad_critica", "la actividad critica")
    actividad_normalizada = str(actividad).lower()
    optimizacion = payload.get("optimizacion") or {}

    reduccion = optimizacion.get("reductionPct", None)
    diesel = optimizacion.get("dieselReduction", None)
    electricidad = optimizacion.get("electricityIncrease", None)

    riesgo_score = min(100, total / 50)

    if riesgo_score >= 70:
        riesgo = "alto"
    elif riesgo_score >= 35:
        riesgo = "medio"
    else:
        riesgo = "bajo"

    if actividad_normalizada == "diesel" and total > 3000:
        insight = (
            "La dependencia de diesel es critica y representa un riesgo "
            "financiero, operacional y regulatorio elevado."
        )
    elif actividad_normalizada == "diesel":
        insight = (
            "El diesel concentra el mayor impacto y debe tratarse como el "
            "primer foco de optimizacion operacional."
        )
    elif actividad_normalizada == "electricidad":
        insight = (
            "El consumo electrico domina el impacto, lo que abre oportunidades "
            "claras de eficiencia energetica, gestion de demanda y abastecimiento renovable."
        )
    else:
        insight = (
            f"{actividad} concentra el mayor impacto del dataset, por lo que "
            "debe priorizarse en la siguiente iteracion de mejora."
        )

    recomendacion_por_actividad = {
        "diesel": "acelerar electrificacion, mejorar rutas, reducir uso de generadores y evaluar combustibles alternativos",
        "electricidad": "implementar eficiencia energetica, gestion horaria de consumo y contratos de energia renovable",
    }
    recomendacion = recomendacion_por_actividad.get(
        actividad_normalizada,
        f"revisar procesos asociados a {actividad} y buscar sustitucion tecnologica o eficiencia operacional",
    )

    texto = f"""
Diagnostico:
Huella detecta que el mayor foco de emisiones se concentra en {actividad}, con una empresa critica identificada: {empresa}. El total analizado alcanza {round(total, 1)} kg CO2e.

Insight adaptativo:
{insight}

Riesgo principal:
El score de riesgo estimado es {round(riesgo_score, 1)}/100, clasificado como riesgo {riesgo}. Este nivel exige priorizacion ejecutiva si la organizacion quiere reducir exposicion regulatoria y costos operacionales.

Recomendacion estrategica:
Huella recomienda {recomendacion}.
"""

    if reduccion is not None:
        texto += f"""

Impacto esperado:
El escenario optimizado sugiere una reduccion estimada de {round(reduccion, 1)}%. Para lograrlo, Huella recomienda reducir diesel en {diesel}% y ajustar electricidad en {electricidad}%.
"""

    texto += """

Siguiente accion concreta:
Implementar un plan piloto sobre la empresa critica, medir resultados durante un periodo corto y comparar contra la linea base actual.
"""

    return texto.strip()
