from django.urls import path
from . import views
urlpatterns=[path("sources/",views.sources),path("sources/<slug:code>/",views.source_detail),path("sources/<slug:code>/sync-runs/",views.source_runs),path("sources/<slug:code>/records/",views.source_records),path("sources/<slug:code>/records/<path:external_id>/",views.record_detail),path("retc/hazardous-waste/",views.retc_hazardous_waste),path("retc/hazardous-waste/metadata/",views.retc_hazardous_waste_metadata)]
