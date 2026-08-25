from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0046_capacidadorganizacion_disponibilidad_inicial_and_more")]

    operations = [
        migrations.AddField(
            model_name="obra",
            name="codigo_interno",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AlterField(
            model_name="obra",
            name="tipo_proyecto",
            field=models.CharField(
                choices=[
                    ("Vivienda", "Vivienda"), ("Edificio habitacional", "Edificio habitacional"),
                    ("Infraestructura", "Infraestructura"), ("Industrial", "Industrial"),
                    ("Comercial", "Comercial"), ("Obra publica", "Obra publica"),
                    ("Urbanizacion", "Urbanizacion"), ("Otro", "Otro"),
                    ("Edificación habitacional", "Edificación habitacional"),
                    ("Edificación comercial", "Edificación comercial"),
                    ("Edificación industrial", "Edificación industrial"),
                    ("Infraestructura vial", "Infraestructura vial"),
                    ("Infraestructura sanitaria", "Infraestructura sanitaria"),
                    ("Obra pública / equipamiento", "Obra pública / equipamiento"),
                    ("Urbanización", "Urbanización"),
                ],
                default="Otro", max_length=40,
            ),
        ),
    ]
