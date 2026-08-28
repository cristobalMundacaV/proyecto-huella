from django.core.exceptions import ObjectDoesNotExist

from ..models import ActividadOperacional, Observacion


def environmental_activity_for_organization(organization, activity_id, work=None):
    rows = (
        ActividadOperacional.objects.filter(organizacion=organization, id=activity_id)
        .select_related("obra", "unidad_operacional", "proceso_operacional")
        .prefetch_related(
            "activos",
            "observaciones__fuente",
            "observaciones__evidencia",
            "observaciones__version_evidencia",
            "observaciones__registro_extraido",
        )
    )
    return rows.filter(obra=work) if work is not None else rows


def activity_environmental_record(activity):
    try:
        return activity.registro_flujo_ambiental
    except ObjectDoesNotExist:
        return None


def activity_provenance(activity):
    return [
        {
            "observation_id": row.id,
            "concept": row.concepto,
            "state": row.estado,
            "source_id": row.fuente_id,
            "actor_id": row.actor_id,
            "evidence_id": row.evidencia_id,
            "evidence_version_id": row.version_evidencia_id,
            "extracted_record_id": row.registro_extraido_id,
            "capture_method": row.metodo_captura,
            "nature": row.naturaleza,
        }
        for row in activity.observaciones.select_related(
            "fuente", "evidencia", "version_evidencia", "registro_extraido"
        ).order_by("timestamp_observacion", "id")
    ]


def usable_observation_count(activity):
    return activity.observaciones.exclude(estado=Observacion.Estado.RECHAZADA).count()
