from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    CREATE UNIQUE INDEX unique_material_property_assertion_single_approved
      ON analytics_materialtechnicalpropertyassertion (material_id, property_key)
      WHERE (estado = 'aprobado');
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    DROP INDEX IF EXISTS unique_material_property_assertion_single_approved;
    """)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0072_material_technical_property")]
    operations = [migrations.RunPython(install, uninstall)]
