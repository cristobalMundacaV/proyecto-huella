from collections import defaultdict
import logging

from django.db import transaction

from ..models import FuenteDatos, Organizacion


logger = logging.getLogger(__name__)
CONSTRUCTION_SOURCE_CATALOG_VERSION = 1

# El nombre representa el origen real dentro del tenant. Una misma fuente puede
# alimentar varios dominios sin duplicarse.
SOURCE_CATALOG = (
    ("Factura eléctrica", "documento", ("energia",)),
    ("Lectura manual de medidor eléctrico", "manual", ("energia",)),
    ("Medidor inteligente eléctrico", "sensor", ("energia",)),
    ("Sistema de distribuidora / plataforma energética", "sistema_externo", ("energia",)),
    ("Medidor de generación", "sensor", ("generacion_propia",)),
    ("Reporte de inversor / generación", "documento", ("generacion_propia",)),
    ("Plataforma de generación", "sistema_externo", ("generacion_propia",)),
    ("Factura sanitaria", "documento", ("agua",)),
    ("Lectura manual de medidor de agua", "manual", ("agua",)),
    ("Medidor de agua", "sensor", ("agua",)),
    ("Registro de abastecimiento externo", "documento", ("agua",)),
    ("Registro de extracción propia", "manual", ("agua",)),
    ("Sistema / plataforma sanitaria", "sistema_externo", ("agua",)),
    ("Factura de combustible", "documento", ("combustibles",)),
    ("Vale de combustible", "documento", ("combustibles",)),
    ("Registro manual de abastecimiento", "manual", ("combustibles",)),
    ("Tarjeta de combustible", "sistema_externo", ("combustibles",)),
    ("ERP de combustibles", "erp", ("combustibles",)),
    ("Telemetría de estanque", "telemetria", ("combustibles",)),
    ("Registro manual de viaje", "manual", ("transporte",)),
    ("GPS", "gps", ("transporte",)),
    ("Hoja / ficha de ruta", "documento", ("transporte",)),
    ("Guía de despacho / transporte", "documento", ("transporte",)),
    ("Odómetro / kilometraje", "manual", ("transporte",)),
    ("Telemetría vehicular", "telemetria", ("transporte",)),
    ("Horómetro", "manual", ("maquinaria",)),
    ("Parte diario de maquinaria", "documento", ("maquinaria",)),
    ("Registro de combustible", "manual", ("combustibles", "maquinaria")),
    ("Telemetría de maquinaria", "telemetria", ("maquinaria",)),
    ("Registro de mantenimiento", "documento", ("maquinaria",)),
    ("Orden de compra", "documento", ("materiales",)),
    ("Factura de materiales", "documento", ("materiales",)),
    ("Guía de despacho de materiales", "documento", ("materiales",)),
    ("Registro de recepcion de materiales", "manual", ("materiales",)),
    ("ERP / compras", "erp", ("materiales",)),
    ("Ficha técnica / EPD / certificación del proveedor", "documento", ("materiales",)),
    ("Ticket de pesaje", "documento", ("residuos",)),
    ("Certificado / manifiesto de retiro", "documento", ("residuos",)),
    ("Certificado de disposición final", "documento", ("residuos",)),
    ("Registro de retiro de residuos", "manual", ("residuos",)),
    ("Reporte del gestor / relleno autorizado", "documento", ("residuos",)),
    ("Sistema del gestor", "sistema_externo", ("residuos",)),
    ("Medición con sonómetro", "manual", ("ruido",)),
    ("Informe de medición de ruido", "documento", ("ruido",)),
    ("Sensor de ruido", "sensor", ("ruido",)),
    ("Medición instrumental", "manual", ("emisiones-atmosfericas",)),
    ("Informe de muestreo / laboratorio", "documento", ("emisiones-atmosfericas",)),
    ("Monitor o sensor ambiental", "sensor", ("emisiones-atmosfericas",)),
    (
        "Registro de mantenimiento / revisión técnica",
        "documento",
        ("emisiones-atmosfericas",),
    ),
)

# Contrato de compatibilidad para consumidores y tests que recorren por dominio.
CATALOG = defaultdict(list)
for _name, _source_type, _domains in SOURCE_CATALOG:
    for _domain in _domains:
        CATALOG[_domain].append((_name, _source_type))
CATALOG = dict(CATALOG)


@transaction.atomic
def ensure_construction_v1_sources(organization):
    organization = Organizacion.objects.select_for_update().get(pk=organization.pk)
    created = 0
    for name, source_type, domains in SOURCE_CATALOG:
        source, was_created = FuenteDatos.objects.get_or_create(
            organizacion=organization,
            nombre=name,
            defaults={
                "tipo": source_type,
                "metadata": {
                    "dominios": list(domains),
                    "provisionada": True,
                    "catalogo": "construction_v1",
                    "catalogo_version": CONSTRUCTION_SOURCE_CATALOG_VERSION,
                },
            },
        )
        created += int(was_created)
        if was_created:
            continue

        metadata = source.metadata or {}
        if not (
            metadata.get("provisionada") is True
            and metadata.get("catalogo") == "construction_v1"
        ):
            # Una coincidencia de nombre custom no se adopta ni reclasifica.
            logger.warning(
                "Fuente custom '%s' coincide con una fuente Construction V1 en "
                "organizacion %s; se preservo sin reclasificar.",
                name,
                organization.organizacion_id,
            )
            continue
        merged_domains = sorted(set(metadata.get("dominios", [])) | set(domains))
        expected_metadata = {
            **metadata,
            "dominios": merged_domains,
            "provisionada": True,
            "catalogo": "construction_v1",
            "catalogo_version": CONSTRUCTION_SOURCE_CATALOG_VERSION,
        }
        if source.metadata != expected_metadata:
            source.metadata = expected_metadata
            source.save(update_fields=["metadata", "updated_at"])
    return created


@transaction.atomic
def ensure_existing_construction_v1_sources():
    created = 0
    organizations = Organizacion.objects.filter(
        preset=Organizacion.Preset.CONSTRUCCION
    ).order_by("pk")
    for organization in organizations:
        created += ensure_construction_v1_sources(organization)
    return created
