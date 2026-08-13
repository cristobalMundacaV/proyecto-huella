from django.db import migrations


def reset_implicit_validation(apps, schema_editor):
    # Correccion conservadora para instalaciones donde 0019 ya fue aplicada:
    # toda regla debe volver a validarse explicitamente con evidencia verificable.
    apps.get_model("analytics", "LimiteNormativoAmbiental").objects.update(validado=False)


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0019_expedienteambiental_and_more"),
    ]

    operations = [
        migrations.RunPython(reset_implicit_validation, migrations.RunPython.noop),
    ]
