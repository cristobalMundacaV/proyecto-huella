"""SOURCE-WATCH-01F — review queue & human governance.

Turns a `requires_review` impact-routing result into a durable, auditable
review task. Resolving/acknowledging a review item never applies any
downstream domain mutation — that always requires a human to separately
invoke that domain's own existing governed service. Repeated watch
executions never create duplicate open items for the same immutable
source change: a PostgreSQL partial unique index
(`knowledge_review_item_open_dedupe`) is the real safety net; the
application-level check below is the ergonomic fast path (return the
existing item instead of racing the index)."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied

from .impact_routing import route_run_impact
from .models import SourceWatchReviewDecision, SourceWatchReviewItem


def _require_global_review_permission(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_superuser:
        raise PermissionDenied("Se requiere permiso global de administrador para esta accion.")


def _open_dedupe_lookup(source, external_id, content_hash):
    return SourceWatchReviewItem.objects.filter(
        source=source, external_id=external_id, content_hash=content_hash or "",
        estado__in=[SourceWatchReviewItem.Estado.OPEN, SourceWatchReviewItem.Estado.ACKNOWLEDGED],
    ).select_for_update().first()


@transaction.atomic
def open_review_item(run, impact):
    """Idempotent: calling this again for the same run+external_id+content
    hash returns the already-open item instead of creating a duplicate."""

    content_hash = (impact["provenance"] or {}).get("content_hash") or ""
    existing = _open_dedupe_lookup(run.source, impact["external_id"], content_hash)
    if existing is not None:
        return existing, False

    try:
        with transaction.atomic():
            item = SourceWatchReviewItem(
                source=run.source,
                sync_run=run,
                external_id=impact["external_id"],
                content_hash=content_hash,
                domain=impact["domain"],
                classification=impact["classification"],
                severity=impact.get("severity", ""),
                impact_level=impact["impact_level"],
                reasons=impact["reasons"],
                affected_objects=impact["affected_objects"],
            )
            item.save()
    except IntegrityError as exc:
        existing = _open_dedupe_lookup(run.source, impact["external_id"], content_hash)
        if existing is not None:
            return existing, False
        raise ValidationError("No se pudo crear el item de revision.") from exc
    return item, True


def open_review_items_for_run(run, classifications_with_impacts):
    """Opens one review item per impact whose classification's
    `requires_review` is true. `classifications_with_impacts` pairs each
    `change_classification.classify_change()` result with its
    `impact_routing.route_impact()` result (caller already computed both;
    this function never recomputes or refetches upstream)."""

    opened = []
    for classification, impact in classifications_with_impacts:
        if not classification.get("requires_review"):
            continue
        item, created = open_review_item(run, impact)
        opened.append((item, created))
    return opened


@transaction.atomic
def acknowledge_review_item(item_id, user, note=""):
    _require_global_review_permission(user)
    item = SourceWatchReviewItem.objects.select_for_update().get(pk=item_id)
    if item.estado != SourceWatchReviewItem.Estado.OPEN:
        raise ValidationError("Solo un item abierto puede reconocerse.")
    item.estado = SourceWatchReviewItem.Estado.ACKNOWLEDGED
    item.save()
    SourceWatchReviewDecision.objects.create(
        review_item=item, decision=SourceWatchReviewDecision.Decision.ACKNOWLEDGED,
        actor=user, note=note,
    )
    return item


@transaction.atomic
def resolve_review_item(item_id, user, note=""):
    _require_global_review_permission(user)
    item = SourceWatchReviewItem.objects.select_for_update().get(pk=item_id)
    if item.estado not in (SourceWatchReviewItem.Estado.OPEN, SourceWatchReviewItem.Estado.ACKNOWLEDGED):
        raise ValidationError("Solo un item abierto o reconocido puede resolverse.")
    item.estado = SourceWatchReviewItem.Estado.RESOLVED
    item.save()
    SourceWatchReviewDecision.objects.create(
        review_item=item, decision=SourceWatchReviewDecision.Decision.RESOLVED,
        actor=user, note=note,
    )
    return item


def open_items_from_run(run):
    """Convenience wiring for 01G's orchestrator: classify + route + open
    review items for one completed run in a single call."""

    result = route_run_impact(run)
    from .change_classification import classify_run

    classifications = classify_run(run)["classifications"]
    paired = list(zip(classifications, result["impacts"]))
    return open_review_items_for_run(run, paired)
