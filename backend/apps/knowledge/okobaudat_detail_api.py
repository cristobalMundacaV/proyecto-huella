from datetime import timedelta

from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .models import OekobaudatEnvironmentalProfileFact, OekobaudatEnvironmentalIndicatorFact
from .bootstrap import OKOBAUDAT_TERMS


class DetailPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class ProvenanceSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="snapshot.source.codigo", read_only=True)
    content_hash = serializers.CharField(source="snapshot.content_hash", read_only=True)
    retrieved_at = serializers.DateTimeField(source="snapshot.retrieved_at", read_only=True)
    source_url = serializers.CharField(source="snapshot.source_url", read_only=True)
    freshness = serializers.SerializerMethodField()
    source_terms = serializers.SerializerMethodField()

    def get_source_terms(self, obj):
        return obj.snapshot.metadata.get("source_terms", OKOBAUDAT_TERMS)

    def get_freshness(self, obj):
        return "stale" if timezone.now() > obj.snapshot.retrieved_at + timedelta(hours=obj.snapshot.source.stale_after_hours) else "fresh"


class IndicatorSerializer(ProvenanceSerializer):
    class Meta:
        model = OekobaudatEnvironmentalIndicatorFact
        fields = "__all__"


class ProfileSerializer(ProvenanceSerializer):
    indicators = IndicatorSerializer(many=True, read_only=True)
    dataset = serializers.CharField(source="process.name", read_only=True)
    datastock_uuid = serializers.UUIDField(source="process.datastock_uuid", read_only=True)
    operational_scope = serializers.SerializerMethodField()

    def get_operational_scope(self, obj):
        return "A1-A3" if obj.standard in {"EN 15804+A1", "EN 15804+A2"} else None

    class Meta:
        model = OekobaudatEnvironmentalProfileFact
        fields = "__all__"


class Filters(serializers.Serializer):
    uuid = serializers.UUIDField(required=False)
    process_uuid = serializers.UUIDField(required=False)
    version = serializers.CharField(required=False)
    dataset_version = serializers.CharField(required=False)
    standard = serializers.ChoiceField(choices=["EN 15804+A1", "EN 15804+A2", "unknown"], required=False)
    indicator = serializers.CharField(required=False)
    module = serializers.CharField(required=False)


class FilterMixin:
    permission_classes = [IsAuthenticated]
    pagination_class = DetailPagination

    def get_queryset(self):
        qs = super().get_queryset()
        filters = Filters(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        data = filters.validated_data
        for parameter, field in {"uuid": "process_uuid", "process_uuid": "process_uuid", "version": "dataset_version",
                                 "dataset_version": "dataset_version", "standard": "standard"}.items():
            if parameter in data:
                qs = qs.filter(**{field: data[parameter]})
        prefix = "indicators__" if qs.model is OekobaudatEnvironmentalProfileFact else ""
        if "indicator" in data:
            qs = qs.filter(**{prefix + "code": data["indicator"]})
        if "module" in data:
            qs = qs.filter(**{prefix + "module": data["module"]})
        return qs.distinct().order_by("pk")


class ProfileList(FilterMixin, generics.ListAPIView):
    serializer_class = ProfileSerializer
    queryset = OekobaudatEnvironmentalProfileFact.objects.select_related("process", "snapshot__source").prefetch_related("indicators__snapshot__source")


class ProfileDetail(FilterMixin, generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    queryset = ProfileList.queryset


class IndicatorList(FilterMixin, generics.ListAPIView):
    serializer_class = IndicatorSerializer
    queryset = OekobaudatEnvironmentalIndicatorFact.objects.select_related("snapshot__source")


class IndicatorDetail(FilterMixin, generics.RetrieveAPIView):
    serializer_class = IndicatorSerializer
    queryset = IndicatorList.queryset
