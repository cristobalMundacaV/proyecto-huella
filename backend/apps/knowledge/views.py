from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import EnvironmentalSource,ExternalRecord
from .serializers import EnvironmentalSourceSerializer,ExternalRecordSerializer,ExternalSnapshotSerializer,SyncRunSerializer
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
