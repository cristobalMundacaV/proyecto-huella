from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0008_historialcambio"),
    ]

    operations = [
        migrations.AddField(
            model_name="lote",
            name="densidad_kg_m3",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=8,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="lote",
            name="estado",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="lote",
            name="observaciones",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="lote",
            name="porcentaje_carbono",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="lote",
            name="tipo_producto",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name="historialcambiolote",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("extraido", "Dato extraido"),
                    ("importado", "Dato importado"),
                    ("validado", "Dato validado"),
                    ("rechazado", "Dato rechazado"),
                    ("corregido", "Dato corregido"),
                ],
                max_length=20,
            ),
        ),
    ]
