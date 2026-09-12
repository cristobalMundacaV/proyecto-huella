from django.urls import path
from . import views

urlpatterns = [
    path("search/", views.search),
    path("epds/<str:epd_id>/", views.detail),
    path("epds/<str:epd_id>/ingest/", views.ingest),
    path("epds/<str:epd_id>/versions/", views.epd_versions),
    path("candidates/", views.candidates),
    path("candidates/<int:candidate_id>/", views.candidate_detail),
    path("candidates/<int:candidate_id>/review/", views.review),
    path("candidates/<int:candidate_id>/promote/", views.promote),
    path("candidates/<int:candidate_id>/mapping/", views.mapping),
    path("candidates/<int:candidate_id>/eligibility/", views.candidate_eligibility),
    path("candidates/<int:candidate_id>/compare/", views.compare),
    path("materials/<int:material_id>/opportunities/", views.material_opportunities),
    path("observability/", views.observability),
]
