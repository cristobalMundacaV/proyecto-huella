from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0026_emisionlote_trazabilidad_transporte"),
    ]

    operations = [
        migrations.AddField(
            model_name="emisionlote",
            name="tipo_consumo_combustible",
            field=models.CharField(
                blank=True,
                choices=[
                    ("cosecha", "Cosecha"),
                    ("despacho", "Despacho"),
                    ("transporte", "Transporte"),
                    ("maquinaria", "Maquinaria"),
                    ("vehiculos", "Vehiculos"),
                ],
                max_length=20,
            ),
        ),
    ]
