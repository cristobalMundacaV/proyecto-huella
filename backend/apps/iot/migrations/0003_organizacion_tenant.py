from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0011_organizacion_tenant"),
        ("iot", "0002_sensor_ingestion"),
    ]

    operations = [
        migrations.RemoveIndex("lecturasensor", "iot_lectura_constru_f3498f_idx"),
        migrations.RenameField("lecturasensor", "constructora", "organizacion"),
        migrations.RenameField("dispositivosensor", "constructora", "organizacion"),
        migrations.RenameField("registrosensor", "constructora", "organizacion"),
    ]
