from django.db import migrations, models


def migrate_preset_forward(apps, schema_editor):
    Organizacion = apps.get_model("analytics", "Organizacion")
    Organizacion.objects.filter(preset="aserradero").update(preset="forestal")


def migrate_preset_backward(apps, schema_editor):
    Organizacion = apps.get_model("analytics", "Organizacion")
    Organizacion.objects.filter(preset="forestal").update(preset="aserradero")


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0010_documentoambiental_limitenormativoambiental_and_more"),
        ("iot", "0002_sensor_ingestion"),
    ]

    operations = [
        migrations.RenameModel("Constructora", "Organizacion"),
        migrations.RenameModel("UsuarioConstructora", "UsuarioOrganizacion"),
        migrations.RenameModel("ConfiguracionConstructora", "ConfiguracionOrganizacion"),
        migrations.RemoveConstraint(
            model_name="usuarioorganizacion",
            name="unique_usuario_constructora",
        ),
        migrations.RemoveIndex("alertacumplimientoambiental", "analytics_a_constru_d04989_idx"),
        migrations.RemoveIndex("alertacumplimientoambiental", "analytics_a_constru_9b3a7d_idx"),
        migrations.RemoveIndex("documentoambiental", "analytics_d_constru_6e7b4c_idx"),
        migrations.RemoveIndex("documentoambiental", "analytics_d_constru_8fe830_idx"),
        migrations.RemoveIndex("documentoambiental", "analytics_d_constru_f0c353_idx"),
        migrations.RemoveIndex("evidenciaobra", "analytics_e_constru_6c9b7c_idx"),
        migrations.RemoveIndex("evidenciaobra", "analytics_e_constru_86e668_idx"),
        migrations.RemoveIndex("limitenormativoambiental", "analytics_l_constru_724fab_idx"),
        migrations.RemoveIndex("limitenormativoambiental", "analytics_l_constru_73e4c1_idx"),
        migrations.RemoveIndex("loteforestal", "analytics_l_constru_11b591_idx"),
        migrations.RemoveIndex("loteforestal", "analytics_l_constru_ab9ed2_idx"),
        migrations.RemoveIndex("loteforestal", "analytics_l_constru_12bef3_idx"),
        migrations.RemoveIndex("registroemision", "analytics_r_constru_11e247_idx"),
        migrations.RemoveIndex("registroemision", "analytics_r_constru_203888_idx"),
        migrations.RemoveIndex("registroemision", "analytics_r_constru_1653c4_idx"),
        migrations.RemoveIndex("variableambientalextraida", "analytics_v_constru_ee0207_idx"),
        migrations.RemoveIndex("variableambientalextraida", "analytics_v_constru_0cbc4a_idx"),
        migrations.RenameField("organizacion", "constructora_id", "organizacion_id"),
        migrations.RenameField("usuarioorganizacion", "constructora", "organizacion"),
        migrations.RenameField("configuracionorganizacion", "constructora", "organizacion"),
        migrations.RenameField("etapaobra", "constructora", "organizacion"),
        migrations.RenameField("obra", "constructora", "organizacion"),
        migrations.RenameField("loteforestal", "constructora", "organizacion"),
        migrations.RenameField("registroemision", "constructora", "organizacion"),
        migrations.RenameField("evidenciaobra", "constructora", "organizacion"),
        migrations.RenameField("accionambiental", "constructora", "organizacion"),
        migrations.RenameField("documentoambiental", "constructora", "organizacion"),
        migrations.RenameField("limitenormativoambiental", "constructora", "organizacion"),
        migrations.RenameField("variableambientalextraida", "constructora", "organizacion"),
        migrations.RenameField("alertacumplimientoambiental", "constructora", "organizacion"),
        migrations.RunPython(migrate_preset_forward, migrate_preset_backward),
        migrations.AlterField(
            model_name="organizacion",
            name="preset",
            field=models.CharField(
                choices=[
                    ("construccion", "Construcción"),
                    ("forestal", "Forestal"),
                    ("transporte", "Transporte"),
                    ("industrial", "Industrial"),
                ],
                db_index=True,
                default="construccion",
                max_length=40,
            ),
        ),
    ]
