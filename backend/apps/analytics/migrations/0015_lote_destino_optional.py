from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0014_empresas_unidades_operativas"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lote",
            name="destino",
            field=models.CharField(blank=True, default="", max_length=180),
        ),
    ]
