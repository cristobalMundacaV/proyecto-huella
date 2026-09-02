from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0052_alter_formulaambiental_factor_ambiental_and_more")]

    operations = [
        migrations.AlterField(
            model_name="formulaambiental",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("transporte_tkm", "Masa x distancia x factor"),
                    ("transporte_vehiculo_km", "Distancia x factor vehiculo"),
                    ("transporte_combustible", "Combustible x factor"),
                    ("combustible_consumido", "Combustible consumido x factor"),
                    ("energia_consumida", "Energia consumida x factor"),
                ],
                max_length=40,
            ),
        ),
    ]
