from django.contrib import admin

from .models import (
    AlertaCumplimientoAmbiental,
    ConfiguracionConstructora,
    Constructora,
    DocumentoAmbiental,
    EtapaObra,
    EvidenciaObra,
    FactorEmision,
    HistorialCambioObra,
    LimiteNormativoAmbiental,
    MaterialConstruccion,
    Obra,
    RegistroEmision,
    TransporteObra,
    UsuarioConstructora,
    VariableAmbientalExtraida,
)


@admin.register(Constructora)
class ConstructoraAdmin(admin.ModelAdmin):
    list_display = ("constructora_id", "nombre", "rut", "region", "comuna", "rubro", "activa")
    search_fields = ("constructora_id", "nombre", "rut", "region", "comuna")
    list_filter = ("region", "comuna", "rubro", "activa")


@admin.register(UsuarioConstructora)
class UsuarioConstructoraAdmin(admin.ModelAdmin):
    list_display = ("user", "constructora", "rol", "cargo", "activo")
    search_fields = ("user__username", "user__email", "constructora__nombre", "cargo")
    list_filter = ("rol", "activo")


@admin.register(ConfiguracionConstructora)
class ConfiguracionConstructoraAdmin(admin.ModelAdmin):
    list_display = ("constructora", "unidad_emisiones", "modo_importacion", "evidencia_obligatoria")
    search_fields = ("constructora__nombre",)


@admin.register(EtapaObra)
class EtapaObraAdmin(admin.ModelAdmin):
    list_display = ("etapa_id", "constructora", "nombre", "tipo", "estado", "activa")
    search_fields = ("etapa_id", "constructora__nombre", "nombre", "tipo")
    list_filter = ("tipo", "estado", "activa")


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("codigo_obra", "constructora", "nombre", "tipo_proyecto", "superficie_m2", "estado")
    search_fields = ("codigo_obra", "constructora__nombre", "nombre", "mandante", "ubicacion")
    list_filter = ("tipo_proyecto", "estado", "region", "comuna")


@admin.register(RegistroEmision)
class RegistroEmisionAdmin(admin.ModelAdmin):
    list_display = ("obra", "etapa", "categoria", "fuente_emision", "fecha", "cantidad", "unidad", "emisiones_kg_co2e")
    search_fields = ("obra__codigo_obra", "obra__nombre", "etapa__nombre", "fuente_emision", "proveedor")
    list_filter = ("categoria", "unidad", "fecha")


@admin.register(EvidenciaObra)
class EvidenciaObraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "obra", "tipo_evidencia", "estado_documental", "fecha_documento")
    search_fields = ("nombre", "obra__codigo_obra", "obra__nombre", "tipo_evidencia")
    list_filter = ("tipo_evidencia", "estado_documental", "fecha_documento")


@admin.register(DocumentoAmbiental)
class DocumentoAmbientalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "constructora", "tipo_documento", "industria", "estado_validacion", "fecha_documento")
    search_fields = ("nombre", "constructora__nombre", "tipo_documento", "resumen")
    list_filter = ("industria", "tipo_documento", "estado_procesamiento", "estado_validacion")


@admin.register(VariableAmbientalExtraida)
class VariableAmbientalExtraidaAdmin(admin.ModelAdmin):
    list_display = ("variable_id", "nombre", "constructora", "valor", "unidad", "estado_cumplimiento")
    search_fields = ("variable_id", "nombre", "constructora__nombre", "punto_medicion")
    list_filter = ("categoria", "estado_cumplimiento", "unidad")


@admin.register(LimiteNormativoAmbiental)
class LimiteNormativoAmbientalAdmin(admin.ModelAdmin):
    list_display = ("variable_id", "nombre", "constructora", "normativa", "comparador", "limite", "unidad", "activo")
    search_fields = ("variable_id", "nombre", "constructora__nombre", "normativa")
    list_filter = ("industria", "normativa", "comparador", "activo")


@admin.register(AlertaCumplimientoAmbiental)
class AlertaCumplimientoAmbientalAdmin(admin.ModelAdmin):
    list_display = ("titulo", "constructora", "severidad", "estado", "normativa", "fecha_evento")
    search_fields = ("titulo", "constructora__nombre", "descripcion", "normativa")
    list_filter = ("severidad", "estado", "normativa")


@admin.register(TransporteObra)
class TransporteObraAdmin(admin.ModelAdmin):
    list_display = ("obra", "etapa", "vehiculo", "patente", "distancia_km", "litros_combustible", "emisiones_kg_co2e")
    search_fields = ("obra__codigo_obra", "obra__nombre", "vehiculo", "patente", "origen", "destino")
    list_filter = ("fecha_hora",)


@admin.register(FactorEmision)
class FactorEmisionAdmin(admin.ModelAdmin):
    list_display = ("categoria", "actividad", "unidad", "factor_emision", "fuente", "anio", "alcance")
    search_fields = ("actividad", "actividad_key", "categoria", "unidad", "fuente")
    list_filter = ("categoria", "unidad", "anio", "alcance")


@admin.register(MaterialConstruccion)
class MaterialConstruccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "unidad_default", "factor_emision_default", "fuente", "anio")
    search_fields = ("nombre", "categoria", "fuente")
    list_filter = ("categoria", "unidad_default", "anio")


@admin.register(HistorialCambioObra)
class HistorialCambioObraAdmin(admin.ModelAdmin):
    list_display = ("obra", "tipo", "usuario", "created_at")
    search_fields = ("obra__codigo_obra", "obra__nombre", "tipo")
    list_filter = ("tipo", "created_at")
