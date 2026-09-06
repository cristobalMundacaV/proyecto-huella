import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.knowledge.legal_evidence import get_legal_evidence_requirement_freshness
from apps.knowledge.models import LegalEvidenceRequirement, LegalEvidenceRequirementVersion
from ..models import EvidenciaObra, LegalEvidenceOperationalLink, LegalEvidenceOperationalMappingRevision, LegalObligationApplicabilityAssessment, Obra, Organizacion, VersionEvidencia
from .legal_applicability import get_legal_assessment_freshness


def _hash(value):return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _normalize_items(requirement_version, items):
    if not isinstance(items, list):raise ValidationError("mapping_items debe ser una lista.")
    valid_types=set(EvidenciaObra.TipoEvidencia.values);valid_classes=set(requirement_version.evidence_classes);seen=set();normalized=[]
    for raw in items:
        item={"evidence_class":str(raw.get("evidence_class","")).strip(),"evidence_type":str(raw.get("evidence_type","")).strip(),"note":str(raw.get("note","")).strip()}
        pair=(item["evidence_class"],item["evidence_type"])
        if item["evidence_class"] not in valid_classes:raise ValidationError("Clase de evidencia no gobernada por el requisito.")
        if item["evidence_type"] not in valid_types:raise ValidationError("Tipo operacional de evidencia invalido.")
        if pair in seen:raise ValidationError("Mapping duplicado.")
        seen.add(pair);normalized.append(item)
    if {item["evidence_class"] for item in normalized} != valid_classes:raise ValidationError("El mapping no cubre todas las clases del requisito.")
    return sorted(normalized,key=lambda item:(item["evidence_class"],item["evidence_type"],item["note"]))


@transaction.atomic
def publish_legal_evidence_operational_mapping(requirement_version, items, user, note=""):
    if not user.is_authenticated or not user.is_superuser:raise ValidationError("Solo superuser puede publicar mappings.")
    version=LegalEvidenceRequirementVersion.objects.select_for_update().select_related("requirement__obligation","legal_obligation_version__obligation").get(pk=requirement_version.pk)
    if version.state != version.State.ACTIVE or get_legal_evidence_requirement_freshness(version)!="fresh":raise ValidationError("El requisito debe estar ACTIVE y fresh.")
    normalized=_normalize_items(version,items);digest=_hash(normalized)
    latest=LegalEvidenceOperationalMappingRevision.objects.select_for_update().filter(requirement_version=version,is_latest=True).first()
    if latest and latest.mapping_hash==digest:return latest,False
    revision=(LegalEvidenceOperationalMappingRevision.objects.filter(requirement_version=version).aggregate(v=Max("revision"))["v"] or 0)+1
    if latest:LegalEvidenceOperationalMappingRevision.objects.filter(pk=latest.pk).update(is_latest=False)
    return LegalEvidenceOperationalMappingRevision.objects.create(requirement_version=version,revision=revision,is_latest=True,mapping_items=normalized,mapping_hash=digest,note=note,created_by=user),True


def get_legal_evidence_mapping_freshness(mapping):
    active=mapping.requirement_version.requirement.versions.filter(state="active").first()
    if not active or active.pk!=mapping.requirement_version_id:return "stale_requirement_version"
    requirement_state=get_legal_evidence_requirement_freshness(mapping.requirement_version)
    if requirement_state!="fresh":return requirement_state
    if mapping.mapping_hash!=_hash(mapping.mapping_items):return "stale_mapping_contract"
    return "fresh"


def _resolve(requirement_code, organization, work):
    requirement=LegalEvidenceRequirement.objects.get(code=requirement_code)
    version=requirement.versions.select_related("requirement__obligation","legal_obligation_version__obligation").filter(state="active").get()
    expected="work" if work else "organization"
    if version.legal_obligation_version.applicability_level!=expected:raise ValidationError("Scope del requisito incompatible.")
    if get_legal_evidence_requirement_freshness(version)!="fresh":raise ValidationError("Requirement stale.")
    mapping=version.operational_mapping_revisions.filter(is_latest=True).first()
    if not mapping or get_legal_evidence_mapping_freshness(mapping)!="fresh":raise ValidationError("No existe mapping operacional fresh.")
    assessment=LegalObligationApplicabilityAssessment.objects.filter(organization=organization,work=work,obligation=version.requirement.obligation,is_latest=True).first()
    if not assessment:raise ValidationError("Aplicabilidad no evaluada.")
    if assessment.result!="applicable" or get_legal_assessment_freshness(assessment,organization,work)!="fresh":raise ValidationError("La aplicabilidad no esta applicable y fresh.")
    return version,mapping,assessment


def list_operational_evidence_candidates(requirement_code, organization, work=None):
    version,mapping,_=_resolve(requirement_code,organization,work);by_type={}
    for item in mapping.mapping_items:by_type.setdefault(item["evidence_type"],[]).append(item["evidence_class"])
    evidence=EvidenciaObra.objects.filter(organizacion=organization,obra=work,tipo_evidencia__in=by_type).order_by("id")
    result=[]
    for item in evidence:
        latest=item.versiones.order_by("-version").first()
        result.append({"evidence_id":item.id,"evidence_type":item.tipo_evidencia,"documentary_state":item.estado_documental,"matched_classes":sorted(by_type[item.tipo_evidencia]),"latest_version":None if not latest else {"id":latest.id,"version":latest.version,"checksum_sha256":latest.checksum_sha256},"linkable":bool(latest),"reason":None if latest else "unversioned_evidence"})
    return result


