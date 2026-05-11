from django.urls import path

from .views import kpis, lecturas, ultimas_lecturas


urlpatterns = [
    path("lecturas/", lecturas),
    path("kpis/", kpis),
    path("lecturas/ultimas/", ultimas_lecturas),
]
