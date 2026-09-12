"""SOURCE-WATCH-01H — operational API & observability.

Exposes source health/freshness, recent sync runs/changes, impact
assessments and the human review queue to authenticated operators. Never
exposes raw upstream payloads beyond what the existing `sources/<code>/records/`
detail API already governs. Mutating review actions require the same
`IsSuperUser` gate the rest of this app already uses for administrative
actions — no new tenant concept is introduced (this app has none)."""

from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .change_classification import classify_run
from .impact_routing import route_run_impact
from .models import EnvironmentalSource, SourceWatchReviewDecision, SourceWatchReviewItem, SyncRun
from .review_queue import acknowledge_review_item, resolve_review_item
from .source_health import source_health
from .views import IsSuperUser, KnowledgePagination


def _review_items_with_decisions(queryset):
    return queryset.prefetch_related(
        Prefetch("decisiones", queryset=SourceWatchReviewDecision.objects.order_by("pk")),
    )


def _review_item_data(item):
    return {
        "id": item.pk,
        "source_id": item.source_id,
        "source_codigo": item.source.codigo,
        "sync_run_id": item.sync_run_id,
        "external_id": item.external_id,
        "content_hash": item.content_hash,
        "domain": item.domain,
        "classification": item.classification,
        "severity": item.severity,
        "impact_level": item.impact_level,
        "reasons": item.reasons,
        "affected_objects": item.affected_objects,
        "estado": item.estado,
        "created_at": item.created_at,
        "decisiones": [
            {"decision": d.decision, "actor_id": d.actor_id, "timestamp": d.timestamp, "note": d.note}
            for d in item.decisiones.all()
        ],
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sources_overview(request):
    """The system-level summary: how many sources are healthy/stale/erroring,
    how many changes/reviews are outstanding. Built from already-loaded
    per-source health (no N+1 beyond one query per source's health, which
    itself performs a small constant number of queries)."""

    sources = list(EnvironmentalSource.objects.all())
    buckets = {}
    for source in sources:
        bucket = source_health(source)["health_bucket"]
        buckets[bucket] = buckets.get(bucket, 0) + 1

    open_reviews = SourceWatchReviewItem.objects.filter(estado=SourceWatchReviewItem.Estado.OPEN).count()
    review_required_impacts = SourceWatchReviewItem.objects.filter(
        estado__in=[SourceWatchReviewItem.Estado.OPEN, SourceWatchReviewItem.Estado.ACKNOWLEDGED],
    ).count()

    return Response({
        "sources_total": len(sources),
        "por_estado_salud": buckets,
        "open_reviews": open_reviews,
        "review_required_impacts": review_required_impacts,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_health_detail(request, code):
    source = get_object_or_404(EnvironmentalSource, codigo=code)
    return Response(source_health(source))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def source_run_changes(request, code, run_id):
    source = get_object_or_404(EnvironmentalSource, codigo=code)
    run = get_object_or_404(SyncRun, pk=run_id, source=source)
    classified = classify_run(run)
    impacted = route_run_impact(run)
    return Response({
        "run_id": run.pk,
        "authoritative": classified["authoritative"],
        "source_metadata_changed": classified["source_metadata_changed"],
        "classifications": classified["classifications"],
        "impacts": impacted["impacts"],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def review_items(request):
    rows = _review_items_with_decisions(
        SourceWatchReviewItem.objects.select_related("source")
    ).order_by("-created_at")
    params = request.query_params
    if params.get("source"):
        rows = rows.filter(source__codigo=params["source"])
    if params.get("estado"):
        rows = rows.filter(estado=params["estado"])
    if params.get("severity"):
        rows = rows.filter(severity=params["severity"])
    if params.get("domain"):
        rows = rows.filter(domain=params["domain"])
    if params.get("impact_level"):
        rows = rows.filter(impact_level=params["impact_level"])
    if params.get("desde"):
        start = parse_date(params["desde"])
        if start:
            rows = rows.filter(created_at__date__gte=start)
    if params.get("hasta"):
        end = parse_date(params["hasta"])
        if end:
            rows = rows.filter(created_at__date__lte=end)

    paginator = KnowledgePagination()
    page = paginator.paginate_queryset(rows, request)
    return paginator.get_paginated_response([_review_item_data(item) for item in page])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def review_item_detail(request, pk):
    item = get_object_or_404(
        _review_items_with_decisions(SourceWatchReviewItem.objects.select_related("source")), pk=pk,
    )
    return Response(_review_item_data(item))


@api_view(["POST"])
@permission_classes([IsSuperUser])
def review_item_acknowledge(request, pk):
    get_object_or_404(SourceWatchReviewItem, pk=pk)
    try:
        item = acknowledge_review_item(pk, request.user, request.data.get("note", ""))
    except ValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
    return Response(_review_item_data(item))


@api_view(["POST"])
@permission_classes([IsSuperUser])
def review_item_resolve(request, pk):
    get_object_or_404(SourceWatchReviewItem, pk=pk)
    try:
        item = resolve_review_item(pk, request.user, request.data.get("note", ""))
    except ValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
    return Response(_review_item_data(item))
