from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0047_obra_contexto_operacional")]

    operations = [
        migrations.AlterField(
            model_name="actividadoperacional",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("transporte", "Transporte"),
                    ("consumo_energia", "Consumo de energia"),
                    ("consumo_agua", "Consumo de agua"),
                    ("consumo_combustible", "Consumo de combustible"),
                    ("consumo_combustible_estacionario", "Consumo de combustible estacionario"),
                    ("operacion_maquinaria", "Operacion de maquinaria"),
                    ("movimiento_material", "Movimiento de material"),
                    ("gestion_residuo", "Gestion de residuo"),
                    ("generacion_energia", "Generacion de energia"),
                    ("monitoreo_ruido", "Monitoreo de ruido"),
                    ("monitoreo_emisiones_atmosfericas", "Monitoreo de emisiones atmosfericas"),
                    ("gestion_suelo", "Gestion de suelo"),
                    ("gestion_hidrica_suelo", "Gestion hidrica y suelo"),
                    ("proceso_productivo", "Proceso productivo"),
                    ("otro", "Otro"),
                ],
                db_index=True,
                default="otro",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="registroflujoambiental",
            name="flujo",
            field=models.CharField(
                choices=[
                    ("energia", "Energia"),
                    ("generacion_propia", "Generacion propia"),
                    ("agua", "Agua"),
                    ("combustible_estacionario", "Combustible estacionario"),
                    ("residuo", "Residuo"),
                    ("ruido", "Ruido"),
                    ("emisiones_atmosfericas", "Emisiones atmosfericas"),
                    ("suelo", "Suelo"),
                    ("gestion_hidrica_suelo", "Gestion hidrica y suelo"),
                ],
                db_index=True,
                max_length=35,
            ),
        ),
    ]
