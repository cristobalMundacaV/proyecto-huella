from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0007_factoremision"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistorialCambioLote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[('extraido','Dato extraído'),('validado','Dato validado'),('rechazado','Dato rechazado'),('corregido','Dato corregido')], max_length=20)),
                ("fuente", models.CharField(blank=True, max_length=80)),
                ("usuario", models.CharField(blank=True, max_length=120, null=True)),
                ("raw_payload", models.JSONField(default=dict, blank=True)),
                ("normalized_payload", models.JSONField(default=dict, blank=True)),
                ("metadata", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "documento",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="historial_entries", to="analytics.documentolote"),
                ),
                (
                    "extraccion",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="historial_entries", to="analytics.extracciondocumento"),
                ),
                (
                    "lote",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="historial_cambios", to="analytics.lote"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
