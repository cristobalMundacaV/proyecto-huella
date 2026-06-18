CONSTRUCTION_REDUCTION_STEPS = [
    (
        "Optimizar materiales de alto impacto",
        "Revisar hormigon, cemento, acero, aridos y proveedores para priorizar alternativas con menor carbono incorporado.",
    ),
    (
        "Reducir transporte y consolidar viajes",
        "Agrupar despachos, evaluar proveedores cercanos y evitar kilometros recorridos sin carga util.",
    ),
    (
        "Mejorar uso de maquinaria",
        "Controlar ralenti, horas maquina, consumo por equipo y mantencion preventiva.",
    ),
    (
        "Reducir uso de generadores",
        "Planificar conexiones temporales a red y limitar generadores a usos operativos inevitables.",
    ),
    (
        "Controlar consumo energetico",
        "Medir kWh por etapa, ordenar horarios de uso y detectar consumos atipicos en faena.",
    ),
    (
        "Segregar y valorizar residuos",
        "Separar residuos valorizables, mejorar retiro trazable y reducir disposicion final.",
    ),
    (
        "Mejorar trazabilidad documental",
        "Vincular facturas, guias, boletas, tickets y fichas tecnicas a obras y registros de emision.",
    ),
    (
        "Medir kg CO2e/m2 por obra",
        "Comparar intensidad de carbono entre proyectos para detectar desviaciones y oportunidades de mejora.",
    ),
    (
        "Automatizar la captura operacional",
        "Usar sensores de combustible, energia, horas encendido, agua y GPS para transformar la obra en una fuente continua de datos ambientales.",
    ),
]


def _format_number_es(value, decimals=1):
    return f"{float(value or 0):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _steps_text():
    return "\n".join(f"- {title}: {detail}" for title, detail in CONSTRUCTION_REDUCTION_STEPS)


def _recommendation_for_category(categoria):
    recomendaciones = {
        "Materiales": "Revisar hormigon, cemento, acero, aridos y proveedores. La seleccion temprana de materiales suele ser la palanca mas fuerte sobre el carbono incorporado.",
        "Transporte": "Evaluar proveedores cercanos, consolidar viajes y reducir kilometros recorridos asociados a materiales, maquinaria y residuos.",
        "Maquinaria": "Controlar ralenti, planificar uso de equipos, medir litros u horas maquina y reforzar mantencion preventiva.",
        "Energia": "Reducir uso de generadores, medir consumo electrico y evaluar conexion temporal a red cuando sea viable.",
        "Agua": "Monitorear consumo por etapa y detectar desviaciones operativas antes de que se vuelvan recurrentes.",
        "Residuos": "Segregar residuos, mejorar trazabilidad de retiro y priorizar reciclaje o valorizacion.",
        "Procesos externos": "Revisar proveedores, subcontratos y procesos tercerizados con mayor impacto declarado.",
    }
    return recomendaciones.get(categoria, "Clasificar mejor los registros para separar materiales, transporte, maquinaria, energia, agua y residuos.")


def _viability_for(payload, categoria):
    total = float(payload.get("total_emisiones", 0) or 0)
    cobertura = payload.get("evidencia_respaldada")
    iot_count = int(payload.get("registros_iot") or 0)
    if total <= 0 and iot_count <= 0:
        return "Media"
    if iot_count >= 10:
        return "Alta"
    if categoria in {"Materiales", "Transporte", "Maquinaria"}:
        return "Media"
    if isinstance(cobertura, (int, float)) and cobertura >= 70:
        return "Alta"
    return "Media"


def generar_analisis_local(payload):
    total = float(payload.get("total_emisiones", 0) or payload.get("emisiones_totales", 0) or 0)
    categoria = payload.get("categoria_critica") or "Sin datos"
    fuente = payload.get("fuente_critica") or "Sin fuente critica"
    etapa = payload.get("etapa_critica") or "Sin etapa critica"
    intensidad = payload.get("intensidad_carbono")
    cobertura = payload.get("evidencia_respaldada")
    iot_count = int(payload.get("registros_iot") or 0)
    iot_emisiones = float(payload.get("emisiones_iot_kg_co2e") or 0)
    iot_por_tipo = payload.get("emisiones_iot_por_tipo") or {}
    top_dispositivos = payload.get("top_dispositivos_iot") or []
    dispositivo_critico = top_dispositivos[0]["dispositivo_id"] if top_dispositivos else "sin dispositivo critico"
    viabilidad = _viability_for(payload, categoria)
    recomendacion_categoria = _recommendation_for_category(categoria)

    intensidad_texto = (
        f"{_format_number_es(intensidad, 2)} kg CO2e/m2"
        if isinstance(intensidad, (int, float))
        else "pendiente de superficie declarada"
    )
    cobertura_texto = (
        f"{_format_number_es(cobertura, 1)}%"
        if isinstance(cobertura, (int, float))
        else "pendiente de vinculacion documental"
    )

    return f"""
Diagnostico:
La obra registra {_format_number_es(total, 1)} kg CO2e. La categoria critica es {categoria}, con foco principal en {fuente}. La etapa critica identificada es {etapa}. La intensidad actual es {intensidad_texto} y la cobertura documental esta {cobertura_texto}.

Lectura operacional IoT:
La ventana actual contiene {iot_count} registros de sensores y {_format_number_es(iot_emisiones, 1)} kg CO2e estimados por telemetria. El dispositivo con mayor impacto operativo es {dispositivo_critico}. Distribucion por tipo: {iot_por_tipo}.

Insight estrategico:
{recomendacion_categoria}

Riesgo operacional detectado:
Si los sensores muestran combustible, horas encendido o kWh concentrados en pocos equipos, la prioridad es detectar ralenti, uso fuera de horario, sobrerrecorridos o maquinaria con bajo rendimiento.

Nivel de viabilidad:
{viabilidad}. La reduccion debe abordarse con acciones progresivas, medibles y compatibles con la continuidad de obra.

Recomendacion principal realista:
Priorizar la categoria {categoria} durante el siguiente ciclo de control, cruzando emisiones, costos, proveedores, telemetria IoT y evidencias disponibles para seleccionar medidas de reduccion aplicables.

Escenario optimo:
Una obra con registros completos por categoria, evidencias vinculadas a fuentes criticas, intensidad kg CO2e/m2 monitoreada por etapa y sensores alimentando alertas operacionales en tiempo casi real.

Niveles de accion:
- Bajo esfuerzo: completar evidencias faltantes, ordenar registros por categoria y revisar consumos atipicos detectados por sensores.
- Medio impacto: ajustar proveedores, planificacion de viajes, uso de equipos, compras de materiales y horarios de consumo energetico.
- Transformacional: incorporar criterios de carbono y telemetria en contratos, planificacion de obra y control diario de operaciones.

Pasos a seguir:
{_steps_text()}

Recomendacion estrategica:
Usar Carbono Zero como tablero de control operativo continuo: medir, documentar, detectar desviaciones, comparar intensidad por obra y priorizar acciones sobre las fuentes con mayor kg CO2e.

Siguiente accion concreta:
Revisar los 5 registros con mayor emision y los 5 dispositivos IoT con mayor impacto, verificar si tienen evidencia asociada y definir una accion de reduccion por cada fuente critica.
""".strip()
