from django.core.exceptions import ValidationError
from django.db import models
import hashlib
import json


def normalized_operational_mapping(requirement_version, items):
    from .provenance import EvidenciaObra
    if not isinstance(items, list):raise ValidationError("mapping_items debe ser una lista.")
    valid_classes=set(requirement_version.evidence_classes);valid_types=set(EvidenciaObra.TipoEvidencia.values);seen=set();result=[]
    for raw in items:
        if not isinstance(raw,dict):raise ValidationError("Item de mapping invalido.")
        item={"evidence_class":str(raw.get("evidence_class","")).strip(),"evidence_type":str(raw.get("evidence_type","")).strip(),"note":str(raw.get("note","")).strip()};pair=(item["evidence_class"],item["evidence_type"])
        if item["evidence_class"] not in valid_classes:raise ValidationError("Clase de evidencia invalida.")
        if item["evidence_type"] not in valid_types:raise ValidationError("Tipo de evidencia invalido.")
        if pair in seen:raise ValidationError("Mapping duplicado.")
        seen.add(pair);result.append(item)
    if {item["evidence_class"] for item in result}!=valid_classes:raise ValidationError("Cobertura incompleta.")
    return sorted(result,key=lambda item:(item["evidence_class"],item["evidence_type"],item["note"]))


def operational_mapping_hash(items):return hashlib.sha256(json.dumps(items,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()


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
        from apps.knowledge.legal_evidence import get_legal_evidence_requirement_freshness
        if self.requirement_version.state!="active" or get_legal_evidence_requirement_freshness(self.requirement_version)!="fresh":raise ValidationError("Requirement debe estar ACTIVE y fresh.")
        normalized=normalized_operational_mapping(self.requirement_version,self.mapping_items)
        if self.mapping_items!=normalized or self.mapping_hash!=operational_mapping_hash(normalized):raise ValidationError("Mapping no normalizado o hash invalido.")
        expected=(LegalEvidenceOperationalMappingRevision.objects.filter(requirement_version=self.requirement_version).aggregate(v=models.Max("revision"))["v"] or 0)+1
        if self.revision!=expected:raise ValidationError("Revision de mapping no secuencial.")
        if not self.created_by.is_superuser:raise ValidationError("Solo superuser puede crear mappings.")
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
        from apps.knowledge.legal_evidence import get_legal_evidence_requirement_freshness
        from ..services.legal_applicability import get_legal_assessment_freshness
        from ..services.legal_evidence_mapping import get_legal_evidence_mapping_freshness
        if self.status!="linked" or self.withdrawn_by_id or self.withdrawn_at or self.withdrawal_reason:raise ValidationError("Un link nuevo debe originarse linked y sin retiro.")
        requirement=self.requirement_version
        if requirement.state!="active" or get_legal_evidence_requirement_freshness(requirement)!="fresh":raise ValidationError("Requirement no publicable.")
        if self.mapping_revision.requirement_version_id!=requirement.id or not self.mapping_revision.is_latest or get_legal_evidence_mapping_freshness(self.mapping_revision)!="fresh":raise ValidationError("Mapping inconsistente.")
        assessment=self.applicability_assessment
        if assessment.organization_id!=self.organization_id or assessment.obligation_id!=requirement.requirement.obligation_id or not assessment.is_latest or assessment.result!="applicable" or get_legal_assessment_freshness(assessment,self.organization,self.work)!="fresh":raise ValidationError("Assessment inconsistente.")
        if self.evidence.organizacion_id!=self.organization_id or self.evidence_version.evidencia_id!=self.evidence_id or self.evidence_version.organizacion_id!=self.organization_id:raise ValidationError("Evidencia o version inconsistente.")
        level=requirement.legal_obligation_version.applicability_level
        if level=="organization" and (self.work_id or assessment.work_id or self.evidence.obra_id):raise ValidationError("Scope organizacional inconsistente.")
        if level=="work" and (not self.work_id or self.work.organizacion_id!=self.organization_id or assessment.work_id!=self.work_id or self.evidence.obra_id!=self.work_id):raise ValidationError("Scope de obra inconsistente.")
        pair={"evidence_class":self.matched_evidence_class,"evidence_type":self.matched_evidence_type}
        if self.matched_evidence_type!=self.evidence.tipo_evidencia or not any(all(item.get(k)==v for k,v in pair.items()) for item in self.mapping_revision.mapping_items):raise ValidationError("Par clase/tipo no mapeado.")
        checks=((self.requirement_snapshot,"code",requirement.requirement.code),(self.requirement_snapshot,"version",requirement.version),(self.mapping_snapshot,"mapping_revision_id",self.mapping_revision_id),(self.mapping_snapshot,"revision",self.mapping_revision.revision),(self.mapping_snapshot,"mapping_hash",self.mapping_revision.mapping_hash),(self.applicability_snapshot,"assessment_id",assessment.id),(self.applicability_snapshot,"revision",assessment.revision),(self.applicability_snapshot,"input_hash",assessment.input_hash),(self.evidence_snapshot,"evidence_id",self.evidence_id),(self.evidence_snapshot,"evidence_version_id",self.evidence_version_id),(self.evidence_snapshot,"evidence_version",self.evidence_version.version),(self.evidence_snapshot,"checksum_sha256",self.evidence_version.checksum_sha256),(self.evidence_snapshot,"evidence_type",self.evidence.tipo_evidencia))
        if any(snapshot.get(key)!=value for snapshot,key,value in checks):raise ValidationError("Snapshot operacional adulterado.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):raise ValidationError("El vinculo de evidencia legal es inmutable.")
