from django.db import migrations, models


def copy_factor_context(apps, schema_editor):
    VersionFactor = apps.get_model("analytics", "VersionFactorAmbiental")
    for version in VersionFactor.objects.select_related("factor").iterator():
        version.contexto = version.factor.contexto or {}
        version.save(update_fields=["contexto"])


class Migration(migrations.Migration):
    dependencies = [("analytics", "0053_alter_formulaambiental_tipo")]

    operations = [
        migrations.AddField(
            model_name="versionfactorambiental",
            name="contexto",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(copy_factor_context, migrations.RunPython.noop),
    ]
