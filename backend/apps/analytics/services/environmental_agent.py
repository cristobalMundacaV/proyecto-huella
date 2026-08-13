import json
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.analytics.models import RecomendacionAgenteAmbiental
from apps.analytics.services.environmental_context import minimal_agent_context


REQUIRED_FIELDS = {
    "accion", "justificacion", "indicador_afectado", "resultado_esperado",
    "prioridad", "periodo_seguimiento", "nivel_confianza",
}

SYSTEM_RULES = """Eres un agente ambiental. Usa exclusivamente el contexto JSON entregado.
No inventes mediciones, normativa ni factores. No hagas calculos deterministas: cita los resultados del backend.
Diferencia hechos, correlaciones e hipotesis y no afirmes causalidad sin evidencia.
No declares una accion efectiva sin medicion posterior ni cumplimiento legal sin una regla validada.
Devuelve solo JSON con: diagnostico (hechos, correlaciones, hipotesis), accion, justificacion,
indicador_afectado, resultado_esperado, prioridad, periodo_seguimiento y nivel_confianza.
Prioridad: baja|media|alta|critica. Confianza: baja|media|alta."""


class EnvironmentalAgentProvider:
    name = "abstract"
    model = ""

    def generate(self, *, system_rules, context):
        raise NotImplementedError


class OpenAIEnvironmentalProvider(EnvironmentalAgentProvider):
    name = "openai"
    model = "gpt-5-mini"

    def __init__(self, client=None):
        if client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("No hay proveedor LLM configurado.")
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.client = client

    def generate(self, *, system_rules, context):
        response = self.client.responses.create(
            model=self.model,
            input=[{"role": "system", "content": system_rules}, {"role": "user", "content": json.dumps(context, default=str, ensure_ascii=False)}],
        )
        return json.loads(response.output_text)


@dataclass
class AgentResult:
    recommendation: RecomendacionAgenteAmbiental
    context_chars: int


class EnvironmentalAgentService:
    def __init__(self, provider):
        self.provider = provider

    def recommend(self, problem):
        if problem.requiere_evaluacion_profesional or problem.estado == "escalada":
            raise ValidationError("La problematica fue escalada y no admite nuevas recomendaciones automaticas.")
        context = minimal_agent_context(problem)
        payload = self.provider.generate(system_rules=SYSTEM_RULES, context=context)
        self._validate(payload, problem, context)
        recommendation = RecomendacionAgenteAmbiental.objects.create(
            problematica=problem,
            accion=payload["accion"], justificacion=payload["justificacion"],
            indicador_afectado=payload["indicador_afectado"], resultado_esperado=payload["resultado_esperado"],
            prioridad=payload["prioridad"], periodo_seguimiento=payload["periodo_seguimiento"],
            nivel_confianza=payload["nivel_confianza"], diagnostico=payload.get("diagnostico", {}),
            contexto_resumen={
                "context_chars": len(json.dumps(context, default=str, ensure_ascii=False)),
                "fuentes_total": context["fuentes"]["total_registros"],
                "historial_total": context["historial_reciente"]["total"],
                "evidencias_total": context["evidencias"]["totales"],
                "reglas_normativas": len(context["normativa"]["reglas_validadas"]),
            },
            proveedor=self.provider.name, modelo=self.provider.model,
        )
        return AgentResult(recommendation, recommendation.contexto_resumen["context_chars"])

    @staticmethod
    def _validate(payload, problem, context):
        if not isinstance(payload, dict) or not REQUIRED_FIELDS.issubset(payload):
            raise ValidationError("El proveedor no devolvio una recomendacion estructurada completa.")
        if payload["prioridad"] not in RecomendacionAgenteAmbiental.Prioridad.values:
            raise ValidationError({"prioridad": "Valor invalido."})
        if payload["nivel_confianza"] not in RecomendacionAgenteAmbiental.Confianza.values:
            raise ValidationError({"nivel_confianza": "Valor invalido."})
        if payload["indicador_afectado"] != problem.indicador:
            raise ValidationError({"indicador_afectado": "Debe corresponder al indicador procesado de la problematica."})
        diagnosis = payload.get("diagnostico", {})
        if not isinstance(diagnosis, dict) or set(diagnosis) != {"hechos", "correlaciones", "hipotesis"}:
            raise ValidationError({"diagnostico": "Debe diferenciar hechos, correlaciones e hipotesis."})
        rendered = " ".join(str(payload.get(field, "")) for field in REQUIRED_FIELDS).lower()
        if ("cumplimiento legal" in rendered or "cumple la normativa" in rendered) and not context["normativa"]["reglas_validadas"]:
            raise ValidationError("No se puede afirmar cumplimiento legal sin una regla validada.")
        if ("accion efectiva" in rendered or "la accion es efectiva" in rendered) and problem.valor_posterior is None:
            raise ValidationError("No se puede declarar una accion efectiva sin medicion posterior.")


def default_agent_service():
    return EnvironmentalAgentService(OpenAIEnvironmentalProvider())
