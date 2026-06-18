from django.urls import path

from .views import kpis, lecturas, ultimas_lecturas
from .views_ingestion import (
    dispositivo_detail,
    dispositivos,
    ingesta,
    kpis_operacionales,
    registros_sensor,
)


urlpatterns = [
    path("lecturas/", lecturas),
    path("kpis/", kpis),
    path("lecturas/ultimas/", ultimas_lecturas),
    path("dispositivos/", dispositivos),
    path("dispositivos/<str:dispositivo_id>/", dispositivo_detail),
    path("ingesta/", ingesta),
    path("registros/", registros_sensor),
    path("operacion/kpis/", kpis_operacionales),
]
