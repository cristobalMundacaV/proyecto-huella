from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import EnvironmentalSource,ExternalRecord
from .serializers import EnvironmentalSourceSerializer,ExternalRecordSerializer,ExternalSnapshotSerializer,SyncRunSerializer
from .services import source_freshness
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sources(request): return Response(EnvironmentalSourceSerializer(EnvironmentalSource.objects.filter(activa=True),many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_detail(request,code):
    source=get_object_or_404(EnvironmentalSource,codigo=code);data=EnvironmentalSourceSerializer(source).data;data["freshness"]=source_freshness(source);return Response(data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_runs(request,code):return Response(SyncRunSerializer(get_object_or_404(EnvironmentalSource,codigo=code).sync_runs.all().order_by("-started_at"),many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_records(request,code):return Response(ExternalRecordSerializer(get_object_or_404(EnvironmentalSource,codigo=code).records.select_related("current_snapshot"),many=True).data)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def record_detail(request,code,external_id):
    record=get_object_or_404(ExternalRecord,source__codigo=code,external_id=external_id);data=ExternalRecordSerializer(record).data;data["snapshots"]=ExternalSnapshotSerializer(record.source.snapshots.filter(external_id=external_id).order_by("retrieved_at"),many=True).data;return Response(data)
