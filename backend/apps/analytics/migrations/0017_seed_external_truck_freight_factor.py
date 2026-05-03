from decimal import Decimal

from django.db import migrations


def seed_external_truck_freight_factor(apps, schema_editor):
    FactorEmision = apps.get_model("analytics", "FactorEmision")
    FactorEmision.objects.update_or_create(
        actividad_key="camion_diesel_rigido_promedio",
        unidad="t-km",
        fuente="DEFRA",
        anio=2025,
        defaults={
            "categoria": "Transporte",
            "actividad": "Camión diésel rígido promedio",
            "factor_emision": Decimal("0.1782"),
            "descripcion": (
                "Transporte externo de carga por camión diésel rígido promedio. "
                "Usar cantidad = toneladas transportadas x kilómetros."
            ),
            "metadata_clasificacion": {
                "uso": "emisiones = toneladas_transportadas * kilometros * 0.1782",
                "ejemplo": "20 toneladas * 100 km * 0.1782 = 356.4 kgCO2e",
            },
        },
    )


def remove_external_truck_freight_factor(apps, schema_editor):
    FactorEmision = apps.get_model("analytics", "FactorEmision")
    FactorEmision.objects.filter(
        actividad_key="camion_diesel_rigido_promedio",
        unidad="t-km",
        fuente="DEFRA",
        anio=2025,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0016_empresa_activa_alter_unidadoperativa_tipo"),
    ]

    operations = [
        migrations.RunPython(
            seed_external_truck_freight_factor,
            remove_external_truck_freight_factor,
        ),
    ]
