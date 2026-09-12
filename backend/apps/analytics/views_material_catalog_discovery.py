"""MATERIAL-DATA-01H — human material catalog discovery.

Read-only search/browse over the already-existing ÖKOBAUDAT material
candidate catalog (01C). This is lexical/exact search and filtering only:
no ranking, no scoring, no functional-equivalence inference. Any
authenticated user may browse (the governance actions — review/promote —
remain superuser-only in views_material_candidates.py, untouched here).
"""

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MaterialEnvironmentalFactorCandidate as Candidate
from .models import UsuarioOrganizacion
from .models.material_factor_mapping import MaterialFactorMapping
from .services.material_quality import assess_material_data_quality
from .views_material_candidates import CandidatePagination, CandidateSerializer, candidate


def _search_row(item):
    """Lightweight row projection using only already select_related/JSON
    fields — deliberately NOT CandidateSerializer, whose ``eligibility``
    field recomputes ``evaluate_material_profile`` live (source_current,
    snapshot byte checks, reference lookups) and is expensive per row.
    Browsing shows the frozen ``initial_eligibility`` instead; the detail
    endpoint below still surfaces the live view for the one row it fetches."""
    process = item.source_profile.process
    return {
        "id": item.pk,
        "status": item.status,
        "process_name": process.name,
        "process_uuid": str(item.source_profile.process_uuid),
        "dataset_version": item.source_profile.dataset_version,
        "standard": item.source_profile.standard,
        "location": process.location_raw,
        "owner_manufacturer": item.functional_context.get("owner_manufacturer"),
        "dataset_type": item.functional_context.get("dataset_type"),
        "classification": item.functional_context.get("classification"),
        "promoted_factor_id": item.promoted_factor_id,
        "initial_eligibility": item.initial_eligibility,
        "calidad": assess_material_data_quality(item),
    }


def _visible_organizations(user):
    if user.is_superuser:
        return None  # sentinel: unrestricted
    return list(
        UsuarioOrganizacion.objects.filter(user=user, activo=True).values_list(
            "organizacion_id", flat=True
        )
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalog_search(request):
    rows = Candidate.objects.select_related(
        "source_profile__process", "source_profile__snapshot"
    ).order_by("pk")
    params = request.query_params
    exact_fields = {
        "status": "status",
        "standard": "source_profile__standard",
        "uuid": "source_profile__process_uuid",
        "process_uuid": "source_profile__process_uuid",
        "dataset_version": "source_profile__dataset_version",
        "version": "source_profile__dataset_version",
        "location": "source_profile__process__location_raw",
        "input_unit": "normalization__normalized_input_unit",
        "owner": "functional_context__owner_manufacturer",
        "dataset_type": "functional_context__dataset_type",
    }
    try:
        for parameter, field in exact_fields.items():
            if parameter in params:
                rows = rows.filter(**{field: params[parameter]})
        if params.get("q"):
            rows = rows.filter(
                source_profile__process__name__icontains=params["q"]
            )
        if params.get("current") in {"true", "false"}:
            rows = rows.filter(
                initial_eligibility__source_current=(params["current"] == "true")
            )
        classification = params.get("classification")
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
        quality_state = params.get("calidad")
        if quality_state:
            ids = [
                row.pk
                for row in rows
                if assess_material_data_quality(row)["estado"] == quality_state
            ]
            rows = rows.filter(pk__in=ids)
        paginator = CandidatePagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response([_search_row(item) for item in page])
    except ValidationError as exc:
        return Response(
            exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages},
            status=400,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalog_discovery_detail(request, candidate_id):
    item = candidate(candidate_id)
    visible_orgs = _visible_organizations(request.user)
    mappings = MaterialFactorMapping.objects.none()
    if item.promoted_factor_id:
        mappings = MaterialFactorMapping.objects.filter(factor_id=item.promoted_factor_id)
        if visible_orgs is not None:
            mappings = mappings.filter(organizacion_id__in=visible_orgs)
    return Response(
        {
            "candidate": CandidateSerializer(item).data,
            "process": {
                "id": item.source_profile.process_id,
                "name": item.source_profile.process.name,
                "process_uuid": str(item.source_profile.process_uuid),
                "dataset_version": item.source_profile.dataset_version,
            },
            "indicators": [
                {
                    "code": row.code,
                    "value": row.value,
                    "unit": row.unit,
                    "module": row.module,
                }
                for row in item.source_profile.indicators.order_by("pk")
            ],
            "calidad": assess_material_data_quality(item),
            "promoted_factor": (
                {
                    "id": item.promoted_factor_id,
                    "version_id": item.promoted_version_id,
                    "codigo": item.promoted_factor.codigo,
                    "estado_version": item.promoted_version.estado,
                }
                if item.promoted_factor_id
                else None
            ),
            "mappings": [
                {
                    "id": mapping.id,
                    "organizacion_id": mapping.organizacion_id,
                    "material_id": mapping.material_id,
                    "estado": mapping.estado,
                    "vigencia_desde": mapping.vigencia_desde,
                    "vigencia_hasta": mapping.vigencia_hasta,
                }
                for mapping in mappings.select_related("material")
            ],
        }
    )
