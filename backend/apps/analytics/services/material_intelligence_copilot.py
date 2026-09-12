"""Material Intelligence Copilot (MI-01I): AI explains deterministic
MATERIAL-INTELLIGENCE findings without becoming an authority. Reuses the
existing ContextGateway (extended with `material_intelligence()`, not
duplicated) and the existing environmental-agent provider abstraction — no
second context gateway, no second provider contract. Every number the
response cites must come literally from the deterministic context; the
provider may never invent an alternative, infer suitability, change a
functional quantity, calculate GWP, or approve an equivalence/substitution.
Disabling this module entirely must not break any MI-01A..01H computation —
it is a read-only explanatory layer on top of them.
"""

from django.core.exceptions import ValidationError

from ..policies.intelligence import IntelligenceOperation, validate_ai_operation
from .context_gateway import ContextGateway

MATERIAL_COPILOT_RULES = """Eres un copiloto explicativo de MATERIAL-INTELLIGENCE.
Usa exclusivamente los hallazgos deterministas del contexto JSON entregado
(propiedades aprobadas, perfiles de aplicación, requisitos, evaluación de
idoneidad, uso funcional, hotspot).

Nunca:
- inventes una alternativa material ni una equivalencia funcional;
- infieras idoneidad o una propiedad no presente en el contexto;
- cambies o calcules una cantidad funcional, un factor o un GWP;
- apruebes una equivalencia, mapeo o sustitución;
- declares algo "aprobado para construcción", "mejor material" o
  "recomendado" — solo hallazgo, advertencia o explicación asistiva.

Todo numero que cites debe provenir literalmente del contexto entregado; si
no está en el contexto, indica explícitamente que se desconoce.

Responde solo JSON con las claves: hechos, hallazgos_deterministas,
advertencias, explicacion_asistiva. Cada una es una lista de strings, salvo
explicacion_asistiva que es un string."""

REQUIRED_FIELDS = {"hechos", "hallazgos_deterministas", "advertencias", "explicacion_asistiva"}


def _validate_payload(payload):
    if not isinstance(payload, dict) or not REQUIRED_FIELDS.issubset(payload):
        raise ValidationError("El proveedor no devolvió una explicación estructurada válida.")
    for field in ("hechos", "hallazgos_deterministas", "advertencias"):
        if not isinstance(payload[field], list):
            raise ValidationError({field: "Debe ser una lista."})
    if not isinstance(payload["explicacion_asistiva"], str):
        raise ValidationError({"explicacion_asistiva": "Debe ser texto."})


class MaterialIntelligenceCopilotService:
    def __init__(self, provider, gateway=None):
        self.provider = provider
        self.gateway = gateway or ContextGateway()

    def explain_material(self, material, organization, *, question="", work=None):
        validate_ai_operation(IntelligenceOperation.READ_CONTEXT)
        context = self.gateway.material_intelligence(material, organization, work=work)
        package = {"context": context, "user_question": (question or "")[:1000]}
        try:
            payload = self.provider.generate(system_rules=MATERIAL_COPILOT_RULES, context=package)
        except Exception as exc:
            raise ValidationError("El proveedor de IA no está disponible.") from exc
        _validate_payload(payload)
        return {
            "material_id": material.pk,
            "hechos": payload["hechos"],
            "hallazgos_deterministas": payload["hallazgos_deterministas"],
            "advertencias": payload["advertencias"],
            "explicacion_asistiva": payload["explicacion_asistiva"],
            "provenance": context["references"],
        }
