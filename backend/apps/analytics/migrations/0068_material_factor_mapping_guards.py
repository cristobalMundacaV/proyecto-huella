from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    CREATE EXTENSION IF NOT EXISTS btree_gist;

    ALTER TABLE analytics_materialfactormapping
      ADD COLUMN vigencia_range daterange
      GENERATED ALWAYS AS (daterange(vigencia_desde, vigencia_hasta, '[]')) STORED;

    ALTER TABLE analytics_materialfactormapping
      ADD CONSTRAINT material_mapping_no_overlap
      EXCLUDE USING gist (
        organizacion_id WITH =,
        material_id WITH =,
        vigencia_range WITH &&
      ) WHERE (estado = 'aprobado');

    CREATE UNIQUE INDEX unique_material_mapping_pending_proposal_open
      ON analytics_materialfactormapping (
        material_id, factor_id, vigencia_desde,
        COALESCE(vigencia_hasta, DATE '9999-12-31')
      ) WHERE (estado = 'propuesto');
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    DROP INDEX IF EXISTS unique_material_mapping_pending_proposal_open;
    ALTER TABLE analytics_materialfactormapping
      DROP CONSTRAINT IF EXISTS material_mapping_no_overlap;
    ALTER TABLE analytics_materialfactormapping
      DROP COLUMN IF EXISTS vigencia_range;
    """)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0067_material_factor_mapping")]
    operations = [migrations.RunPython(install, uninstall)]