@transaction.atomic
def create_operational_evidence_link(requirement_code, organization, work, evidence, evidence_version, user, evidence_class=None, note=""):
    if work:work=Obra.objects.select_for_update().get(pk=work.pk)
    else:organization=Organizacion.objects.select_for_update().get(pk=organization.pk)
    version,mapping,assessment=_resolve(requirement_code,organization,work)
    evidence=EvidenciaObra.objects.get(pk=evidence.pk,organizacion=organization,obra=work);evidence_version=VersionEvidencia.objects.get(pk=evidence_version.pk,evidencia=evidence,organizacion=organization)
    classes=sorted({i["evidence_class"] for i in mapping.mapping_items if i["evidence_type"]==evidence.tipo_evidencia})
    if not classes:raise ValidationError("Tipo de evidencia no compatible.")
    if evidence_class is None:
        if len(classes)!=1:raise ValidationError("evidence_class es obligatorio por ambiguedad.")
        evidence_class=classes[0]
    if evidence_class not in classes:raise ValidationError("evidence_class no compatible.")
    existing=LegalEvidenceOperationalLink.objects.filter(organization=organization,work=work,requirement_version=version,evidence_version=evidence_version,matched_evidence_class=evidence_class,status="linked").first()
    if existing:return existing,False
    req={"code":version.requirement.code,"version":version.version,"title":version.title,"requirement_statement":version.requirement_statement,"proof_objective":version.proof_objective,"evidence_mode":version.evidence_mode,"evidence_classes":version.evidence_classes,"accepted_evidence_descriptions":version.accepted_evidence_descriptions,"temporal_scope":version.temporal_scope,"legal_basis_snapshot":version.legal_basis_snapshot}
    ms={"mapping_revision_id":mapping.id,"revision":mapping.revision,"mapping_hash":mapping.mapping_hash,"mapping_items":mapping.mapping_items,"matched_evidence_class":evidence_class,"matched_evidence_type":evidence.tipo_evidencia}
    aps={"assessment_id":assessment.id,"revision":assessment.revision,"result":assessment.result,"evaluator_version":assessment.evaluator_version,"input_hash":assessment.input_hash,"context_hash":assessment.context_hash,"evaluated_at":assessment.evaluated_at.isoformat()}
    es={"evidence_id":evidence.id,"evidence_version_id":evidence_version.id,"evidence_version":evidence_version.version,"checksum_sha256":evidence_version.checksum_sha256,"evidence_type":evidence.tipo_evidencia,"documentary_state_at_link":evidence.estado_documental,"evidence_name":evidence.nombre,"document_date":evidence.fecha_documento.isoformat() if evidence.fecha_documento else None,"capture_method":evidence.metodo_captura,"evidence_version_processing_state":evidence_version.estado_procesamiento}
    return LegalEvidenceOperationalLink.objects.create(organization=organization,work=work,requirement_version=version,mapping_revision=mapping,applicability_assessment=assessment,evidence=evidence,evidence_version=evidence_version,matched_evidence_class=evidence_class,matched_evidence_type=evidence.tipo_evidencia,note=note,requirement_snapshot=req,mapping_snapshot=ms,applicability_snapshot=aps,evidence_snapshot=es,linked_by=user),True


@transaction.atomic
def withdraw_legal_evidence_link(link,user,reason):
    if not str(reason).strip():raise ValidationError("withdrawal_reason es obligatorio.")
    link=LegalEvidenceOperationalLink.objects.select_for_update().get(pk=link.pk)
    if link.status!="linked":raise ValidationError("Solo un link activo puede retirarse.")
    LegalEvidenceOperationalLink.objects.filter(pk=link.pk).update(status="withdrawn",withdrawn_by=user,withdrawn_at=timezone.now(),withdrawal_reason=str(reason).strip());link.refresh_from_db();return link


def get_legal_evidence_link_freshness(link):
    active=link.requirement_version.requirement.versions.filter(state="active").first()
    if not active or active.pk!=link.requirement_version_id:return "stale_requirement"
    latest=link.requirement_version.operational_mapping_revisions.filter(is_latest=True).first()
    if not latest or latest.pk!=link.mapping_revision_id or get_legal_evidence_mapping_freshness(latest)!="fresh":return "stale_mapping"
    current=LegalObligationApplicabilityAssessment.objects.filter(organization=link.organization,work=link.work,obligation=link.requirement_version.requirement.obligation,is_latest=True).first()
    if not current or current.pk!=link.applicability_assessment_id or current.result!="applicable" or get_legal_assessment_freshness(current,link.organization,link.work)!="fresh":return "stale_applicability"
    if link.evidence.versiones.order_by("-version").values_list("pk",flat=True).first()!=link.evidence_version_id:return "stale_evidence_version"
    return "fresh"
