from openai import APIConnectionError, APIStatusError, OpenAI
from django.conf import settings


def get_client():
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no esta configurada en .env")

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def generar_analisis_ia(payload):
    prompt = f"""
Eres un consultor experto en sostenibilidad, huella de carbono y eficiencia operacional.

Analiza estos datos de una empresa:

Total emisiones: {payload.get("total_emisiones")}
Empresa critica: {payload.get("empresa_critica")}
Actividad critica: {payload.get("actividad_critica")}
Resultado de simulacion: {payload.get("simulacion")}
Resultado de optimizacion: {payload.get("optimizacion")}

Genera una respuesta ejecutiva en espanol con:
1. Diagnostico claro.
2. Riesgo principal.
3. Recomendacion estrategica.
4. Impacto esperado.
5. Siguiente accion concreta.

Se directo, profesional y convincente.
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
