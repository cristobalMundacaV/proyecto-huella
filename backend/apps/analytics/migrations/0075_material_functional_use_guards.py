from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    CREATE UNIQUE INDEX unique_material_functional_use_single_approved
      ON analytics_materialfunctionaluse (material_id, profile_id)
      WHERE (estado = 'aprobado');
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    DROP INDEX IF EXISTS unique_material_functional_use_single_approved;
    """)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0074_material_functional_use")]
    operations = [migrations.RunPython(install, uninstall)]
