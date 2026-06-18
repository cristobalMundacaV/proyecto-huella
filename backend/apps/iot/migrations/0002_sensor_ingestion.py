from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0005_especiemadera_transporteloteforestal_loteforestal_and_more"),
        ("iot", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DispositivoSensor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dispositivo_id", models.CharField(max_length=120, unique=True)),
                ("nombre", models.CharField(max_length=160)),
                ("tipo_sensor", models.CharField(default="mixto", max_length=40)),
                ("ubicacion", models.CharField(blank=True, max_length=180)),
                ("descripcion", models.TextField(blank=True)),
                ("api_key_hash", models.CharField(blank=True, max_length=180)),
                ("activo", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("constructora", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="dispositivos_iot", to="analytics.constructora")),
                ("obra", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dispositivos_iot", to="analytics.obra")),
                ("etapa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dispositivos_iot", to="analytics.etapaobra")),
                ("factor_emision_default", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="dispositivos_iot", to="analytics.factoremision")),
            ],
            options={"ordering": ["constructora__nombre", "nombre"]},
        ),
        migrations.CreateModel(
            name="RegistroSensor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(blank=True, max_length=120)),
                ("tipo", models.CharField(max_length=40)),
                ("valor", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unidad", models.CharField(blank=True, max_length=40)),
                ("factor_emision_usado", models.DecimalField(decimal_places=6, default=Decimal("0"), max_digits=12)),
                ("co2e_estimado", models.DecimalField(decimal_places=3, editable=False, max_digits=14)),
                ("timestamp_sensor", models.DateTimeField(db_index=True, default=timezone.now)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("estado_procesamiento", models.CharField(db_index=True, default="recibido", max_length=30)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("error_procesamiento", models.TextField(blank=True)),
                ("dispositivo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registros", to="iot.dispositivosensor")),
                ("constructora", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registros_iot", to="analytics.constructora")),
                ("obra", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registros_iot", to="analytics.obra")),
                ("etapa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registros_iot", to="analytics.etapaobra")),
                ("factor_catalogo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registros_iot", to="analytics.factoremision")),
                ("registro_emision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="registros_iot_origen", to="analytics.registroemision")),
            ],
            options={"ordering": ["-timestamp_sensor", "-received_at"]},
        ),
    ]
