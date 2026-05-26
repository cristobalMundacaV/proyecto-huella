from django.conf import settings
from openai import APIConnectionError, APIStatusError, OpenAI


def get_client():
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no esta configurada en .env")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def generar_analisis_ia(payload):
    prompt = f"""
Actua como consultor senior de sostenibilidad y eficiencia operacional para obras de construccion.

Debes entregar recomendaciones realistas para reducir emisiones durante la ejecucion de la obra. Considera materiales, transporte, maquinaria, energia, agua, residuos, evidencias documentales, intensidad kg CO2e/m2, categoria critica, etapa critica, fuente critica y viabilidad de reduccion.

Contexto de Carbono Zero:
- Emisiones totales: {payload.get("total_emisiones") or payload.get("emisiones_totales")} kg CO2e
- Obra critica: {payload.get("obra_critica")}
- Categoria critica: {payload.get("categoria_critica")}
- Fuente critica: {payload.get("fuente_critica")}
- Etapa critica: {payload.get("etapa_critica")}
- Intensidad de carbono: {payload.get("intensidad_carbono") or "pendiente"} kg CO2e/m2
- Evidencia respaldada: {payload.get("evidencia_respaldada") or "pendiente de vinculacion documental"}

Reglas:
1) Si Materiales es critico, recomienda revisar hormigon, cemento, acero, aridos y proveedores.
2) Si Transporte es critico, recomienda proveedores cercanos, consolidacion de viajes y reduccion de kilometros.
3) Si Maquinaria es critica, recomienda controlar ralenti, mantencion y planificacion de equipos.
4) Si Energia es critica, recomienda reducir generadores y optimizar consumo electrico.
5) Si Residuos es critico, recomienda segregacion, reciclaje y valorizacion.
6) Si la trazabilidad documental es baja, recomienda subir y vincular evidencias faltantes.
7) No prometas reducciones absolutas ni certificaciones oficiales. Diferencia escenario optimo de recomendacion realista.
8) Mantén tono ejecutivo, claro y aplicable.

Estructura obligatoria de salida:
Diagnostico:
Insight estrategico:
Nivel de viabilidad:
Recomendacion principal realista:
Escenario optimo:
Niveles de accion:
Pasos a seguir:
Recomendacion estrategica:
Siguiente accion concreta:

Devuelve solo el texto final en espanol, sin markdown.
"""

    try:
        response = get_client().responses.create(
            model="gpt-5-mini",
            input=prompt,
        )
    except APIConnectionError as exc:
        raise ValueError("No se pudo conectar con OpenAI. Revisa tu conexion o intenta nuevamente.") from exc
    except APIStatusError as exc:
        error_code = getattr(exc, "code", None)
        if exc.status_code == 429 or error_code == "insufficient_quota":
            raise ValueError("La API key de OpenAI no tiene cuota disponible.") from exc
        raise ValueError(f"OpenAI rechazo la solicitud: {exc.message}") from exc

    return response.output_text
