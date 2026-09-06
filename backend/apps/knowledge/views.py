from django.http import Http404
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import BcnLegalNormFact,EnvironmentalSource,ExternalFileArtifact,ExternalRecord,HuellaChileEmissionFactorFact,RetcHazardousWasteFact
from .serializers import BcnLegalNormFactSerializer,EnvironmentalSourceSerializer,ExternalRecordSerializer,ExternalSnapshotSerializer,HuellaChileEmissionFactorFactSerializer,RetcHazardousWasteFactSerializer,SyncRunSerializer
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
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def huellachile_emission_factors(request):
    queryset=HuellaChileEmissionFactorFact.objects.filter(artifact__is_current=True).select_related("artifact").order_by("id")
    for parameter in ("dataset_year","alcance","categoria","actividad","unidad_actividad","technical_source_1"):
        value=request.query_params.get(parameter)
        if value: queryset=queryset.filter(**{parameter if parameter=="dataset_year" else f"{parameter}__iexact":value})
    return paginated(request,queryset,HuellaChileEmissionFactorFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def huellachile_emission_factors_metadata(request):
    artifacts=ExternalFileArtifact.objects.select_related("source","parent_record").filter(source__codigo="huellachile",parent_record__kind="huellachile_emission_factor_dataset",is_current=True,metadata__edition=request.query_params.get("edition","completa"))
    if request.query_params.get("year"): artifacts=artifacts.filter(metadata__year=request.query_params["year"])
    artifact=artifacts.order_by("-metadata__year","-retrieved_at").first()
    if not artifact: raise Http404
    metadata=artifact.metadata;publication=artifact.parent_record.current_snapshot.raw_payload or {}
    return Response({"publisher":metadata.get("publisher"),"source_page":metadata.get("source_page"),"logical_resource":artifact.external_resource_id,"title":artifact.parent_record.title,"year":metadata.get("year"),"edition":metadata.get("edition"),"filename":publication.get("filename") or metadata.get("filename"),"filename_version":publication.get("filename_version") or metadata.get("filename_version"),"source_url":publication.get("url") or artifact.source_url,"sha256":artifact.content_sha256,"bytes":artifact.byte_size,"retrieved_at":artifact.retrieved_at,"artifact_version":artifact.version,"fact_count":artifact.huellachile_emission_factor_facts.count(),"sheet_count":len(metadata.get("sheets",[])),"references":metadata.get("references",[]),"freshness":source_freshness(artifact.source)})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_norms(request):
    queryset=BcnLegalNormFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="bcn-leychile").prefetch_related("versions","relations").order_by("number")
    for parameter,lookup in {"number":"number__iexact","norm_type":"norm_type_name__iexact","issuer":"issuer_name__icontains","title":"title__icontains"}.items():
        if request.query_params.get(parameter):queryset=queryset.filter(**{lookup:request.query_params[parameter]})
    if request.query_params.get("scope_tag"):queryset=queryset.filter(scope_tags__contains=[request.query_params["scope_tag"]])
    return paginated(request,queryset,BcnLegalNormFactSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bcn_norm_detail(request,pk):
    queryset=BcnLegalNormFact.objects.filter(snapshot__current_for__current_snapshot=models.F("snapshot"),snapshot__source__codigo="bcn-leychile").prefetch_related("versions","relations")
    return Response(BcnLegalNormFactSerializer(get_object_or_404(queryset,pk=pk)).data)
