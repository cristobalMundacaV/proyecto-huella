from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0025_lote_unidad_operativa_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="emisionlote",
            name="destino_coords",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emisionlote",
            name="destino_transporte",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="emisionlote",
            name="distancia_km",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="emisionlote",
            name="origen_coords",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="emisionlote",
            name="origen_transporte",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="emisionlote",
            name="ruta_geometry",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
