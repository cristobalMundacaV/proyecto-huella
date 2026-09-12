from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import MaterialEnvironmentalFactorCandidate as Candidate
from .services.material_candidates import (
    evaluate_material_profile,
    review_material_candidate,
    promote_material_candidate,
)
from .services.material_quality import assess_material_data_quality
from .services.material_source_impact import assess_candidate_impact
from .views_factor_candidates import IsSuperUser, _validation_response


class IsActiveGlobalReviewer(IsSuperUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_active


class CandidateSerializer(serializers.ModelSerializer):
    reviews = serializers.SerializerMethodField()
    eligibility = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        fields = "__all__"
        read_only_fields = [f.name for f in Candidate._meta.fields]

    def get_reviews(self, obj):
        return list(
            obj.reviews.order_by("pk").values(
                "id",
                "decision",
                "reviewer_id",
                "reviewed_at",
                "note",
                "context",
                "eligibility",
            )
        )

    def get_eligibility(self, obj):
        result = evaluate_material_profile(obj.source_profile)
        return {key: result[key] for key in ("compatible", "source_current", "reasons")}


class CandidatePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def candidate(pk):
    return get_object_or_404(
        Candidate.objects.select_related(
            "source_profile__process", "source_profile__snapshot"
        ),
        pk=pk,
    )


@api_view(["GET"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidates(request):
    rows = Candidate.objects.order_by("pk")
    fields = {
        "status": "status",
        "standard": "source_profile__standard",
        "uuid": "source_profile__process_uuid",
        "process_uuid": "source_profile__process_uuid",
        "dataset_version": "source_profile__dataset_version",
        "version": "source_profile__dataset_version",
        "location": "source_profile__process__location_raw",
        "input_unit": "normalization__normalized_input_unit",
    }
    try:
        for param, field in fields.items():
            if param in request.query_params:
                rows = rows.filter(**{field: request.query_params[param]})
        # Exact classification name/code, never substring or fuzzy matching.
        classification = request.query_params.get("classification")
        if classification is not None:
            ids = [
                row.pk
                for row in rows
                if any(
                    classification == entry.get("name")
                    or any(
                        classification in (node.get("id"), node.get("label"))
                        for node in entry.get("path", [])
                        if isinstance(node, dict)
                    )
                    for entry in row.functional_context.get("classification", [])
                    if isinstance(entry, dict)
                )
            ]
            rows = rows.filter(pk__in=ids)
        paginator = CandidatePagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(
            CandidateSerializer(page, many=True).data
        )
    except ValidationError as exc:
        return _validation_response(exc)


@api_view(["GET"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidate_detail(request, candidate_id):
    return Response(CandidateSerializer(candidate(candidate_id)).data)


@api_view(["GET"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidate_eligibility(request, candidate_id):
    return Response(evaluate_material_profile(candidate(candidate_id).source_profile))


@api_view(["GET"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidate_quality(request, candidate_id):
    return Response(assess_material_data_quality(candidate(candidate_id)))


@api_view(["GET"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidate_source_impact(request, candidate_id):
    return Response(assess_candidate_impact(candidate(candidate_id)))


@api_view(["POST"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidate_review(request, candidate_id):
    candidate(candidate_id)
    if not isinstance(request.data, dict) or set(request.data) - {
        "decision",
        "note",
        "context",
    }:
        return Response({"detail": "Campos de revisión inválidos."}, status=400)
    try:
        item = review_material_candidate(
            candidate_id,
            request.user,
            request.data.get("decision"),
            request.data.get("note", ""),
            request.data.get("context"),
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(CandidateSerializer(item).data)


@api_view(["POST"])
@permission_classes([IsActiveGlobalReviewer])
def material_candidate_promote(request, candidate_id):
    candidate(candidate_id)
    if request.data:
        return Response(
            {"detail": "La promoción no acepta overrides ni factor objetivo."},
            status=400,
        )
    try:
        factor, version = promote_material_candidate(candidate_id, request.user)
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(
        {"factor_id": factor.pk, "version_id": version.pk, "estado": version.estado},
        status=201,
    )
