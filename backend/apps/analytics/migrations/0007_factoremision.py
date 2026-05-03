from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0006_extracciondocumento"),
    ]

    operations = [
        migrations.CreateModel(
            name="FactorEmision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("actividad", models.CharField(max_length=120)),
                ("unidad", models.CharField(max_length=40)),
                (
                    "factor_emision",
                    models.DecimalField(decimal_places=6, max_digits=12),
                ),
                ("fuente", models.CharField(max_length=180)),
                ("anio", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["actividad", "unidad", "-anio"],
            },
        ),
        migrations.AddConstraint(
            model_name="factoremision",
            constraint=models.UniqueConstraint(
                fields=("actividad", "unidad", "fuente", "anio"),
                name="unique_factor_emision_fuente_anio",
            ),
        ),
    ]
