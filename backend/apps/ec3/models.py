from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("La evidencia y las decisiones EC3 son inmutables.")

    def delete(self):
        raise ValidationError("La evidencia y las decisiones EC3 son inmutables.")

    def bulk_update(self, *args, **kwargs):
        raise ValidationError("La evidencia y las decisiones EC3 son inmutables.")


class Immutable(models.Model):
    objects = ImmutableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("La evidencia y las decisiones EC3 son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La evidencia y las decisiones EC3 son inmutables.")


class RateBudget(models.Model):
    # One account-wide budget, shared by web workers and jobs, including retries.
    key = models.CharField(max_length=80, primary_key=True)
    events = models.JSONField(default=list)
    blocked_until = models.FloatField(default=0)


class ResponseCache(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    value = models.JSONField()
    expires_at = models.DateTimeField(db_index=True)


class EpdVersion(Immutable):
    snapshot = models.ForeignKey("knowledge.ExternalSnapshot", on_delete=models.PROTECT, related_name="ec3_versions")
    record = models.ForeignKey("knowledge.ExternalRecord", on_delete=models.PROTECT, related_name="ec3_versions")
    upstream_version = models.PositiveIntegerField(null=True)
    local_version = models.PositiveIntegerField()
    evidence = models.JSONField()
    evidence_checksum = models.CharField(max_length=64)
    rights_reference = models.CharField(max_length=500)
    retrieved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["record", "local_version"], name="ec3_record_version_unique")]


class Candidate(models.Model):
    material = models.ForeignKey("analytics.MaterialOperacional", on_delete=models.PROTECT, related_name="ec3_candidates")
    epd_version = models.ForeignKey(EpdVersion, on_delete=models.PROTECT, related_name="candidates")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    promoted_version = models.OneToOneField("analytics.VersionFactorAmbiental", null=True, blank=True, on_delete=models.PROTECT, related_name="ec3_candidate")
    mapping = models.OneToOneField("analytics.MaterialFactorMapping", null=True, blank=True, on_delete=models.PROTECT, related_name="ec3_candidate")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["material", "epd_version"], name="ec3_material_epd_candidate_unique")]


class Review(Immutable):
    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name="reviews")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=12, choices=[("approved", "Approved"), ("rejected", "Rejected")])
    lcia_method = models.CharField(max_length=80, blank=True)
    context = models.JSONField()
    evaluation = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(decision__in=["approved", "rejected"]), name="ec3_review_decision_valid")]
