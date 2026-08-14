import json

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import (HitoDecisionIA, MemoriaOrganizacion,
                      RecomendacionAgenteAmbiental, RestriccionContextual)
from .context_gateway import ContextGateway
from .environmental_agent import SYSTEM_RULES
from .environmental_agent import OpenAIEnvironmentalProvider


PROPOSAL_FIELDS = {"titulo", "descripcion", "justificacion", "kpis_afectados", "requisitos", "riesgos", "prioridad"}
COPILOT_RULES = SYSTEM_RULES + """
Prepara una propuesta, nunca ejecutes acciones ni calcules valores. Devuelve JSON con titulo, descripcion,
justificacion, kpis_afectados, requisitos, riesgos y prioridad. Considera restricciones entregadas."""


class CopilotProposalService:
    def __init__(self, provider, gateway=None):
        self.provider = provider
        self.gateway = gateway or ContextGateway()

    @transaction.atomic
    def propose(self, problem, message="", user=None, previous=None, context_categories=None):
        context = self.gateway.problem(problem, problem.organizacion)
        additional = {}
        for category in context_categories or []:
            if category == "organization_memory":
                additional[category] = self.gateway.organization_memory(problem.organizacion)
            elif category == "intervention":
                additional[category] = self.gateway.intervention(problem, problem.organizacion)
            else:
                raise ValidationError({"referencias_contextuales": f"Categoria no permitida: {category}."})
        package = {"context": context, "additional_context": additional, "user_message": message[:1000], "previous_proposal": previous.id if previous else None}
        HitoDecisionIA.objects.create(organizacion=problem.organizacion, problematica=problem, propuesta=previous, tipo="contexto_consultado", resumen="Contexto minimo preparado por ContextGateway.", referencias_contexto=["problem", *additional.keys()], usuario=user)
        payload = self.provider.generate(system_rules=COPILOT_RULES, context=package)
        self._validate(payload, problem)
        restrictions = context["restricciones"]
        proposal = RecomendacionAgenteAmbiental.objects.create(
            problematica=problem, titulo=payload["titulo"], descripcion=payload["descripcion"],
            accion=payload["titulo"], justificacion=payload["justificacion"],
            indicador_afectado=(payload["kpis_afectados"] or [problem.indicador])[0],
            resultado_esperado="Propuesta sujeta a confirmacion humana y evaluacion posterior.",
            prioridad=payload["prioridad"], periodo_seguimiento=payload.get("periodo_seguimiento", "por definir"),
            nivel_confianza=payload.get("nivel_confianza", "media"), diagnostico={"hechos": [], "correlaciones": [], "hipotesis": []},
            requisitos=payload["requisitos"], riesgos=payload["riesgos"], kpis_afectados=payload["kpis_afectados"],
            restricciones_consideradas=[item["id"] for item in restrictions], referencias_contexto=["problem", *additional.keys()],
            estado="ajustada" if previous else "propuesta", version=(previous.version + 1) if previous else 1,
            propuesta_anterior=previous, mensaje_usuario=message, proveedor=self.provider.name, modelo=self.provider.model,
            contexto_resumen={"context_chars": len(json.dumps(package, default=str)), "categorias": ["problem", *additional.keys()]},
        )
        HitoDecisionIA.objects.create(organizacion=problem.organizacion, problematica=problem, propuesta=proposal, tipo="adaptacion" if previous else "propuesta", resumen=payload["justificacion"][:500], referencias_contexto=proposal.referencias_contexto, payload_auditable={"titulo": proposal.titulo, "prioridad": proposal.prioridad}, usuario=user)
        return proposal

    def refute(self, proposal, message, user=None):
        if not message.strip():
            raise ValidationError("La refutacion no puede estar vacia.")
        restriction = RestriccionContextual.objects.create(
            organizacion=proposal.problematica.organizacion, problematica=proposal.problematica,
            tipo="refutacion_usuario", descripcion=message.strip(), contenido={"propuesta_origen": proposal.id}, created_by=user,
        )
        MemoriaOrganizacion.objects.create(
            organizacion=proposal.problematica.organizacion, problematica=proposal.problematica,
            tipo="restriccion_operacional", contenido={"descripcion": message.strip(), "restriccion": restriction.id}, fuente_origen="feedback_usuario",
        )
        proposal.estado = "rechazada"; proposal.save(update_fields=["estado"])
        HitoDecisionIA.objects.create(organizacion=proposal.problematica.organizacion, problematica=proposal.problematica, propuesta=proposal, tipo="refutacion", resumen=message[:500], referencias_contexto=["restriction", restriction.id], usuario=user)
        adjusted = self.propose(proposal.problematica, message=message, user=user, previous=proposal)
        return restriction, adjusted

    @staticmethod
    def _validate(payload, problem):
        if not isinstance(payload, dict) or not PROPOSAL_FIELDS.issubset(payload):
            raise ValidationError("El proveedor no devolvio una propuesta estructurada valida.")
        if payload["prioridad"] not in RecomendacionAgenteAmbiental.Prioridad.values:
            raise ValidationError({"prioridad": "Valor invalido."})
        if not isinstance(payload["kpis_afectados"], list) or not isinstance(payload["requisitos"], list) or not isinstance(payload["riesgos"], list):
            raise ValidationError("KPIs, requisitos y riesgos deben ser listas.")
        allowed = set(problem.indicadores_v2.values_list("indicador__codigo", flat=True)) or {problem.indicador}
        if not set(payload["kpis_afectados"]).issubset(allowed):
            raise ValidationError("La propuesta referencia KPIs no asociados a la problematica.")


def default_copilot_service():
    return CopilotProposalService(OpenAIEnvironmentalProvider())
