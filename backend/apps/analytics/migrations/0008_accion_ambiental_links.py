# Generated manually for Carbono Zero environmental action traceability links

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0007_accion_ambiental"),
    ]

    operations = [
        migrations.AddField(
            model_name="accionambiental",
            name="obra",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_ambientales", to="analytics.obra"),
        ),
        migrations.AddField(
            model_name="accionambiental",
            name="lote_forestal",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_ambientales", to="analytics.loteforestal"),
        ),
        migrations.AddField(
            model_name="accionambiental",
            name="registro_emision",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_ambientales", to="analytics.registroemision"),
        ),
        migrations.AddField(
            model_name="accionambiental",
            name="evidencia",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acciones_ambientales", to="analytics.evidenciaobra"),
        ),
        migrations.AddIndex(
            model_name="accionambiental",
            index=models.Index(fields=["constructora", "obra"], name="analytics_ac_construct_obra_idx"),
        ),
        migrations.AddIndex(
            model_name="accionambiental",
            index=models.Index(fields=["constructora", "lote_forestal"], name="analytics_ac_construct_lote_idx"),
        ),
        migrations.AddIndex(
            model_name="accionambiental",
            index=models.Index(fields=["constructora", "registro_emision"], name="analytics_ac_construct_reg_idx"),
        ),
        migrations.AddIndex(
            model_name="accionambiental",
            index=models.Index(fields=["constructora", "evidencia"], name="analytics_ac_construct_evi_idx"),
        ),
    ]
