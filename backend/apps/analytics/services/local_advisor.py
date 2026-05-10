from .activity_semantics import is_diesel_activity, is_electricity_activity


def _pick_realistic_initial_reduction(max_reduction_pct):
    if max_reduction_pct <= 0:
        return 20
    if max_reduction_pct <= 30:
        return 20
    return min(35, max(15, round(max_reduction_pct * 0.4)))


def _activity_row(actividad):
    return {"actividad": actividad, "actividad_key": actividad}


def _format_number_es(value, decimals=1):
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _describe_activity(actividad):
    if is_diesel_activity(_activity_row(actividad)):
        return "el diésel asociado a combustión móvil"
    return actividad


def _with_preposition_de(label):
    return f"del {label[3:]}" if str(label).startswith("el ") else f"de {label}"


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
    activity_label = _describe_activity(actividad)
    activity_with_de = _with_preposition_de(activity_label)

    return {
        "low": (
            "🟢 Bajo esfuerzo: 5% - 15% de reducción\n"
            f"Ajustes operativos en el uso {activity_with_de}, mejor control del consumo, "
            "mantenimiento preventivo y seguimiento semanal de indicadores."
        ),
        "medium": (
            "🟡 Impacto medio: 15% - 35% de reducción\n"
            f"Optimización gradual del uso {activity_with_de} mediante cambios en procesos, "
            "análisis de desempeño y sustitución parcial de tecnología."
        ),
        "high": (
            "🔴 Transformacional: más de 35% de reducción\n"
            f"Rediseño estructural del uso {activity_with_de}, inversión dedicada, "
            "renovación tecnológica y planificación a mediano y largo plazo."
        ),
    }


WOOD_INDUSTRY_REDUCTION_STEPS = [
    (
        "Optimizar rutas de despacho y transporte",
        "Reducir kilómetros recorridos en vacío, mejorar rutas, cargar mejor los camiones y evitar viajes innecesarios.",
    ),
    (
        "Mejorar la eficiencia de maquinaria y camiones",
        "Aplicar mantención preventiva, controlar la presión de los neumáticos, calibrar motores y reducir el ralentí excesivo.",
    ),
    (
        "Controlar conduccion y operacion",
        "Capacitar a operadores para disminuir aceleraciones bruscas, tiempos muertos y uso ineficiente de equipos.",
    ),
    (
        "Renovar flota gradualmente",
        "Reemplazar camiones o maquinaria antigua por modelos más eficientes, sin exigir un cambio completo de una sola vez.",
    ),
    (
        "Usar combustibles de menor emision cuando sea viable",
        "Evaluar biodiésel, diésel renovable u otras mezclas compatibles según disponibilidad, costo y garantía técnica.",
    ),
    (
        "Electrificar operaciones internas especificas",
        "Priorizar grúas, equipos de patio, montacargas o vehículos livianos antes que el transporte forestal pesado.",
    ),
    (
        "Planificar mejor la cosecha y acopio",
        "Acercar puntos de acopio, reducir movimientos internos y evitar traslados repetidos de la misma carga.",
    ),
    (
        "Medir litros por actividad",
        "Separar el consumo por cosecha, despacho, transporte, maquinaria y vehículos para identificar dónde actuar primero.",
    ),
]


WOOD_INDUSTRY_KEY_IDEA = (
    "Aunque el uso de combustible sea inevitable en una operación maderera, las emisiones "
    "sí pueden reducirse mediante eficiencia operacional, optimización logística, "
    "mantención preventiva, renovación tecnológica y combustibles alternativos."
)


def _wood_industry_steps_text():
    lines = []

    for title, detail in WOOD_INDUSTRY_REDUCTION_STEPS:
        lines.append(f"- {title}: {detail}")

    return "\n".join(lines)


def generar_analisis_local(payload):
    total = float(payload.get("total_emisiones", 0) or 0)
    unidad = payload.get("unidad_critica") or payload.get("empresa_critica") or "la unidad critica"
    actividad = payload.get("actividad_critica", "la actividad critica")
    actividad_row = _activity_row(actividad)
    activity_label = _describe_activity(actividad)
    optimizacion = payload.get("optimizacion") or {}

    max_reduction_pct = float(optimizacion.get("reductionPct", 0) or 0)
    if max_reduction_pct <= 0 and is_diesel_activity(actividad_row) and total > 0:
        max_reduction_pct = 25.0

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
            "La alta dependencia del diésel concentra riesgos operativos, de costos y de cumplimiento ambiental. "
            "Por esta razón, las acciones sobre este frente serán determinantes para el resultado global de descarbonización."
        )
    elif is_diesel_activity(actividad_row):
        insight = (
            "El diésel sigue siendo la principal causa de impacto y conviene intervenirlo "
            "antes de distribuir esfuerzos en múltiples frentes menores."
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
        f"bajo una intervención profunda en el uso {_with_preposition_de(activity_label)}."
        if is_diesel_activity(actividad_row)
        else f"bajo una intervención profunda sobre {actividad}."
    )

    optimal_line = (
        f"El escenario máximo identifica una reducción agregada cercana al {_format_number_es(max_reduction_pct, 1)}% "
        f"de las emisiones totales, {intervention_line}"
    )

    if realistic_reduction_pct < realistic_min:
        realistic_reduction_pct = realistic_min
    if realistic_reduction_pct > realistic_max:
        realistic_reduction_pct = realistic_max

    texto = f"""
Diagnóstico:
El principal foco de impacto se concentra en {activity_label}, siendo {unidad} la unidad operativa crítica. Sobre una base de {_format_number_es(total, 1)} kg CO₂e, este frente representa la mayor exposición ambiental y operativa.

Insight estratégico:
{insight}

Nivel de viabilidad:
{viability}. La implementación debe realizarse de forma gradual, priorizada y progresiva, para evitar impactos negativos en la operación y mantener la continuidad del negocio.

Recomendación principal realista:
Reducir el consumo {_with_preposition_de(activity_label)} entre un {realistic_min}% y un {realistic_max}% en el corto y mediano plazo, iniciando con una fase priorizada cercana al {realistic_reduction_pct}%. Esto debe lograrse mediante medidas progresivas de eficiencia operacional y sustitución parcial de equipos o tecnologías.

Escenario óptimo: potencial máximo
{optimal_line} Este escenario se presenta solo como una referencia estratégica de largo plazo, ya que implica cambios estructurales importantes, inversión relevante y una transición operativa progresiva.

Escenario recomendado: realista
En el corto plazo, la recomendación implementable es iniciar con una fase de reducción del {realistic_reduction_pct}% sobre el consumo {_with_preposition_de(activity_label)}. Esta fase debe enfocarse en medidas de rápida adopción, menor costo inicial y bajo riesgo para la continuidad operacional.

Niveles de acción:
{levels["low"]}
{levels["medium"]}
{levels["high"]}

Pasos a seguir para reducir emisiones en una operacion maderera:
{_wood_industry_steps_text()}

Idea clave:
{WOOD_INDUSTRY_KEY_IDEA}

Recomendación estratégica:
Priorizar una hoja de ruta en dos etapas: primero, aplicar mejoras rápidas de eficiencia durante los primeros 0 a 3 meses; luego, avanzar en decisiones estructurales entre los 3 y 18 meses, para acercarse de manera realista al potencial máximo de reducción.

Siguiente acción concreta:
Ejecutar un piloto de 8 a 12 semanas en la unidad de {unidad}, enfocado en {activity_label}. Durante este periodo se debe validar la línea base y realizar seguimiento semanal de consumo, emisiones y costos antes de escalar la intervención.
"""

    return texto.strip()
