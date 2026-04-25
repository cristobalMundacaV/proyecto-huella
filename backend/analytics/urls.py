from django.urls import path
from .views import (
    ai_advisor,
    compare_dashboard_data,
    dashboard_data,
    upload_dashboard_data,
)

urlpatterns = [
    path("dashboard/", dashboard_data),
    path("upload/", upload_dashboard_data),
    path("compare/", compare_dashboard_data),
    path("ai-advisor/", ai_advisor),
]
