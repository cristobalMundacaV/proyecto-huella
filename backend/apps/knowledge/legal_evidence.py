from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    LegalEvidenceRequirement,
    LegalEvidenceRequirementVersion,
    LegalObligation,
    LegalObligationVersion,
)


EDITABLE_EVIDENCE_FIELDS = {
    "title",
    "requirement_statement",
    "proof_objective",
    "evidence_mode",
    "evidence_classes",
    "accepted_evidence_descriptions",
    "temporal_scope",
    "notes",
}


def _superuser(user):
    if not user or not user.is_authenticated or not user.is_superuser:
        raise ValidationError("Solo un superusuario puede gobernar requisitos de evidencia.")


def _legal_basis(version):
    return {
        "obligation_id": version.obligation_id,
        "obligation_code": version.obligation.code,
        "obligation_version_id": version.id,
        "obligation_version": version.version,
        "state_at_creation": version.state,
        "modality": version.modality,
        "canonical_statement": version.canonical_statement,
        "applicability_level": version.applicability_level,
        "applicability_mode": version.applicability_mode,
        "source_provenance": version.source_provenance,
    }


def _validate_fields(version):
    for field in ("title", "requirement_statement", "proof_objective"):
        if not isinstance(getattr(version, field), str) or not getattr(version, field).strip():
            raise ValidationError(f"{field} es obligatorio.")
    if version.evidence_mode not in LegalEvidenceRequirementVersion.EvidenceMode.values:
        raise ValidationError("evidence_mode invalido.")
    classes = version.evidence_classes
    if not isinstance(classes, list) or not classes:
        raise ValidationError("evidence_classes debe contener al menos una clase.")
    if any(item not in LegalEvidenceRequirementVersion.EvidenceClass.values for item in classes):
        raise ValidationError("evidence_classes contiene una clase invalida.")
    descriptions = version.accepted_evidence_descriptions
    if not isinstance(descriptions, list) or not descriptions or any(not isinstance(item, str) or not item.strip() for item in descriptions):
        raise ValidationError("accepted_evidence_descriptions debe contener textos no vacios.")
    if version.temporal_scope not in LegalEvidenceRequirementVersion.TemporalScope.values:
        raise ValidationError("temporal_scope invalido.")


def _validate_contract(version):
    if version.requirement.obligation_id != version.legal_obligation_version.obligation_id:
        raise ValidationError("La obligacion del requisito no coincide con su base juridica.")
    expected = _legal_basis(version.legal_obligation_version)
    expected["state_at_creation"] = LegalObligationVersion.State.ACTIVE
    if version.legal_basis_snapshot != expected:
        raise ValidationError("La base juridica congelada es invalida.")
    _validate_fields(version)


def _new_version(requirement, legal_version, user, version_number, fields):
    if legal_version.state != LegalObligationVersion.State.ACTIVE:
        raise ValidationError("Solo una version juridica ACTIVE puede originar el requisito.")
    if requirement.obligation_id != legal_version.obligation_id:
        raise ValidationError("La version juridica pertenece a otra obligacion.")
    return LegalEvidenceRequirementVersion.objects.create(
        requirement=requirement,
        version=version_number,
        legal_obligation_version=legal_version,
        legal_basis_snapshot=_legal_basis(legal_version),
        created_by=user,
        **{field: fields.get(field, "" if field not in ("evidence_classes", "accepted_evidence_descriptions") else []) for field in EDITABLE_EVIDENCE_FIELDS},
    )


@transaction.atomic
def create_legal_evidence_requirement(obligation, legal_obligation_version, user, **fields):
    _superuser(user)
    obligation = LegalObligation.objects.select_for_update().get(pk=obligation.pk)
    legal_version = LegalObligationVersion.objects.select_for_update().select_related("obligation").get(pk=legal_obligation_version.pk)
    requirement = LegalEvidenceRequirement.objects.create(obligation=obligation)
    version = _new_version(requirement, legal_version, user, 1, fields)
    return requirement, version


@transaction.atomic
def create_legal_evidence_requirement_version(requirement, legal_obligation_version, user, **fields):
    _superuser(user)
    requirement = LegalEvidenceRequirement.objects.select_for_update().select_related("obligation").get(pk=requirement.pk)
    legal_version = LegalObligationVersion.objects.select_for_update().select_related("obligation").get(pk=legal_obligation_version.pk)
    number = (requirement.versions.aggregate(value=Max("version"))["value"] or 0) + 1
    return _new_version(requirement, legal_version, user, number, fields)


@transaction.atomic
def update_legal_evidence_requirement_draft(version, user, **fields):
    _superuser(user)
    version = LegalEvidenceRequirementVersion.objects.select_for_update().get(pk=version.pk)
    if version.state != version.State.DRAFT:
        raise ValidationError("Solo un draft puede editarse.")
    for field, value in fields.items():
        if field not in EDITABLE_EVIDENCE_FIELDS:
            raise ValidationError(f"Campo no editable: {field}.")
        setattr(version, field, value)
    version.save()
    return version


@transaction.atomic
def validate_legal_evidence_requirement_version(version, user):
    _superuser(user)
    version = LegalEvidenceRequirementVersion.objects.select_for_update().select_related("requirement__obligation", "legal_obligation_version__obligation").get(pk=version.pk)
    if version.state != version.State.DRAFT:
        raise ValidationError("Solo un draft puede validarse.")
    _validate_contract(version)
    LegalEvidenceRequirementVersion.objects.filter(pk=version.pk).update(state=version.State.VALIDATED, validated_by=user, validated_at=timezone.now())
    version.refresh_from_db()
    return version


@transaction.atomic
def activate_legal_evidence_requirement_version(version, user):
    _superuser(user)
    version = LegalEvidenceRequirementVersion.objects.select_for_update().select_related("requirement__obligation", "legal_obligation_version__obligation").get(pk=version.pk)
    if version.state != version.State.VALIDATED:
        raise ValidationError("Solo una version validada puede activarse.")
    _validate_contract(version)
    now = timezone.now()
    LegalEvidenceRequirementVersion.objects.select_for_update().filter(requirement=version.requirement, state=version.State.ACTIVE).exclude(pk=version.pk).update(state=version.State.OBSOLETE, obsoleted_at=now)
    LegalEvidenceRequirementVersion.objects.filter(pk=version.pk).update(state=version.State.ACTIVE, activated_by=user, activated_at=now)
    version.refresh_from_db()
    return version


@transaction.atomic
def obsolete_legal_evidence_requirement_version(version, user):
    _superuser(user)
    version = LegalEvidenceRequirementVersion.objects.select_for_update().get(pk=version.pk)
    if version.state != version.State.ACTIVE:
        raise ValidationError("Solo una version activa puede quedar obsoleta.")
    LegalEvidenceRequirementVersion.objects.filter(pk=version.pk).update(state=version.State.OBSOLETE, obsoleted_at=timezone.now())
    version.refresh_from_db()
    return version


def get_legal_evidence_requirement_freshness(version):
    active = LegalObligationVersion.objects.filter(obligation=version.requirement.obligation, state=LegalObligationVersion.State.ACTIVE).select_related("obligation").first()
    if not active or active.pk != version.legal_obligation_version_id:
        return "stale_legal_version"
    if version.legal_basis_snapshot != _legal_basis(active):
        return "stale_legal_contract"
    return "fresh"
