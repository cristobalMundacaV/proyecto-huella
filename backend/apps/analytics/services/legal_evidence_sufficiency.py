from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from apps.knowledge.legal_evidence import get_legal_evidence_requirement_freshness
from apps.knowledge.models import LegalEvidenceRequirement
from ..models import LegalEvidenceOperationalLink, LegalEvidenceRequirementSufficiencyReview, LegalObligationApplicabilityAssessment, Obra, Organizacion
from ..models.legal_evidence_sufficiency import sufficiency_basis_hash, sufficiency_review_hash
from ..permissions import Permission, require_tenant_permission, require_work_access
from .legal_applicability import get_legal_assessment_freshness
from .legal_evidence_mapping import get_legal_evidence_link_freshness, get_legal_evidence_mapping_freshness


def build_evidence_class_coverage(requirement_version, links):
    required = sorted(set(requirement_version.evidence_classes))
    linked = sorted({link.matched_evidence_class for link in links if link.matched_evidence_class in required})
    return {"required_classes": required, "linked_classes": linked, "unlinked_classes": sorted(set(required) - set(linked)), "link_count": len(links), "coverage_complete": set(required).issubset(linked)}


def _requirement_snapshot(version):
    return {"code": version.requirement.code, "version": version.version, "title": version.title, "requirement_statement": version.requirement_statement, "proof_objective": version.proof_objective, "evidence_mode": version.evidence_mode, "evidence_classes": version.evidence_classes, "accepted_evidence_descriptions": version.accepted_evidence_descriptions, "temporal_scope": version.temporal_scope, "legal_basis_snapshot": version.legal_basis_snapshot}


def _mapping_snapshot(mapping):
    return {"mapping_revision_id": mapping.id, "revision": mapping.revision, "mapping_hash": mapping.mapping_hash, "mapping_items": mapping.mapping_items}


def _applicability_snapshot(assessment):
    return {"assessment_id": assessment.id, "revision": assessment.revision, "result": assessment.result, "evaluator_version": assessment.evaluator_version, "input_hash": assessment.input_hash, "context_hash": assessment.context_hash, "evaluated_at": assessment.evaluated_at.isoformat()}


def _link_snapshot(link):
    evidence = link.evidence_snapshot
    return {"link_id": link.id, "matched_evidence_class": link.matched_evidence_class, "matched_evidence_type": link.matched_evidence_type, "evidence_id": link.evidence_id, "evidence_version_id": link.evidence_version_id, "evidence_version": evidence.get("evidence_version"), "checksum_sha256": evidence.get("checksum_sha256"), "documentary_state_at_link": evidence.get("documentary_state_at_link"), "evidence_name": evidence.get("evidence_name"), "document_date": evidence.get("document_date"), "link_freshness_at_review": "fresh"}


def _active_links(version, organization, work):
    return list(LegalEvidenceOperationalLink.objects.filter(organization=organization, work=work, requirement_version=version, status="linked").select_related("evidence", "evidence_version", "mapping_revision", "applicability_assessment", "requirement_version__requirement").order_by("id"))


def resolve_sufficiency_review_basis(requirement_code, organization, work=None):
    try:
        requirement = LegalEvidenceRequirement.objects.get(code=requirement_code)
    except LegalEvidenceRequirement.DoesNotExist as exc:
        raise ValidationError("No existe el requisito.") from exc
    version = requirement.versions.select_related("requirement__obligation", "legal_obligation_version__obligation").filter(state="active").first()
    if not version:
        raise ValidationError("No existe una version ACTIVE del requisito.")
    expected = "work" if work else "organization"
    if version.legal_obligation_version.applicability_level != expected:
        raise ValidationError("Scope del requisito incompatible.")
    if get_legal_evidence_requirement_freshness(version) != "fresh":
        raise ValidationError("Requirement stale.")
    mapping = version.operational_mapping_revisions.filter(is_latest=True).first()
    if not mapping:
        raise ValidationError("No existe mapping operacional.")
    if get_legal_evidence_mapping_freshness(mapping) != "fresh":
        raise ValidationError("Mapping stale.")
    assessment = LegalObligationApplicabilityAssessment.objects.filter(organization=organization, work=work, obligation=requirement.obligation, is_latest=True).first()
    if not assessment:
        raise ValidationError("Aplicabilidad no evaluada.")
    if assessment.result != "applicable":
        raise ValidationError(f"Aplicabilidad {assessment.result}.")
    if get_legal_assessment_freshness(assessment, organization, work) != "fresh":
        raise ValidationError("Assessment stale.")
    links = _active_links(version, organization, work)
    if any(get_legal_evidence_link_freshness(link) != "fresh" for link in links):
        raise ValidationError("Existen links stale.")
    requirement_snapshot = _requirement_snapshot(version)
    mapping_snapshot = _mapping_snapshot(mapping)
    applicability_snapshot = _applicability_snapshot(assessment)
    evidence_bundle_snapshot = {"evidence_mode": version.evidence_mode, "coverage": build_evidence_class_coverage(version, links), "links": [_link_snapshot(link) for link in links]}
    return requirement, version, mapping, assessment, links, requirement_snapshot, mapping_snapshot, applicability_snapshot, evidence_bundle_snapshot


