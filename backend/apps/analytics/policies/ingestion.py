import json

from ..models import (
    ActivoOperacional,
    AplicabilidadCapacidadObra,
    Obra,
    ProcesoIngesta,
    ProcesoOperacional,
    PuntoAmbientalOperacional,
    UnidadOperacional,
)
from ..permissions import filter_works_for_user


def parse_ingestion_context(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("El contexto debe ser un objeto JSON v�lido.") from exc
    if not isinstance(value, dict):
        raise ValueError("El contexto debe ser un objeto.")
    return value


def user_can_access_ingestion_context(user, organization, context):
    work_id = context.get("obra_id") if isinstance(context, dict) else None
    if not work_id:
        return True
    return (
        filter_works_for_user(Obra.objects.all(), user, organization)
        .filter(id=work_id)
        .exists()
    )


def validate_ingestion_contract(ingestion_type, destination):
    if ingestion_type not in ProcesoIngesta.TipoIngesta.values:
        raise ValueError("Tipo de ingesta no soportado.")
    if destination not in ProcesoIngesta.DestinoOperacional.values:
        raise ValueError("Destino operacional no soportado.")


def validate_structured_contract(ingestion_type, destination, payload):
    allowed = {
        ProcesoIngesta.TipoIngesta.MANUAL_ESTRUCTURADO,
        ProcesoIngesta.TipoIngesta.API,
        ProcesoIngesta.TipoIngesta.TELEMETRIA,
        ProcesoIngesta.TipoIngesta.SENSOR,
    }
    if ingestion_type not in allowed:
        raise ValueError("El contrato estructurado requiere un canal no documental.")
    if destination not in ProcesoIngesta.DestinoOperacional.values:
        raise ValueError("Destino operacional no soportado.")
    rows = payload if isinstance(payload, list) else [payload]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("El payload debe ser un objeto o lista de objetos.")
    return rows


def validate_process_context(process, context):
    if not isinstance(context, dict):
        raise ValueError("El contexto debe ser un objeto.")
    references = {
        "obra_id": Obra,
        "unidad_operacional_id": UnidadOperacional,
        "proceso_operacional_id": ProcesoOperacional,
        "activo_id": ActivoOperacional,
        "punto_id": PuntoAmbientalOperacional,
    }
    for field, model in references.items():
        if (
            context.get(field)
            and not model.objects.filter(
                organizacion=process.organizacion, id=context[field]
            ).exists()
        ):
            raise ValueError(f"La referencia {field} no pertenece a la organizaci�n.")
    scope = context.get("alcance", "organizacion")
    if scope not in {"organizacion", "obra", "dominio", "activo"}:
        raise ValueError("El alcance informado no es v�lido.")
    if scope in {"obra", "dominio", "activo"} and not context.get("obra_id"):
        raise ValueError("El alcance seleccionado requiere una obra.")
    if scope == "dominio":
        domain = context.get("dominio")
        if not domain:
            raise ValueError("El alcance ambiental requiere un dominio.")
        capability = (
            "gestion_hidrica_suelo"
            if domain in {"hidrica_suelo", "hidrica-suelo"}
            else domain
        )
        if not AplicabilidadCapacidadObra.objects.filter(
            obra_id=context["obra_id"],
            obra__organizacion=process.organizacion,
            capacidad__clave=capability,
            estado__in=["aplica", "sin_datos"],
        ).exists():
            raise ValueError(
                "El dominio no est� confirmado como aplicable para la obra."
            )
    if scope == "activo":
        raise ValueError(
            "El modelo actual no permite verificar que un activo pertenezca a una obra."
        )


def ensure_ingestion_mutable(process):
    if process.estado in {
        ProcesoIngesta.Estado.COMPLETADO,
        ProcesoIngesta.Estado.COMPLETADO_OBSERVACIONES,
    }:
        raise ValueError("Una ingesta confirmada es inmutable.")
