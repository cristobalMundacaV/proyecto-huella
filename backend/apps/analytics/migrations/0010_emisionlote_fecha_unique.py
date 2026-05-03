from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0009_lote_importador_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="emisionlote",
            name="fecha",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="emisionlote",
            constraint=models.UniqueConstraint(
                fields=(
                    "lote",
                    "actividad",
                    "unidad",
                    "fecha",
                    "cantidad",
                    "factor_emision",
                ),
                name="unique_emision_lote_importada",
            ),
        ),
    ]
