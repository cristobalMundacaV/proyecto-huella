from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import EnvironmentalSource,ExternalFileArtifact,ExternalRecord,RetcHazardousWasteFact
from .serializers import EnvironmentalSourceSerializer,ExternalRecordSerializer,ExternalSnapshotSerializer,RetcHazardousWasteFactSerializer,SyncRunSerializer
from .services import source_freshness
class KnowledgePagination(PageNumberPagination):
    page_size=50;page_size_query_param="page_size";max_page_size=200
def paginated(request,queryset,serializer):
    paginator=KnowledgePagination();page=paginator.paginate_queryset(queryset,request);return paginator.get_paginated_response(serializer(page,many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sources(request): return Response(EnvironmentalSourceSerializer(EnvironmentalSource.objects.filter(activa=True),many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_detail(request,code):
    source=get_object_or_404(EnvironmentalSource,codigo=code);data=EnvironmentalSourceSerializer(source).data;data["freshness"]=source_freshness(source);return Response(data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_runs(request,code):return paginated(request,get_object_or_404(EnvironmentalSource,codigo=code).sync_runs.all().order_by("-started_at"),SyncRunSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_records(request,code):return paginated(request,get_object_or_404(EnvironmentalSource,codigo=code).records.select_related("current_snapshot").order_by("external_id"),ExternalRecordSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def record_detail(request,code,external_id):
    record=get_object_or_404(ExternalRecord,source__codigo=code,external_id=external_id);data=ExternalRecordSerializer(record).data
    paginator=KnowledgePagination();page=paginator.paginate_queryset(record.source.snapshots.filter(external_id=external_id).order_by("retrieved_at"),request);data["snapshots"]={"count":paginator.page.paginator.count,"next":paginator.get_next_link(),"previous":paginator.get_previous_link(),"results":ExternalSnapshotSerializer(page,many=True).data};return Response(data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retc_hazardous_waste(request):
    queryset=RetcHazardousWasteFact.objects.filter(artifact__is_current=True).select_related("artifact").order_by("id")
    for parameter in ("year","region","comuna","contaminantes","razon_social","rubro"):
        value=request.query_params.get(parameter)
        if not value: continue
        lookup=parameter if parameter=="year" else f"{parameter}__iexact"
        queryset=queryset.filter(**{lookup:value})
    return paginated(request,queryset,RetcHazardousWasteFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def retc_hazardous_waste_metadata(request):
    artifact=get_object_or_404(ExternalFileArtifact.objects.select_related("source","parent_record"),source__codigo="retc",parent_record__canonical_key="generacion-de-residuos-peligrosos",is_current=True)
    return Response({"source":artifact.source.nombre,"dataset":artifact.parent_record.title,"resource":{"id":artifact.external_resource_id,"name":artifact.name,"url":artifact.source_url,"format":artifact.format},"year":artifact.metadata.get("year") or artifact.retc_hazardous_waste_facts.values_list("year",flat=True).first(),"sha256":artifact.content_sha256,"retrieved_at":artifact.retrieved_at,"upstream_modified_at":artifact.upstream_modified_at,"record_count":artifact.retc_hazardous_waste_facts.count(),"license":{"name":artifact.source.licencia_nombre,"url":artifact.source.licencia_url,"attribution_required":artifact.source.atribucion_requerida},"freshness":source_freshness(artifact.source)})
