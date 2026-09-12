from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    CREATE UNIQUE INDEX unique_map_app_profile_identity
      ON analytics_materialapplicationprofile (
        organizacion_id, COALESCE(obra_id, 0), codigo, version
      );

    CREATE UNIQUE INDEX unique_map_app_profile_single_approved
      ON analytics_materialapplicationprofile (
        organizacion_id, COALESCE(obra_id, 0), codigo
      ) WHERE (estado = 'aprobado');
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    DROP INDEX IF EXISTS unique_map_app_profile_single_approved;
    DROP INDEX IF EXISTS unique_map_app_profile_identity;
    """)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0070_material_application_profile")]
    operations = [migrations.RunPython(install, uninstall)]
