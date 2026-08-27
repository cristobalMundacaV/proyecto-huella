from django.db.models import Q

from ..models import FuenteDatos, PlantillaMapeo, ProcesoIngesta
from ..permissions import filter_works_for_user
from ..models import Obra, Organizacion


def organization_by_public_id(organization_id):
    return Organizacion.objects.filter(organizacion_id=organization_id)


def ingestion_process_for_organization(organization, ingestion_id):
    return ProcesoIngesta.objects.select_related(
        "version_evidencia__evidencia", "fuente_datos", "plantilla_mapeo"
    ).filter(organizacion=organization, id=ingestion_id)


def ingestion_processes_for_user(organization, user):
    allowed_ids = list(
        filter_works_for_user(Obra.objects.all(), user, organization).values_list(
            "id", flat=True
        )
    )
    return organization.procesos_ingesta.select_related(
        "version_evidencia__evidencia", "fuente_datos", "plantilla_mapeo"
    ).filter(
        Q(contexto_confirmado__obra_id__isnull=True)
        | Q(contexto_confirmado__obra_id__in=allowed_ids)
    )


def mapping_templates_for_organization(organization):
    return (
        PlantillaMapeo.objects.filter(organizacion=organization)
        .select_related("fuente_datos")
        .prefetch_related("mapeos")
    )


def source_for_organization(organization, source_id):
    if not source_id:
        return None
    return FuenteDatos.objects.filter(organizacion=organization, id=source_id).first()


def source_by_name(organization, name):
    return FuenteDatos.objects.filter(organizacion=organization, nombre=name).first()


def active_template_for_process(process):
    return PlantillaMapeo.objects.filter(
        organizacion=process.organizacion,
        fuente_datos=process.fuente_datos,
        activa=True,
        tipo_ingesta=process.tipo_ingesta,
        destino_operacional=process.destino_operacional,
        flujo=process.flujo,
    ).first()


def next_template_version(process, name):
    latest = (
        PlantillaMapeo.objects.filter(
            organizacion=process.organizacion,
            fuente_datos=process.fuente_datos,
            nombre=name,
        )
        .order_by("-version")
        .values_list("version", flat=True)
        .first()
    )
    return (latest or 0) + 1


def extracted_records_for_process(process):
    return process.registros_extraidos.all()


def extracted_records_for_update(process):
    return process.registros_extraidos.select_for_update()


def process_has_processed_records(process):
    return process.registros_extraidos.filter(estado="procesado").exists()


def column_mappings_for_template(template):
    return template.mapeos.all()
