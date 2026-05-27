from django.contrib import admin

from .models import LecturaSensor


@admin.register(LecturaSensor)
class LecturaSensorAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_registro",
        "constructora",
        "etapa_obra",
        "sensor",
        "tipo",
        "valor",
        "unidad",
        "co2e_estimado",
    )
    search_fields = ("constructora", "etapa_obra", "sensor", "tipo")
    list_filter = ("tipo", "fecha_registro")
