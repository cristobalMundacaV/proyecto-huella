import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import models


def canonical_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def sufficiency_basis_hash(requirement_snapshot, mapping_snapshot, applicability_snapshot, evidence_bundle_snapshot):
    return canonical_hash({"requirement_snapshot": requirement_snapshot, "mapping_snapshot": mapping_snapshot, "applicability_snapshot": applicability_snapshot, "evidence_bundle_snapshot": evidence_bundle_snapshot})


def sufficiency_review_hash(basis_hash, decision, rationale, reviewer_note, reviewed_by_id):
    return canonical_hash({"basis_hash": basis_hash, "decision": decision, "rationale": str(rationale).strip(), "reviewer_note": str(reviewer_note).strip(), "reviewed_by_id": reviewed_by_id})


class ImmutableSufficiencyReviewQuerySet(models.QuerySet):
    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Use el servicio de revision de suficiencia.")

    def delete(self):
        raise ValidationError("La historia de revisiones de suficiencia es inmutable.")


class LegalEvidenceRequirementSufficiencyReview(models.Model):
    class Scope(models.TextChoices):
        ORGANIZATION = "organization", "Organization"
        WORK = "work", "Work"

    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        SUFFICIENT = "sufficient", "Sufficient"
        INSUFFICIENT = "insufficient", "Insufficient"

    objects = ImmutableSufficiencyReviewQuerySet.as_manager()
    organization = models.ForeignKey("analytics.Organizacion", on_delete=models.PROTECT, related_name="legal_evidence_sufficiency_reviews")
    work = models.ForeignKey("analytics.Obra", on_delete=models.PROTECT, null=True, blank=True, related_name="legal_evidence_sufficiency_reviews")
    scope_level = models.CharField(max_length=20, choices=Scope.choices)
    requirement = models.ForeignKey("knowledge.LegalEvidenceRequirement", on_delete=models.PROTECT, related_name="sufficiency_reviews")
    requirement_version = models.ForeignKey("knowledge.LegalEvidenceRequirementVersion", on_delete=models.PROTECT, related_name="sufficiency_reviews")
    mapping_revision = models.ForeignKey("analytics.LegalEvidenceOperationalMappingRevision", on_delete=models.PROTECT, related_name="sufficiency_reviews")
    applicability_assessment = models.ForeignKey("analytics.LegalObligationApplicabilityAssessment", on_delete=models.PROTECT, related_name="evidence_sufficiency_reviews")
    revision = models.PositiveIntegerField()
    is_latest = models.BooleanField(default=True, db_index=True)
    decision = models.CharField(max_length=20, choices=Decision.choices)
    rationale = models.TextField()
    reviewer_note = models.TextField(blank=True)
    requirement_snapshot = models.JSONField()
    mapping_snapshot = models.JSONField()
    applicability_snapshot = models.JSONField()
    evidence_bundle_snapshot = models.JSONField()
    basis_hash = models.CharField(max_length=64)
    review_hash = models.CharField(max_length=64)
    reviewed_by = models.ForeignKey("auth.User", on_delete=models.PROTECT, related_name="legal_evidence_sufficiency_reviews")
    reviewed_at = models.DateTimeField()

    class Meta:
        ordering = ["-revision"]
        constraints = [
            models.CheckConstraint(condition=(models.Q(scope_level="organization", work__isnull=True) | models.Q(scope_level="work", work__isnull=False)), name="analytics_sufficiency_scope_work"),
            models.UniqueConstraint(fields=["organization", "requirement", "revision"], condition=models.Q(work__isnull=True), name="analytics_sufficiency_org_revision"),
            models.UniqueConstraint(fields=["work", "requirement", "revision"], condition=models.Q(work__isnull=False), name="analytics_sufficiency_work_revision"),
            models.UniqueConstraint(fields=["organization", "requirement"], condition=models.Q(work__isnull=True, is_latest=True), name="analytics_sufficiency_org_latest"),
            models.UniqueConstraint(fields=["work", "requirement"], condition=models.Q(work__isnull=False, is_latest=True), name="analytics_sufficiency_work_latest"),
        ]

    def clean(self):
        from apps.knowledge.legal_evidence import get_legal_evidence_requirement_freshness
        from ..services.legal_applicability import get_legal_assessment_freshness
        from ..services.legal_evidence_mapping import get_legal_evidence_link_freshness, get_legal_evidence_mapping_freshness

        if self.decision not in self.Decision.values or not str(self.rationale).strip():
            raise ValidationError("Decision valida y rationale son obligatorios.")
        if self.requirement_version.requirement_id != self.requirement_id:
            raise ValidationError("Requirement/version inconsistente.")
        if self.mapping_revision.requirement_version_id != self.requirement_version_id:
            raise ValidationError("Mapping/version inconsistente.")
        assessment = self.applicability_assessment
        if assessment.organization_id != self.organization_id or assessment.obligation_id != self.requirement.obligation_id:
            raise ValidationError("Assessment inconsistente.")
        if self.requirement_version.state != "active" or get_legal_evidence_requirement_freshness(self.requirement_version) != "fresh":
            raise ValidationError("Requirement no publicable.")
        if not self.mapping_revision.is_latest or get_legal_evidence_mapping_freshness(self.mapping_revision) != "fresh":
            raise ValidationError("Mapping no publicable.")
        if not assessment.is_latest or assessment.result != "applicable" or get_legal_assessment_freshness(assessment, self.organization, self.work) != "fresh":
            raise ValidationError("Assessment no publicable.")
        level = self.requirement_version.legal_obligation_version.applicability_level
        if level != self.scope_level:
            raise ValidationError("Scope inconsistente.")
        if level == self.Scope.ORGANIZATION and (self.work_id or assessment.work_id):
            raise ValidationError("Scope organizacional inconsistente.")
        if level == self.Scope.WORK and (not self.work_id or self.work.organizacion_id != self.organization_id or assessment.work_id != self.work_id):
            raise ValidationError("Scope de obra inconsistente.")
        expected_revision = (type(self).objects.filter(organization_id=self.organization_id, work_id=self.work_id, requirement_id=self.requirement_id).aggregate(value=models.Max("revision"))["value"] or 0) + 1
        if self.revision != expected_revision or not self.is_latest:
            raise ValidationError("Revision no secuencial o latest invalido.")
        expected_requirement = {"code": self.requirement.code, "version": self.requirement_version.version, "title": self.requirement_version.title, "requirement_statement": self.requirement_version.requirement_statement, "proof_objective": self.requirement_version.proof_objective, "evidence_mode": self.requirement_version.evidence_mode, "evidence_classes": self.requirement_version.evidence_classes, "accepted_evidence_descriptions": self.requirement_version.accepted_evidence_descriptions, "temporal_scope": self.requirement_version.temporal_scope, "legal_basis_snapshot": self.requirement_version.legal_basis_snapshot}
        expected_mapping = {"mapping_revision_id": self.mapping_revision_id, "revision": self.mapping_revision.revision, "mapping_hash": self.mapping_revision.mapping_hash, "mapping_items": self.mapping_revision.mapping_items}
        expected_applicability = {"assessment_id": assessment.id, "revision": assessment.revision, "result": assessment.result, "evaluator_version": assessment.evaluator_version, "input_hash": assessment.input_hash, "context_hash": assessment.context_hash, "evaluated_at": assessment.evaluated_at.isoformat()}
        if self.requirement_snapshot != expected_requirement or self.mapping_snapshot != expected_mapping or self.applicability_snapshot != expected_applicability:
            raise ValidationError("Snapshot de revision adulterado.")
        checks = (
            (self.requirement_snapshot, "code", self.requirement.code),
            (self.requirement_snapshot, "version", self.requirement_version.version),
            (self.mapping_snapshot, "mapping_revision_id", self.mapping_revision_id),
            (self.mapping_snapshot, "revision", self.mapping_revision.revision),
            (self.mapping_snapshot, "mapping_hash", self.mapping_revision.mapping_hash),
            (self.applicability_snapshot, "assessment_id", assessment.id),
            (self.applicability_snapshot, "revision", assessment.revision),
            (self.applicability_snapshot, "input_hash", assessment.input_hash),
        )
        if any(snapshot.get(key) != value for snapshot, key, value in checks):
            raise ValidationError("Snapshot de revision adulterado.")
        links = self.evidence_bundle_snapshot.get("links") if isinstance(self.evidence_bundle_snapshot, dict) else None
        if not isinstance(links, list):
            raise ValidationError("Evidence bundle invalido.")
        from .legal_evidence_mapping import LegalEvidenceOperationalLink
        ids = [item.get("link_id") for item in links]
        linked = {item.id: item for item in LegalEvidenceOperationalLink.objects.filter(pk__in=ids)}
        if len(ids) != len(set(ids)) or set(ids) != set(linked):
            raise ValidationError("Links de evidence bundle invalidos.")
        for item in links:
            link = linked[item["link_id"]]
            if link.status != "linked" or get_legal_evidence_link_freshness(link) != "fresh" or link.organization_id != self.organization_id or link.work_id != self.work_id or link.requirement_version_id != self.requirement_version_id:
                raise ValidationError("Link fuera del scope de revision.")
            expected = {"link_id": link.id, "matched_evidence_class": link.matched_evidence_class, "matched_evidence_type": link.matched_evidence_type, "evidence_id": link.evidence_id, "evidence_version_id": link.evidence_version_id, "evidence_version": link.evidence_snapshot.get("evidence_version"), "checksum_sha256": link.evidence_snapshot.get("checksum_sha256"), "documentary_state_at_link": link.evidence_snapshot.get("documentary_state_at_link"), "evidence_name": link.evidence_snapshot.get("evidence_name"), "document_date": link.evidence_snapshot.get("document_date"), "link_freshness_at_review": "fresh"}
            if item != expected:
                raise ValidationError("Snapshot de link adulterado.")
        required = sorted(set(self.requirement_version.evidence_classes))
        linked_classes = sorted({item["matched_evidence_class"] for item in links if item["matched_evidence_class"] in required})
        expected_bundle = {"evidence_mode": self.requirement_version.evidence_mode, "coverage": {"required_classes": required, "linked_classes": linked_classes, "unlinked_classes": sorted(set(required) - set(linked_classes)), "link_count": len(links), "coverage_complete": set(required).issubset(linked_classes)}, "links": links}
        if self.evidence_bundle_snapshot != expected_bundle:
            raise ValidationError("Evidence bundle adulterado.")
        expected_basis = sufficiency_basis_hash(self.requirement_snapshot, self.mapping_snapshot, self.applicability_snapshot, self.evidence_bundle_snapshot)
        expected_review = sufficiency_review_hash(expected_basis, self.decision, self.rationale, self.reviewer_note, self.reviewed_by_id)
        if self.basis_hash != expected_basis or self.review_hash != expected_review:
            raise ValidationError("Hash de revision invalido.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("La revision de suficiencia es inmutable.")
        self.rationale = str(self.rationale).strip()
        self.reviewer_note = str(self.reviewer_note).strip()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("La revision de suficiencia es inmutable.")
