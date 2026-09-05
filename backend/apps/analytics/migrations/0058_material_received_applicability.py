from django.db import migrations


METHOD_CODE = "construccion-v1-material-recibido"


def add_material_event_scope(apps, schema_editor):
    VersionMetodologia = apps.get_model("analytics", "VersionMetodologia")
    VersionMetodologia.objects.filter(
        metodologia__organizacion__isnull=True,
        metodologia__codigo=METHOD_CODE,
        version=1,
        aplicabilidad={"tipos_actividad": ["movimiento_material"]},
    ).update(
        aplicabilidad={
            "tipos_actividad": ["movimiento_material"],
            "tipos_evento_material": ["recepcion"],
        }
    )


def remove_material_event_scope(apps, schema_editor):
    VersionMetodologia = apps.get_model("analytics", "VersionMetodologia")
    VersionMetodologia.objects.filter(
        metodologia__organizacion__isnull=True,
        metodologia__codigo=METHOD_CODE,
        version=1,
        aplicabilidad={
            "tipos_actividad": ["movimiento_material"],
            "tipos_evento_material": ["recepcion"],
        },
    ).update(aplicabilidad={"tipos_actividad": ["movimiento_material"]})


class Migration(migrations.Migration):
    dependencies = [("analytics", "0057_add_material_quantity_formula")]
    operations = [migrations.RunPython(add_material_event_scope, remove_material_event_scope)]
