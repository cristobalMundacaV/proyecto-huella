from django.core.exceptions import ValidationError
from django.db import models


class ImmutableLegalEvidenceOperationalQuerySet(models.QuerySet):
    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Use el servicio gobernado de evidencia legal operacional.")

    def delete(self):
        raise ValidationError("La historia de evidencia legal operacional es inmutable.")


class LegalEvidenceOperationalMappingRevision(models.Model):
    objects = ImmutableLegalEvidenceOperationalQuerySet.as_manager()
    requirement_version = models.ForeignKey("knowledge.LegalEvidenceRequirementVersion", on_delete=models.PROTECT, related_name="operational_mapping_revisions")
    revision = models.PositiveIntegerField()
    is_latest = models.BooleanField(default=True, db_index=True)
    mapping_items = models.JSONField()
    mapping_hash = models.CharField(max_length=64)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="created_legal_evidence_mappings")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requirement_version", "revision"], name="analytics_legal_evidence_mapping_revision"),
            models.UniqueConstraint(fields=["requirement_version"], condition=models.Q(is_latest=True), name="analytics_legal_evidence_mapping_latest"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:raise ValidationError("El mapping operacional es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):raise ValidationError("El mapping operacional es inmutable.")


class LegalEvidenceOperationalLink(models.Model):
    class Status(models.TextChoices):
        LINKED = "linked", "Linked"
        WITHDRAWN = "withdrawn", "Withdrawn"

    objects = ImmutableLegalEvidenceOperationalQuerySet.as_manager()
    organization = models.ForeignKey("analytics.Organizacion", on_delete=models.PROTECT, related_name="legal_evidence_links")
    work = models.ForeignKey("analytics.Obra", on_delete=models.PROTECT, null=True, blank=True, related_name="legal_evidence_links")
    requirement_version = models.ForeignKey("knowledge.LegalEvidenceRequirementVersion", on_delete=models.PROTECT, related_name="operational_links")
    mapping_revision = models.ForeignKey(LegalEvidenceOperationalMappingRevision, on_delete=models.PROTECT, related_name="links")
    applicability_assessment = models.ForeignKey("analytics.LegalObligationApplicabilityAssessment", on_delete=models.PROTECT, related_name="evidence_links")
    evidence = models.ForeignKey("analytics.EvidenciaObra", on_delete=models.PROTECT, related_name="legal_requirement_links")
    evidence_version = models.ForeignKey("analytics.VersionEvidencia", on_delete=models.PROTECT, related_name="legal_requirement_links")
    matched_evidence_class = models.CharField(max_length=40)
    matched_evidence_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LINKED, db_index=True)
    note = models.TextField(blank=True)
    requirement_snapshot = models.JSONField()
    mapping_snapshot = models.JSONField()
    applicability_snapshot = models.JSONField()
    evidence_snapshot = models.JSONField()
    linked_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="created_legal_evidence_links")
    linked_at = models.DateTimeField(auto_now_add=True)
    withdrawn_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, null=True, blank=True, related_name="withdrawn_legal_evidence_links")
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "requirement_version", "evidence_version", "matched_evidence_class"], condition=models.Q(status="linked", work__isnull=True), name="analytics_active_legal_evidence_org_link"),
            models.UniqueConstraint(fields=["work", "requirement_version", "evidence_version", "matched_evidence_class"], condition=models.Q(status="linked", work__isnull=False), name="analytics_active_legal_evidence_work_link"),
        ]
        ordering = ["-linked_at"]

    def save(self, *args, **kwargs):
        if self.pk:raise ValidationError("El vinculo de evidencia legal es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):raise ValidationError("El vinculo de evidencia legal es inmutable.")
