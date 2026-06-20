# Generated manually for Carbono Zero traceable environmental actions

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0002_constructora_preset"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccionAmbiental",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("responsible", models.CharField(blank=True, default="Equipo ambiental", max_length=160)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pendiente", "Pendiente"), ("en_progreso", "En progreso"), ("validacion", "En validacion"), ("completada", "Completada")], db_index=True, default="pendiente", max_length=30)),
                ("source", models.CharField(blank=True, max_length=160)),
                ("evidence", models.CharField(blank=True, max_length=220)),
                ("tracking_kpi", models.CharField(blank=True, max_length=180)),
                ("source_card_id", models.CharField(blank=True, max_length=120)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("constructora", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acciones_ambientales", to="analytics.constructora")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["constructora", "status"], name="analytics_ac_construct_4f4e2a_idx"),
                    models.Index(fields=["constructora", "due_date"], name="analytics_ac_construct_f70a3f_idx"),
                ],
            },
        ),
    ]
