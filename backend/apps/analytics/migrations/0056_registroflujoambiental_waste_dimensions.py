from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0055_alter_evidenciaobra_tipo_evidencia")]

    operations = [
        migrations.AddField(
            model_name="registroflujoambiental",
            name="clasificacion_residuo",
            field=models.CharField(
                blank=True,
                choices=[("no_peligroso", "No peligroso"), ("peligroso", "Peligroso")],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="registroflujoambiental",
            name="tipo_residuo",
            field=models.SlugField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="registroflujoambiental",
            name="tipo_residuo_otro",
            field=models.CharField(blank=True, max_length=180),
        ),
    ]