def get_sufficiency_review_readiness(requirement_code, organization, work=None):
    try:
        data = resolve_sufficiency_review_basis(requirement_code, organization, work)
        return "ready", data
    except ValidationError as exc:
        message = " ".join(exc.messages).lower()
        states = (("no existe una version active", "requirement_stale"), ("requirement stale", "requirement_stale"), ("no existe mapping", "no_mapping"), ("mapping stale", "mapping_stale"), ("no evaluada", "not_evaluated"), ("not_applicable", "not_applicable"), ("undetermined", "undetermined"), ("assessment stale", "assessment_stale"), ("links stale", "stale_links"))
        return next((state for needle, state in states if needle in message), "requirement_stale"), None


@transaction.atomic
def review_legal_evidence_sufficiency(requirement_code, organization, work, decision, rationale, user, reviewer_note=""):
    require_tenant_permission(user, organization, Permission.COMPLIANCE_REVIEW)
    require_tenant_permission(user, organization, Permission.EVIDENCE_VIEW)
    require_work_access(user, organization, work)
    if decision not in LegalEvidenceRequirementSufficiencyReview.Decision.values:
        raise ValidationError("Decision invalida.")
    rationale = str(rationale).strip()
    reviewer_note = str(reviewer_note).strip()
    if not rationale:
        raise ValidationError("rationale es obligatorio.")
    if work:
        work = Obra.objects.select_for_update().get(pk=work.pk, organizacion=organization)
    else:
        organization = Organizacion.objects.select_for_update().get(pk=organization.pk)
    requirement, version, mapping, assessment, links, req_snapshot, map_snapshot, app_snapshot, bundle = resolve_sufficiency_review_basis(requirement_code, organization, work)
    if decision == "sufficient" and not links:
        raise ValidationError("No puede marcarse sufficient sin evidencia vinculada.")
    basis = sufficiency_basis_hash(req_snapshot, map_snapshot, app_snapshot, bundle)
    digest = sufficiency_review_hash(basis, decision, rationale, reviewer_note, user.id)
    latest = LegalEvidenceRequirementSufficiencyReview.objects.select_for_update().filter(organization=organization, work=work, requirement=requirement, is_latest=True).first()
    if latest and latest.review_hash == digest:
        return latest, False
    revision = (LegalEvidenceRequirementSufficiencyReview.objects.filter(organization=organization, work=work, requirement=requirement).aggregate(value=Max("revision"))["value"] or 0) + 1
    if latest:
        LegalEvidenceRequirementSufficiencyReview.objects.filter(pk=latest.pk).update(is_latest=False)
    review = LegalEvidenceRequirementSufficiencyReview.objects.create(organization=organization, work=work, scope_level="work" if work else "organization", requirement=requirement, requirement_version=version, mapping_revision=mapping, applicability_assessment=assessment, revision=revision, is_latest=True, decision=decision, rationale=rationale, reviewer_note=reviewer_note, requirement_snapshot=req_snapshot, mapping_snapshot=map_snapshot, applicability_snapshot=app_snapshot, evidence_bundle_snapshot=bundle, basis_hash=basis, review_hash=digest, reviewed_by=user)
    return review, True


def get_legal_evidence_sufficiency_review_freshness(review):
    active = review.requirement.versions.filter(state="active").first()
    if not active or active.pk != review.requirement_version_id or get_legal_evidence_requirement_freshness(active) != "fresh":
        return "stale_requirement"
    latest_mapping = active.operational_mapping_revisions.filter(is_latest=True).first()
    if not latest_mapping or latest_mapping.pk != review.mapping_revision_id or get_legal_evidence_mapping_freshness(latest_mapping) != "fresh":
        return "stale_mapping"
    assessment = LegalObligationApplicabilityAssessment.objects.filter(organization=review.organization, work=review.work, obligation=review.requirement.obligation, is_latest=True).first()
    if not assessment or assessment.pk != review.applicability_assessment_id or assessment.result != "applicable" or get_legal_assessment_freshness(assessment, review.organization, review.work) != "fresh":
        return "stale_applicability"
    reviewed_ids = [item.get("link_id") for item in review.evidence_bundle_snapshot.get("links", [])]
    reviewed_links = list(LegalEvidenceOperationalLink.objects.filter(pk__in=reviewed_ids).select_related("evidence", "evidence_version", "requirement_version__requirement", "mapping_revision", "applicability_assessment"))
    if len(reviewed_links) != len(set(reviewed_ids)) or any(get_legal_evidence_link_freshness(link) == "stale_evidence_version" for link in reviewed_links):
        return "stale_evidence_version"
    active_ids = list(LegalEvidenceOperationalLink.objects.filter(organization=review.organization, work=review.work, requirement_version=active, status="linked").order_by("id").values_list("id", flat=True))
    if active_ids != reviewed_ids:
        return "stale_link_set"
    expected_basis = sufficiency_basis_hash(review.requirement_snapshot, review.mapping_snapshot, review.applicability_snapshot, review.evidence_bundle_snapshot)
    expected_review = sufficiency_review_hash(expected_basis, review.decision, review.rationale, review.reviewer_note, review.reviewed_by_id)
    if expected_basis != review.basis_hash or expected_review != review.review_hash:
        return "stale_review_contract"
    return "fresh"
