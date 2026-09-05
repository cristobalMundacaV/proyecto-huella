from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from .models import (
    EnvironmentalFactorCandidate,
    FactorAmbiental,
    VersionFactorAmbiental,
)
from .services.factor_candidates import (
    apply_candidate_mapping,
    equivalent_global_factors,
    evaluate_factor_candidate_compatibility,
    promote_candidate_to_draft,
)
from .services.factor_governance import transition_factor_version


def _factor_summary(factor):
    return {
        "id": factor.id,
        "codigo": factor.codigo,
        "nombre": factor.nombre,
        "unidad_entrada": factor.unidad_entrada,
        "unidad_resultado": factor.unidad_resultado,
        "contexto": factor.contexto,
    }


def _candidate_data(candidate):
    fact = candidate.source_fact
    compatibility = candidate.compatibility or evaluate_factor_candidate_compatibility(
        candidate
    )
    equivalence = (
        equivalent_global_factors(candidate)
        if candidate.mapping_type
        else {"status": "sin_mapping", "factors": []}
    )
    return {
        "id": candidate.id,
        "status": candidate.status,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
        "reviewed_by": candidate.reviewed_by_id,
        "reviewed_at": candidate.reviewed_at,
        "review_note": candidate.review_note,
        "source": {
            "provider": "HuellaChile",
            "publisher": fact.publisher,
            "dataset_year": fact.dataset_year,
            "external_activity": fact.actividad,
            "external_category": fact.categoria,
            "external_scope": fact.alcance,
            "published_factor": fact.published_value_raw,
            "activity_unit": fact.unidad_actividad,
            "factor_unit": fact.unidad_factor,
            "technical_sources": [
                fact.technical_source_1,
                fact.technical_source_2,
                fact.technical_source_3,
            ],
            "fact_id": fact.id,
            "artifact_id": fact.artifact_id,
            "artifact_version": fact.artifact.version,
            "artifact_sha256": fact.artifact.content_sha256,
            "source_current": fact.artifact.is_current,
            "source_status": "current" if fact.artifact.is_current else "outdated",
        },
        "normalized_input_unit": compatibility.get("normalized_input_unit"),
        "normalized_result_unit": compatibility.get("normalized_result_unit"),
        "mechanical_compatibility": compatibility.get("compatible", False),
        "compatibility_reasons": compatibility.get("reasons", []),
        "compatibility": compatibility,
        "mapping_type": candidate.mapping_type,
        "mapping_context": candidate.mapping_context,
        "equivalence": {
            "status": equivalence["status"],
            "factors": [_factor_summary(item) for item in equivalence["factors"]],
        },
        "promoted_factor": (
            _factor_summary(candidate.promoted_factor)
            if candidate.promoted_factor_id
            else None
        ),
        "promoted_version": candidate.promoted_version_id,
    }


def _candidate(candidate_id):
    return get_object_or_404(
        EnvironmentalFactorCandidate.objects.select_related(
            "source_fact__artifact",
            "reviewed_by",
            "promoted_factor",
            "promoted_version",
        ),
        pk=candidate_id,
    )


def _validation_response(exc):
    if hasattr(exc, "message_dict"):
        return Response(exc.message_dict, status=400)
    return Response({"detail": exc.messages}, status=400)


def _require_superuser(request):
    return request.user.is_authenticated and request.user.is_superuser


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return _require_superuser(request)


@api_view(["GET"])
@permission_classes([IsSuperUser])
def factor_candidates(request):
    rows = EnvironmentalFactorCandidate.objects.select_related(
        "source_fact__artifact", "reviewed_by", "promoted_factor", "promoted_version"
    ).order_by("id")
    if request.query_params.get("status"):
        rows = rows.filter(status=request.query_params["status"])
    if request.query_params.get("year"):
        rows = rows.filter(source_fact__dataset_year=request.query_params["year"])
    return Response([_candidate_data(item) for item in rows])


@api_view(["GET"])
@permission_classes([IsSuperUser])
def factor_candidate_detail(request, candidate_id):
    return Response(_candidate_data(_candidate(candidate_id)))


@api_view(["POST"])
@permission_classes([IsSuperUser])
def factor_candidate_mapping(request, candidate_id):
    if not _require_superuser(request):
        return Response(
            {"detail": "Sólo un superusuario puede gobernar factores globales."},
            status=403,
        )
    try:
        item = apply_candidate_mapping(
            _candidate(candidate_id),
            request.user,
            request.data.get("mapping_type"),
            request.data.get("mapping_context") or {},
            request.data.get("review_note", ""),
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(_candidate_data(item))


@api_view(["POST"])
@permission_classes([IsSuperUser])
def factor_candidate_reject(request, candidate_id):
    if not _require_superuser(request):
        return Response(
            {"detail": "Sólo un superusuario puede gobernar factores globales."},
            status=403,
        )
    item = _candidate(candidate_id)
    if item.promoted_version_id:
        return Response(
            {"detail": "Un candidato promovido no puede rechazarse."}, status=400
        )
    item.status = item.Status.REJECTED
    item.reviewed_by = request.user
    item.reviewed_at = timezone.now()
    item.review_note = request.data.get("review_note", "")
    item.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "updated_at",
        ]
    )
    return Response(_candidate_data(item))


@api_view(["POST"])
@permission_classes([IsSuperUser])
def factor_candidate_promote(request, candidate_id):
    if not _require_superuser(request):
        return Response(
            {"detail": "Sólo un superusuario puede promover factores globales."},
            status=403,
        )
    target = None
    if request.data.get("target_factor_id") is not None:
        target = get_object_or_404(FactorAmbiental, pk=request.data["target_factor_id"])
    try:
        factor, version = promote_candidate_to_draft(
            _candidate(candidate_id), request.user, request.data.get("mode"), target
        )
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(
        {
            "factor": _factor_summary(factor),
            "version": {
                "id": version.id,
                "version": version.version,
                "estado": version.estado,
            },
        },
        status=201,
    )


@api_view(["POST"])
@permission_classes([IsSuperUser])
def global_factor_version_transition(request, factor_id, version_id):
    if not _require_superuser(request):
        return Response(
            {"detail": "Sólo un superusuario puede gobernar factores globales."},
            status=403,
        )
    version = get_object_or_404(
        VersionFactorAmbiental.objects.select_related("factor"),
        pk=version_id,
        factor_id=factor_id,
        factor__organizacion__isnull=True,
    )
    try:
        transition_factor_version(version, request.data.get("estado"))
    except ValidationError as exc:
        return _validation_response(exc)
    return Response(
        {"id": version.id, "version": version.version, "estado": version.estado}
    )
