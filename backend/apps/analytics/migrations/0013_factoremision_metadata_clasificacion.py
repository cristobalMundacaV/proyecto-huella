from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0012_alter_historialcambiolote_tipo"),
    ]

    operations = [
        migrations.AddField(
            model_name="factoremision",
            name="metadata_clasificacion",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
