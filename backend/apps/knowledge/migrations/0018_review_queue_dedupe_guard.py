from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    CREATE UNIQUE INDEX knowledge_review_item_open_dedupe
      ON knowledge_sourcewatchreviewitem (source_id, external_id, content_hash)
      WHERE (estado IN ('open', 'acknowledged'));
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS knowledge_review_item_open_dedupe;")


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0017_source_watch_review_queue")]
    operations = [migrations.RunPython(install, uninstall)]
