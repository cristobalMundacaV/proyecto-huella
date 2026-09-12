from functools import wraps

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.analytics.models import MaterialOperacional
from apps.analytics.permissions import Permission, require_tenant_permission
from apps.knowledge.models import EnvironmentalSource, ExternalRecord
from .client import Ec3Client, UpstreamError
from .conf import enabled
from .models import Candidate, EpdVersion
from .observability import observability_summary
from .opportunity import compare_candidates, material_candidate_opportunities
from .rate_limit import RateLimited
from .schemas import external_id as validate_external_id
from .services import (candidate_data, evaluate_version, ingest_epd, promote_candidate, propose_candidate,
                       propose_mapping, provenance, require_reviewer, review_candidate)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"non_field_errors": ["Campos no admitidos."]})
        return super().to_internal_value(data)


class SearchInput(StrictSerializer):
    omf = serializers.CharField(max_length=4000)
    page_number = serializers.IntegerField(min_value=1, max_value=1000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=25, default=5)


class CandidateInput(StrictSerializer):
    material_id = serializers.IntegerField(min_value=1)
    epd_version_id = serializers.IntegerField(min_value=1)


class ReviewInput(StrictSerializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    lcia_method = serializers.CharField(max_length=80)
    context = serializers.DictField()


class MappingInput(StrictSerializer):
    vigencia_desde = serializers.DateField()
    vigencia_hasta = serializers.DateField(required=False, allow_null=True, default=None)


def api(methods):
    def decorate(fn):
        @api_view(methods)
        @permission_classes([IsAuthenticated])
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            try:
                enabled()
                require_reviewer(request.user)
                return fn(request, *args, **kwargs)
            except DjangoValidationError as exc:
                return Response({"detail": exc.message_dict if hasattr(exc, "message_dict") else exc.messages}, status=400)
            except RateLimited as exc:
                return Response({"detail": "ec3_rate_limited", "retry_after": exc.retry_after}, status=429, headers={"Retry-After": str(exc.retry_after)})
            except UpstreamError as exc:
                return Response({"detail": exc.code}, status=exc.status)
        return wrapped
    return decorate


def validated(schema, data):
    serializer = schema(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


@api(["GET"])
def search(request):
    params = validated(SearchInput, request.query_params.dict())
    client = Ec3Client()
    try:
        return Response(client.search(**params))
    finally:
        client.close()


@api(["GET"])
def detail(request, epd_id):
    client = Ec3Client()
    try:
        return Response(client.detail(epd_id))
    finally:
        client.close()


@api(["POST"])
def ingest(request, epd_id):
    validated(StrictSerializer, request.data)
    version = ingest_epd(epd_id, request.user)
    return Response({"epd_version_id": version.pk, "provenance": provenance(version)}, status=201)


@api(["GET", "POST"])
def candidates(request):
    if request.method == "POST":
        values = validated(CandidateInput, request.data)
        material = get_object_or_404(MaterialOperacional, pk=values["material_id"])
        version = get_object_or_404(EpdVersion, pk=values["epd_version_id"])
        return Response(candidate_data(propose_candidate(material, version, request.user)), status=201)
    class ListInput(StrictSerializer):
        material_id = serializers.IntegerField(min_value=1)
        page = serializers.IntegerField(min_value=1, default=1)
    params = validated(ListInput, request.query_params.dict())
    material = get_object_or_404(MaterialOperacional, pk=params["material_id"])
    rows = Candidate.objects.filter(material=material).select_related("material", "epd_version__snapshot", "mapping", "promoted_version").order_by("pk")
    offset = (params["page"] - 1) * 25
    count = rows.count()
    return Response({"status": "UNMAPPED" if not count else "CANDIDATES_FOUND", "count": count,
                     "next_page": params["page"] + 1 if offset + 25 < count else None,
                     "results": [candidate_data(c) for c in rows[offset:offset + 25]]})


@api(["GET"])
def candidate_detail(request, candidate_id):
    return Response(candidate_data(get_object_or_404(Candidate, pk=candidate_id)))


@api(["POST"])
def review(request, candidate_id):
    get_object_or_404(Candidate, pk=candidate_id)
    values = validated(ReviewInput, request.data)
    candidate = review_candidate(candidate_id, request.user, values["decision"], values["lcia_method"], values["context"])
    return Response(candidate_data(candidate))


@api(["POST"])
def promote(request, candidate_id):
    get_object_or_404(Candidate, pk=candidate_id)
    validated(StrictSerializer, request.data)
    return Response(candidate_data(promote_candidate(candidate_id, request.user)), status=201)


@api(["POST"])
def mapping(request, candidate_id):
    get_object_or_404(Candidate, pk=candidate_id)
    values = validated(MappingInput, request.data)
    return Response(candidate_data(propose_mapping(candidate_id, request.user, values["vigencia_desde"], values["vigencia_hasta"])), status=201)


class MethodInput(StrictSerializer):
    lcia_method = serializers.CharField(max_length=80)


@api(["GET"])
def candidate_eligibility(request, candidate_id):
    candidate = get_object_or_404(Candidate, pk=candidate_id)
    values = validated(MethodInput, request.query_params.dict())
    return Response(evaluate_version(candidate.epd_version, values["lcia_method"]))


@api(["GET"])
def epd_versions(request, epd_id):
    epd_id = validate_external_id(epd_id)
    source = get_object_or_404(EnvironmentalSource, codigo="ec3-openepd")
    record = get_object_or_404(ExternalRecord, source=source, external_id=epd_id)
    versions = record.ec3_versions.order_by("local_version")
    return Response({"epd_id": epd_id, "record_estado": record.estado,
                     "versions": [{"epd_version_id": v.pk, "local_version": v.local_version,
                                   "upstream_version": v.upstream_version, "retrieved_at": v.retrieved_at,
                                   "provenance": provenance(v)} for v in versions]})


class CompareInput(StrictSerializer):
    candidate_a = serializers.IntegerField(min_value=1)
    candidate_b = serializers.IntegerField(min_value=1)
    lcia_method = serializers.CharField(max_length=80)


@api(["GET"])
def compare(request, candidate_id):
    values = validated(CompareInput, {**request.query_params.dict(), "candidate_a": candidate_id})
    candidate_a = get_object_or_404(Candidate, pk=values["candidate_a"])
    candidate_b = get_object_or_404(Candidate, pk=values["candidate_b"])
    return Response(compare_candidates(candidate_a, candidate_b, values["lcia_method"]))


@api(["GET"])
def material_opportunities(request, material_id):
    material = get_object_or_404(MaterialOperacional, pk=material_id)
    require_tenant_permission(request.user, material.organizacion, Permission.MATERIAL_MAPPING_VIEW)
    values = validated(MethodInput, request.query_params.dict())
    return Response(material_candidate_opportunities(material.organizacion, material, values["lcia_method"]))


@api(["GET"])
def observability(request):
    return Response(observability_summary())
