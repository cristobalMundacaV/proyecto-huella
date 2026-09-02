from django.db import transaction

from ..models import FuenteDatos


CATALOG = {
    "energia": [
        ("Factura eléctrica", "documento"),
        ("Lectura manual de medidor eléctrico", "manual"),
        ("Medidor inteligente eléctrico", "sensor"),
        ("Sistema de distribuidora / plataforma energética", "sistema_externo"),
    ],
    "generacion_propia": [
        ("Medidor de generación", "sensor"),
        ("Reporte de inversor / generación", "documento"),
        ("Plataforma de generación", "sistema_externo"),
    ],
    "agua": [
        ("Factura sanitaria", "documento"),
        ("Lectura manual de medidor de agua", "manual"),
        ("Medidor de agua", "sensor"),
        ("Registro de abastecimiento externo", "documento"),
    ],
    "combustibles": [
        ("Vale de combustible", "documento"),
        ("Registro manual de abastecimiento", "manual"),
        ("Factura de combustible", "documento"),
        ("Telemetría de estanque", "telemetria"),
        ("ERP de combustibles", "erp"),
    ],
    "transporte": [
        ("Registro manual de viaje", "manual"),
        ("Guía de despacho / transporte", "documento"),
        ("GPS", "gps"),
        ("Telemetría vehicular", "telemetria"),
    ],
    "materiales": [
        ("Guía de despacho de materiales", "documento"),
        ("Registro de recepcion de materiales", "manual"),
        ("ERP / compras", "erp"),
    ],
    "residuos": [
        ("Ticket de pesaje", "documento"),
        ("Certificado / manifiesto de retiro", "documento"),
        ("Registro de retiro de residuos", "manual"),
        ("Sistema del gestor", "sistema_externo"),
    ],
    "ruido": [
        ("Medición con sonómetro", "manual"),
        ("Informe de medición de ruido", "documento"),
        ("Sensor de ruido", "sensor"),
    ],
    "emisiones-atmosfericas": [
        ("Medición instrumental", "manual"),
        ("Informe de muestreo / laboratorio", "documento"),
        ("Monitor o sensor ambiental", "sensor"),
    ],
}


@transaction.atomic
def ensure_construction_v1_sources(organization):
    created = 0
    for domain, rows in CATALOG.items():
        for name, source_type in rows:
            source, was_created = FuenteDatos.objects.get_or_create(
                organizacion=organization,
                nombre=name,
                defaults={
                    "tipo": source_type,
                    "metadata": {
                        "dominios": [domain],
                        "provisionada": True,
                        "catalogo": "construction_v1",
                    },
                },
            )
            if not was_created and not (source.metadata or {}).get("dominios"):
                source.metadata = {
                    **(source.metadata or {}),
                    "dominios": [domain],
                    "provisionada": True,
                    "catalogo": "construction_v1",
                }
                source.save(update_fields=["metadata", "updated_at"])
            created += int(was_created)
    return created
