from django.urls import path
from .views import (
    ai_advisor,
    compare_dashboard_data,
    dashboard_data,
    optimize_dashboard_data,
    risk_score_data,
    simulate_dashboard_data,
    upload_dashboard_data,
)

urlpatterns = [
    path("dashboard/", dashboard_data),
    path("upload/", upload_dashboard_data),
    path("compare/", compare_dashboard_data),
    path("ai-advisor/", ai_advisor),
    path("simulate/", simulate_dashboard_data),
    path("optimize/", optimize_dashboard_data),
    path("risk-score/", risk_score_data),
]
