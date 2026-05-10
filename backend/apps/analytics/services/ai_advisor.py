from openai import APIConnectionError, APIStatusError, OpenAI
from django.conf import settings


def get_client():
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no esta configurada en .env")

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def generar_analisis_ia(payload):
    optimizacion = payload.get("optimizacion") or {}
    actividad = payload.get("actividad_critica") or "actividad critica"
    actividad_normalizada = str(actividad).lower()
    max_reduction_pct = optimizacion.get("reductionPct")

    if actividad_normalizada == "diesel":
        optimal_reduction_pct = optimizacion.get("dieselReduction")
    elif actividad_normalizada == "electricidad":
        optimal_reduction_pct = optimizacion.get("electricityReduction")
    else:
        optimal_reduction_pct = optimizacion.get("activityReduction")

    prompt = f"""
Actua como un consultor experto en sostenibilidad y eficiencia operativa empresarial.

Tu objetivo NO es maximizar la reduccion teorica de emisiones, sino generar recomendaciones REALISTAS, IMPLEMENTABLES y alineadas con la operacion actual de la empresa.

Contexto:
- Emisiones totales: {payload.get("total_emisiones")} kg CO2e
- Actividad critica: {payload.get("actividad_critica")}
- Unidad operativa critica: {payload.get("unidad_critica") or payload.get("empresa_critica")}
- Reduccion potencial maxima estimada: {max_reduction_pct}%
- Escenario optimo detectado: reducir {actividad} en {optimal_reduction_pct}%

Reglas clave:
1) Diferencia explicitamente entre:
    - Escenario optimo teorico (maximo potencial, aunque no sea viable)
    - Escenario recomendado (realista y aplicable en el corto/mediano plazo)

2) NUNCA recomiendes reducciones extremas (70%-90%) como accion directa si implican detener operaciones, reemplazo completo sin transicion o inversiones no razonables en el corto plazo.

3) Evalua viabilidad considerando dependencia operativa de la actividad, facilidad de sustitucion tecnologica, costo implicito y tiempo de implementacion.

4) Genera SIEMPRE 3 niveles de accion:
    - 🟢 Bajo esfuerzo (quick wins, 5%-15% reduccion)
    - 🟡 Medio impacto (15%-35% reduccion, requiere ajustes operativos)
    - 🔴 Transformacional (35%+ reduccion, requiere cambios estructurales)

5) Si el escenario optimo supera el 50% de reduccion, tratalo SOLO como referencia estrategica y NO como recomendacion directa.

6) Reformula recomendaciones absolutas en estrategias progresivas.
    Ejemplo:
    - NO usar: "Reducir diesel 80%"
    - SI usar: "Reducir consumo de diesel entre 10%-25% mediante optimizacion de rutas, mantenimiento y transicion parcial a alternativas"

7) El lenguaje debe reflejar realismo: usar terminos como gradual, progresivo, faseado y priorizado. Evitar absolutos como eliminar, reemplazar completamente o reducir al maximo.

Base de conocimiento para empresas madereras:
- Optimizar rutas de despacho y transporte: menos kilometros vacios, mejores rutas, camiones mejor cargados y menos viajes innecesarios.
- Mejorar la eficiencia de maquinaria y camiones: mantencion preventiva, neumaticos correctos, motores calibrados y evitar ralenti excesivo.
- Controlar conduccion y operacion: capacitar operadores para reducir aceleraciones bruscas, tiempos muertos y uso ineficiente de equipos.
- Renovar flota gradualmente: cambiar camiones o maquinaria antigua por modelos mas eficientes, sin hacerlo todo de golpe.
- Usar combustibles de menor emision cuando sea viable: biodiesel, diesel renovable u otras mezclas compatibles segun disponibilidad y costo.
- Electrificar operaciones internas especificas: priorizar gruas, equipos de patio, montacargas o vehiculos livianos cuando el transporte forestal pesado no sea electrificable todavia.
- Planificar mejor la cosecha y acopio: acercar puntos de acopio, reducir movimientos internos y evitar traslados repetidos de la misma carga.
- Medir litros por actividad: separar consumo por cosecha, despacho, transporte, maquinaria y vehiculos.

Idea clave que debes transmitir cuando aplique:
Aunque el combustible sea inevitable en la operacion maderera, las emisiones si pueden reducirse mediante eficiencia operacional, optimizacion logistica, mantencion, renovacion tecnologica y combustibles alternativos.

Estructura obligatoria de salida:
Diagnostico:
Insight estrategico:
Nivel de viabilidad (Alta/Media/Baja):
Recomendacion principal REALISTA:
Escenario optimo (referencia no inmediata):
Niveles de accion:
Pasos a seguir:
Recomendacion estrategica:
Siguiente accion concreta:

Tono: profesional, claro, ejecutivo, sin exageraciones ni promesas irreales.

Devuelve solo el texto final en espanol, sin markdown.
"""

    try:
        response = get_client().responses.create(
            model="gpt-5-mini",
            input=prompt,
        )
    except APIConnectionError as exc:
        raise ValueError(
            "No se pudo conectar con OpenAI. Revisa tu conexion o intenta nuevamente."
        ) from exc
    except APIStatusError as exc:
        error_code = getattr(exc, "code", None)

        if exc.status_code == 429 or error_code == "insufficient_quota":
            raise ValueError(
                "La API key de OpenAI no tiene cuota disponible. Revisa el plan, billing o creditos de la cuenta."
            ) from exc

        raise ValueError(f"OpenAI rechazo la solicitud: {exc.message}") from exc

    return response.output_text
