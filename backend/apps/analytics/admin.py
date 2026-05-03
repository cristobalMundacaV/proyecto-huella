from django.contrib import admin

from .models import (
    DocumentoLote,
    EmisionLote,
    Empresa,
    EspecieMadera,
    ExtraccionDocumento,
    FactorEmision,
    Lote,
    TransporteLote,
    UnidadOperativa,
)


@admin.register(EspecieMadera)
class EspecieMaderaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "densidad_kg_m3", "porcentaje_carbono")
    search_fields = ("nombre",)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("empresa_id", "nombre", "rut", "region", "comuna", "rubro")
    search_fields = ("empresa_id", "nombre", "rut", "region", "comuna")
    list_filter = ("region", "comuna", "rubro")


@admin.register(UnidadOperativa)
class UnidadOperativaAdmin(admin.ModelAdmin):
    list_display = ("unidad_id", "empresa", "nombre", "tipo", "activa")
    search_fields = ("unidad_id", "empresa__nombre", "nombre", "tipo")
    list_filter = ("tipo", "activa")


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        "id_lote",
        "empresa",
        "unidad_operativa",
        "empresa_aserradero",
        "fecha",
        "especie",
        "volumen_m3",
        "origen",
        "tipo_producto",
        "estado",
        "emisiones_kg_co2e",
    )
    search_fields = ("id_lote", "empresa_aserradero", "empresa__nombre", "unidad_operativa__nombre", "especie", "origen")
    list_filter = ("empresa", "unidad_operativa", "especie", "fecha")


@admin.register(EmisionLote)
class EmisionLoteAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "unidad_operativa",
        "lote",
        "actividad",
        "tipo_asignacion",
        "fecha",
        "cantidad",
        "unidad",
        "factor_emision",
        "emisiones_kg_co2e",
    )
    search_fields = ("empresa__nombre", "unidad_operativa__nombre", "lote__id_lote", "actividad", "unidad")
    list_filter = ("tipo_asignacion", "actividad", "unidad", "fecha")


@admin.register(FactorEmision)
class FactorEmisionAdmin(admin.ModelAdmin):
    list_display = (
        "categoria",
        "actividad",
        "actividad_key",
        "unidad",
        "factor_emision",
        "anio",
    )
    search_fields = ("actividad", "actividad_key", "unidad")
    list_filter = ("categoria", "unidad", "anio")


@admin.register(DocumentoLote)
class DocumentoLoteAdmin(admin.ModelAdmin):
    list_display = (
        "lote",
        "tipo_documento",
        "fecha",
        "estado_validacion",
        "archivo",
    )
    search_fields = ("lote__id_lote", "tipo_documento", "archivo")
    list_filter = ("tipo_documento", "estado_validacion", "fecha")


@admin.register(TransporteLote)
class TransporteLoteAdmin(admin.ModelAdmin):
    list_display = (
        "lote",
        "vehiculo",
        "patente",
        "fecha_hora",
        "ruta",
        "distancia_km",
        "litros_calculados",
        "emisiones_transporte_kg_co2e",
    )
    search_fields = ("lote__id_lote", "vehiculo", "patente", "ruta")
    list_filter = ("fecha_hora",)


@admin.register(ExtraccionDocumento)
class ExtraccionDocumentoAdmin(admin.ModelAdmin):
    list_display = ("documento", "estado_revision", "created_at")
    search_fields = ("documento__lote__id_lote", "texto_extraido")
    list_filter = ("estado_revision", "created_at")

# Register your models here.
