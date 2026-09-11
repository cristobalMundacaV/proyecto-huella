from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE FUNCTION knowledge_obd_detail_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Oekobaudat environmental history is immutable';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER knowledge_obd_profile_immutable BEFORE UPDATE OR DELETE
        ON knowledge_oekobaudatenvironmentalprofilefact
        FOR EACH ROW EXECUTE FUNCTION knowledge_obd_detail_immutable();
        CREATE TRIGGER knowledge_obd_indicator_immutable BEFORE UPDATE OR DELETE
        ON knowledge_oekobaudatenvironmentalindicatorfact
        FOR EACH ROW EXECUTE FUNCTION knowledge_obd_detail_immutable();
        CREATE TRIGGER knowledge_obd_snapshot_immutable BEFORE UPDATE OR DELETE
        ON knowledge_externalsnapshot FOR EACH ROW
        WHEN (OLD.record_kind IN ('okobaudat_process_detail', 'okobaudat_detail_reference'))
        EXECUTE FUNCTION knowledge_obd_detail_immutable();
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        DROP TRIGGER IF EXISTS knowledge_obd_snapshot_immutable ON knowledge_externalsnapshot;
        DROP TRIGGER IF EXISTS knowledge_obd_indicator_immutable ON knowledge_oekobaudatenvironmentalindicatorfact;
        DROP TRIGGER IF EXISTS knowledge_obd_profile_immutable ON knowledge_oekobaudatenvironmentalprofilefact;
        DROP FUNCTION IF EXISTS knowledge_obd_detail_immutable();
    """)


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0012_oekobaudatenvironmentalprofilefact_and_more")]
    operations = [migrations.RunPython(install, uninstall)]
