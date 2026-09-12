"""EC3-01 — observability (capability 13).

Purely derived from already-persisted governed state (`SyncRun`, the
shared `RateBudget` row, `ResponseCache`, `EpdVersion`, `Candidate`,
`Review`) — no new metrics/log model, mirroring SOURCE-WATCH's
derive-don't-duplicate `source_health()`. Never includes a credential, a
raw upstream body or a raw exception: every failure reason here is one of
the same sanitized `SyncRun.message` codes `services.ingest_epd` already
writes (`ec3_rate_limited`, `ec3_epd_not_found`, `ec3_unavailable`, ...).
"""

from django.utils import timezone

from apps.knowledge.models import EnvironmentalSource, ExternalRecord, SyncRun

from .models import Candidate, EpdVersion, RateBudget, Review, ResponseCache
from .rate_limit import DatabaseRateLimiter


def observability_summary(*, window_seconds=3600):
    source = EnvironmentalSource.objects.filter(codigo="ec3-openepd").first()
    if source is None:
        return {"registered": False}

    since = timezone.now() - timezone.timedelta(seconds=window_seconds)
    runs = SyncRun.objects.filter(source=source, started_at__gte=since)
    failure_reasons = {}
    for message in runs.filter(estado="error").exclude(message="").values_list("message", flat=True):
        failure_reasons[message] = failure_reasons.get(message, 0) + 1

    budget = RateBudget.objects.filter(key=DatabaseRateLimiter.key).first()
    now = timezone.now().timestamp()
    tokens_last_60s = sum(cost for stamp, cost in (budget.events if budget else []) if stamp > now - 60)

    return {
        "registered": True,
        "window_seconds": window_seconds,
        "requests_total": runs.count(),
        "errors": runs.filter(estado="error").count(),
        "failure_reasons": failure_reasons,
        "rate_limited_recent": failure_reasons.get("ec3_rate_limited", 0),
        "tokens_consumed_last_60s": tokens_last_60s,
        "rate_capacity_per_minute": DatabaseRateLimiter.capacity,
        "cache_rows_total": ResponseCache.objects.count(),
        "cache_rows_expired": ResponseCache.objects.filter(expires_at__lte=timezone.now()).count(),
        "epds_known": ExternalRecord.objects.filter(source=source).count(),
        "epds_flagged_revalidation_failed": ExternalRecord.objects.filter(
            source=source, metadata__ec3_validation_failed=True).count(),
        "epd_versions_total": EpdVersion.objects.filter(record__source=source).count(),
        "candidates_total": Candidate.objects.count(),
        "candidates_pending_review": Candidate.objects.filter(reviews__isnull=True).count(),
        "reviews_total": Review.objects.count(),
    }
