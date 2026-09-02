from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0054_versionfactorambiental_contexto")]

    operations = [
        migrations.AlterField(
            model_name="evidenciaobra",
            name="tipo_evidencia",
            field=models.CharField(
                choices=[
                    ("factura_material", "Factura de material"), ("guia_despacho", "Guia de despacho"),
                    ("orden_compra", "Orden de compra"), ("factura_combustible", "Factura de combustible"),
                    ("documento_origen", "Documento de origen"), ("boleta_electrica", "Boleta electrica"),
                    ("ticket_pesaje", "Ticket de pesaje"), ("ficha_tecnica_material", "Ficha tecnica de material"),
                    ("certificado_proveedor", "Certificado de proveedor"), ("certificado_forestal", "Certificado forestal"),
                    ("registro_maquinaria", "Registro de maquinaria"), ("registro_retiro_residuos", "Registro de retiro de residuos"),
                    ("registro_produccion", "Registro produccion"), ("registro_secado", "Registro secado"),
                    ("documento_transporte", "Documento de transporte"),
                    ("factura_agua", "Factura o boleta sanitaria"), ("lectura_medidor_agua", "Lectura de medidor de agua"),
                    ("abastecimiento_camion_aljibe", "Abastecimiento por camion aljibe"),
                    ("extraccion_agua_propia", "Extraccion propia de agua"), ("informe_hidrico", "Informe o certificado hidrico"),
                    ("lectura_medidor_electrico", "Lectura de medidor electrico"), ("reporte_generacion", "Reporte de generacion"),
                    ("reporte_inversor_energia", "Reporte de inversor o sistema energetico"),
                    ("vale_combustible", "Vale o comprobante de combustible"), ("registro_abastecimiento", "Registro de abastecimiento"),
                    ("registro_estanque_telemetria", "Registro de estanque o telemetria"), ("hoja_ruta", "Hoja o ficha de ruta"),
                    ("registro_gps_kilometraje", "Registro GPS o kilometraje"), ("comprobante_despacho", "Comprobante de despacho"),
                    ("horometro", "Horometro"), ("parte_diario_maquinaria", "Parte diario de maquinaria"),
                    ("registro_mantenimiento", "Registro de mantenimiento"), ("epd_material", "Declaracion ambiental de producto"),
                    ("manifiesto_retiro", "Manifiesto o guia de retiro"), ("certificado_disposicion_final", "Certificado de disposicion final"),
                    ("informe_gestor_residuos", "Informe del gestor"), ("informe_medicion_ruido", "Informe de medicion de ruido"),
                    ("registro_sonometro", "Registro de sonometro"), ("calibracion_sonometro", "Calibracion de sonometro"),
                    ("informe_muestreo_atmosferico", "Informe de muestreo"),
                    ("informe_laboratorio_atmosferico", "Informe de laboratorio"),
                    ("medicion_instrumental_atmosferica", "Medicion instrumental"),
                    ("informe_monitor_ambiental", "Informe de monitor o sensor"), ("otro", "Otro"),
                ],
                default="otro",
                max_length=40,
            ),
        )
    ]
