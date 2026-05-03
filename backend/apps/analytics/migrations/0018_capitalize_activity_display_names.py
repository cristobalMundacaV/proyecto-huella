from django.db import migrations


def format_activity_display_name(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def capitalize_activity_names(apps, schema_editor):
    for model_name in ("FactorEmision", "EmisionLote"):
        model = apps.get_model("analytics", model_name)
        for obj in model.objects.all().only("id", "actividad"):
            formatted = format_activity_display_name(obj.actividad)
            if formatted != obj.actividad:
                model.objects.filter(pk=obj.pk).update(actividad=formatted)


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0017_seed_external_truck_freight_factor"),
    ]

    operations = [
        migrations.RunPython(capitalize_activity_names, migrations.RunPython.noop),
    ]
