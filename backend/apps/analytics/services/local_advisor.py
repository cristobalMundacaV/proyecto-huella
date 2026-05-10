from .activity_semantics import is_diesel_activity, is_electricity_activity


def _pick_realistic_initial_reduction(max_reduction_pct):
    if max_reduction_pct <= 0:
        return 20
    return min(35, max(15, round(max_reduction_pct * 0.4)))


def _activity_row(actividad):
    return {"actividad": actividad, "actividad_key": actividad}


def _guess_optimal_activity_reduction(actividad, optimizacion):
    row = _activity_row(actividad)
    if is_diesel_activity(row):
        return optimizacion.get("dieselReduction")
    if is_electricity_activity(row):
        return optimizacion.get("electricityIncrease")
    return optimizacion.get("activityReduction")


def _assess_viability(actividad, max_reduction_pct, optimal_reduction_pct):
    pressure = 0

    if is_diesel_activity(_activity_row(actividad)):
        pressure += 2

    if max_reduction_pct > 50:
        pressure += 2
    elif max_reduction_pct > 35:
        pressure += 1

    if optimal_reduction_pct is not None and float(optimal_reduction_pct) >= 70:
        pressure += 2

    if pressure >= 4:
        return "Baja"
    if pressure >= 2:
        return "Media"
    return "Alta"


def _recommended_range_by_viability(viability):
    if viability == "Baja":
        return (10, 20)
    if viability == "Media":
        return (15, 30)
    return (20, 35)


def _action_levels(actividad):
    return {
        "low": (
            f"🟢 Bajo esfuerzo (5%-15% reduccion): ajustes operativos en {actividad}, "
            "mejor control de consumo, mantenimiento preventivo y disciplina de seguimiento semanal."
        ),
        "medium": (
            f"🟡 Medio impacto (15%-35% reduccion): optimizacion faseada de {actividad} con "
            "cambios de procesos, analitica de desempeno y sustitucion parcial de tecnologia."
        ),
        "high": (
            f"🔴 Transformacional (35%+ reduccion): rediseño estructural de {actividad}, "
            "capex dedicado, renovacion tecnologica y plan de transicion plurianual."
        ),
    }


def generar_analisis_local(payload):
    total = float(payload.get("total_emisiones", 0) or 0)
    unidad = payload.get("unidad_critica") or payload.get("empresa_critica") or "la unidad critica"
    actividad = payload.get("actividad_critica", "la actividad critica")
    actividad_row = _activity_row(actividad)
    optimizacion = payload.get("optimizacion") or {}

    max_reduction_pct = float(optimizacion.get("reductionPct", 0) or 0)
    optimal_reduction_pct = _guess_optimal_activity_reduction(
        actividad,
        optimizacion,
    )
    realistic_reduction_pct = _pick_realistic_initial_reduction(max_reduction_pct)
    viability = _assess_viability(
        actividad,
        max_reduction_pct,
        optimal_reduction_pct,
    )
    realistic_min, realistic_max = _recommended_range_by_viability(viability)
    levels = _action_levels(actividad)

    if is_diesel_activity(actividad_row) and total > 3000:
        insight = (
            "La dependencia de diesel concentra riesgo operativo, de costos y de cumplimiento, "
            "por lo que este frente define el resultado global de descarbonizacion."
        )
    elif is_diesel_activity(actividad_row):
        insight = (
            "El diesel sigue siendo la principal causa de impacto y conviene intervenirlo "
            "antes de distribuir esfuerzos en multiples frentes menores."
        )
    elif is_electricity_activity(actividad_row):
        insight = (
            "El consumo electrico domina la huella; esto habilita mejoras escalables via eficiencia, "
            "gestion de demanda y contratos de energia de menor factor de emision."
        )
    else:
        insight = (
            f"{actividad} concentra la mayor parte del impacto y debe tratarse como frente prioritario "
            "para capturar reducciones relevantes en el corto y mediano plazo."
        )

    intervention_line = (
        f"bajo una intervencion profunda en el uso de {actividad}."
        if is_diesel_activity(actividad_row)
        else f"bajo una intervencion profunda sobre {actividad}."
    )

    optimal_line = (
        f"El potencial maximo identifica una reduccion agregada cercana al {round(max_reduction_pct, 1)}% "
        f"de las emisiones totales, {intervention_line}"
    )

    if realistic_reduction_pct < realistic_min:
        realistic_reduction_pct = realistic_min
    if realistic_reduction_pct > realistic_max:
        realistic_reduction_pct = realistic_max

    texto = f"""
Diagnostico:
El principal foco de impacto se concentra en {actividad}, siendo {unidad} la unidad operativa critica. Sobre una base de {round(total, 1)} kg CO2e, este frente explica la mayor parte de la exposicion ambiental y operativa.

Insight estrategico:
{insight}

Nivel de viabilidad:
{viability}, la implementacion debe ser gradual, priorizada y progresiva para evitar fricciones operativas y mantener continuidad del negocio.

Recomendacion principal REALISTA:
Reducir consumo de {actividad} entre {realistic_min}% y {realistic_max}% en el corto/mediano plazo, iniciando con una fase priorizada alrededor de {realistic_reduction_pct}%, mediante medidas progresivas de eficiencia y sustitucion parcial.

Escenario optimo (potencial maximo):
{optimal_line} Este escenario se presenta unicamente como referencia estrategica de largo plazo, ya que implica cambios estructurales significativos, inversion relevante y una transicion operativa progresiva.

Escenario recomendado (realista):
En el corto plazo, la recomendacion implementable es una fase inicial de {realistic_reduction_pct}% sobre {actividad}, con foco en medidas de rapida adopcion, menor costo implicito y menor riesgo de continuidad operacional.

Niveles de accion:
{levels["low"]}
{levels["medium"]}
{levels["high"]}

Recomendacion estrategica:
Priorizar una hoja de ruta en dos velocidades: quick wins de eficiencia en 0-3 meses y decisiones estructurales en 3-18 meses para acercarse de forma creible al potencial maximo.

Siguiente accion concreta:
Ejecutar un piloto de 8-12 semanas en {unidad} sobre {actividad}, validar linea base y seguimiento semanal (consumo, emisiones y costo) antes de escalar la intervencion.
"""

    return texto.strip()
