import hashlib,json
from dataclasses import dataclass
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.knowledge.legal_governance import evaluate_legal_obligation_applicability
from apps.knowledge.models import LegalObligationVersion
from ..models import LegalObligationApplicabilityAssessment,Obra,Organizacion

LEGAL_APPLICABILITY_EVALUATOR_VERSION="legal-applicability-1"

def _canonical(payload):return json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def _hash(payload):return hashlib.sha256(_canonical(payload).encode()).hexdigest()

def build_legal_applicability_context(organization,work=None):
    return {"organization":{"id":organization.id,"organizacion_id":organization.organizacion_id,"name":organization.nombre,"country":organization.pais,"preset":organization.preset,"rubro":organization.rubro,"region":organization.region,"comuna":organization.comuna},"work":None if work is None else {"id":work.id,"codigo_obra":work.codigo_obra,"name":work.nombre,"type":work.tipo_proyecto,"environmental_profile":work.perfil_ambiental,"region":work.region,"comuna":work.comuna,"state":work.estado}}

def _semantic_context(snapshot):
    org=snapshot["organization"];work=snapshot["work"]
    return {"organization":{key:org[key] for key in ("country","preset","rubro","region","comuna")},"work":None if work is None else {key:work[key] for key in ("type","environmental_profile","region","comuna","state")}}

def _criteria(version):return [{"order_index":item.order_index,"dimension":item.dimension,"operator":item.operator,"values":item.values,"note":item.note} for item in version.criteria.all().order_by("order_index")]
def _legal(version):return {"obligation_id":version.obligation_id,"obligation_code":version.obligation.code,"obligation_version_id":version.id,"version":version.version,"state":version.state,"modality":version.modality,"canonical_statement":version.canonical_statement,"applicability_level":version.applicability_level,"applicability_mode":version.applicability_mode,"source_provenance":version.source_provenance}
def _input_hash(evaluator,legal,criteria,context):return _hash({"evaluator_version":evaluator,"legal_snapshot":legal,"criteria_snapshot":criteria,"context_snapshot":context})
def _dto(version,criteria):return SimpleNamespace(applicability_mode=version.applicability_mode,applicability_level=version.applicability_level,criteria=[SimpleNamespace(**item) for item in criteria])

@dataclass
class BatchResult:
    active_obligations:int=0;created:int=0;superseded:int=0;unchanged:int=0;applicable:int=0;not_applicable:int=0;undetermined:int=0
    def data(self):return self.__dict__.copy()

def _evaluate(version,organization,work,user,result):
    context=build_legal_applicability_context(organization,work);criteria=_criteria(version);legal=_legal(version);input_hash=_input_hash(LEGAL_APPLICABILITY_EVALUATOR_VERSION,legal,criteria,context)
    latest=LegalObligationApplicabilityAssessment.objects.select_for_update().filter(organization=organization,work=work,obligation=version.obligation,is_latest=True).first()
    if latest and latest.input_hash==input_hash:assessment=latest;result.unchanged+=1
    else:
        revision=(LegalObligationApplicabilityAssessment.objects.filter(organization=organization,work=work,obligation=version.obligation).aggregate(value=Max("revision"))["value"] or 0)+1
        details=evaluate_legal_obligation_applicability(_dto(version,criteria),_semantic_context(context))
        if latest:LegalObligationApplicabilityAssessment.objects.filter(pk=latest.pk).update(is_latest=False);result.superseded+=1
        assessment=LegalObligationApplicabilityAssessment.objects.create(organization=organization,work=work,obligation=version.obligation,obligation_version=version,scope_level=version.applicability_level,evaluator_version=LEGAL_APPLICABILITY_EVALUATOR_VERSION,revision=revision,is_latest=True,result=details["result"],context_snapshot=context,criteria_snapshot=criteria,legal_snapshot=legal,evaluation_details=details,context_hash=_hash(_semantic_context(context)),input_hash=input_hash,evaluated_by=user,evaluated_at=timezone.now());result.created+=1
    setattr(result,assessment.result,getattr(result,assessment.result)+1)

@transaction.atomic
def evaluate_active_legal_obligations_for_organization(organization,user):
    organization=Organizacion.objects.select_for_update().get(pk=organization.pk);versions=LegalObligationVersion.objects.filter(state="active",applicability_level="organization").select_related("obligation").prefetch_related("criteria");result=BatchResult(active_obligations=versions.count())
    for version in versions:_evaluate(version,organization,None,user,result)
    return result

@transaction.atomic
def evaluate_active_legal_obligations_for_work(organization,work,user):
    organization=Organizacion.objects.select_for_update().get(pk=organization.pk);work=Obra.objects.select_for_update().get(pk=work.pk)
    if work.organizacion_id!=organization.id:raise ValidationError("La obra pertenece a otra organizacion.")
    versions=LegalObligationVersion.objects.filter(state="active").select_related("obligation").prefetch_related("criteria");result=BatchResult(active_obligations=versions.count())
    for version in versions:_evaluate(version,organization,None if version.applicability_level=="organization" else work,user,result)
    return result

def get_legal_assessment_freshness(assessment,organization,work=None):
    active=LegalObligationVersion.objects.filter(obligation=assessment.obligation,state="active").select_related("obligation").prefetch_related("criteria").first()
    if not active or active.id!=assessment.obligation_version_id:return "stale_legal_version"
    if assessment.evaluator_version!=LEGAL_APPLICABILITY_EVALUATOR_VERSION:return "stale_evaluator"
    context=build_legal_applicability_context(organization,work)
    if assessment.context_hash!=_hash(_semantic_context(context)):return "stale_context"
    if assessment.input_hash!=_input_hash(LEGAL_APPLICABILITY_EVALUATOR_VERSION,_legal(active),_criteria(active),context):return "stale_legal_contract"
    return "fresh"
