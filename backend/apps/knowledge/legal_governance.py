from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .bcn_obligations import BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION, current_bcn_norm_facts
from .bcn_text import BCN_LEGAL_XML_PARSER_VERSION, get_current_bcn_legal_text
from .legal_contracts import DIMENSIONS,validate_criterion,validate_semantic_fields
from .models import BcnLegalObligationCandidate, BcnLegalObligationCandidateReview, LegalObligation, LegalObligationApplicabilityCriterion, LegalObligationVersion

EDITABLE=("modality","canonical_statement","subject_text","action_text","object_text","condition_text","temporal_text","applicability_level","applicability_mode")

def _superuser(user):
    if not user or not user.is_superuser:raise ValidationError("Solo un superusuario puede gobernar obligaciones juridicas.")

def ensure_current_obligation_candidate(candidate):
    run=candidate.extraction_run;article=run.article;artifact=article.parse.source_document.artifact
    if run.extractor_version!=BCN_LEGAL_OBLIGATION_EXTRACTOR_VERSION or run.status!="success" or run.source_text_hash!=article.text_hash:raise ValidationError("El candidato no pertenece al extractor current.")
    fact=artifact.parent_record.current_snapshot.bcn_legal_norm_fact
    if not current_bcn_norm_facts().filter(pk=fact.pk).exists():raise ValidationError("El candidato no pertenece al corpus juridico current.")
    try:current_artifact,current_parse=get_current_bcn_legal_text(fact)
    except Exception as exc:raise ValidationError("El candidato es historico o su texto current no esta disponible.") from exc
    if current_artifact.pk!=artifact.pk or current_parse.pk!=article.parse_id:raise ValidationError("El candidato es historico.")
    return candidate

def _provenance(candidate):
    article=candidate.extraction_run.article;parse=article.parse;artifact=parse.source_document.artifact;fact=artifact.parent_record.current_snapshot.bcn_legal_norm_fact
    return {"source":"BCN/LeyChile","candidate_id":candidate.id,"candidate_key":candidate.candidate_key,"extractor_version":candidate.extraction_run.extractor_version,"modality_hint":candidate.modality_hint,"norm_id":fact.id,"norm_number":fact.number,"norm_title":fact.title,"norm_uri":fact.norm_uri,"version_uri":fact.latest_version_uri,"artifact_id":artifact.id,"artifact_sha256":artifact.content_sha256,"parser_version":parse.parser_version,"article_id":article.id,"article_key":article.article_key,"article_number":article.article_number,"article_text_hash":article.text_hash,"source_quote":candidate.source_quote,"source_start":candidate.source_start,"source_end":candidate.source_end,"trigger_text":candidate.trigger_text,"trigger_start":candidate.trigger_start,"trigger_end":candidate.trigger_end}

def _create_criteria(version,criteria):
    clean=[validate_criterion(item,version.applicability_level) for item in criteria]
    for index,item in enumerate(clean,1):LegalObligationApplicabilityCriterion.objects.create(obligation_version=version,order_index=index,**item)

@transaction.atomic
def reject_legal_candidate(candidate,reviewer,note=""):
    _superuser(reviewer);candidate=BcnLegalObligationCandidate.objects.select_for_update().get(pk=candidate.pk);ensure_current_obligation_candidate(candidate)
    if hasattr(candidate,"review"):raise ValidationError("El candidato ya fue revisado.")
    return BcnLegalObligationCandidateReview.objects.create(candidate=candidate,decision="rejected",reviewer=reviewer,reviewed_at=timezone.now(),note=note)

@transaction.atomic
def promote_legal_candidate(candidate,reviewer,mode,target_obligation=None,criteria=None,**fields):
    _superuser(reviewer);candidate=BcnLegalObligationCandidate.objects.select_for_update().get(pk=candidate.pk);ensure_current_obligation_candidate(candidate)
    if hasattr(candidate,"review"):raise ValidationError("El candidato ya fue revisado.")
    if mode=="create_obligation":
        if target_obligation is not None:raise ValidationError("create_obligation no acepta target.")
        obligation=LegalObligation.objects.create()
    elif mode=="new_version":
        if target_obligation is None:raise ValidationError("new_version exige target_obligation.")
        obligation=LegalObligation.objects.select_for_update().get(pk=target_obligation.pk)
    else:raise ValidationError("Modo de promocion invalido.")
    number=(obligation.versions.aggregate(value=Max("version"))["value"] or 0)+1
    payload={key:fields.get(key,"") for key in EDITABLE};payload.setdefault("modality",candidate.modality_hint);payload["modality"]=fields.get("modality") or candidate.modality_hint;payload["applicability_level"]=fields.get("applicability_level") or "work";payload["applicability_mode"]=fields.get("applicability_mode") or "pending"
    validate_semantic_fields(payload["modality"],payload["applicability_level"],payload["applicability_mode"])
    version=LegalObligationVersion.objects.create(obligation=obligation,version=number,state="draft",source_candidate=candidate,source_provenance=_provenance(candidate),created_by=reviewer,**payload)
    _create_criteria(version,criteria or [])
    review=BcnLegalObligationCandidateReview.objects.create(candidate=candidate,decision="approved",reviewer=reviewer,reviewed_at=timezone.now(),note=fields.get("note", ""),promoted_obligation=obligation,promoted_version=version)
    return obligation,version,review

@transaction.atomic
def update_legal_obligation_draft(version,user,criteria=None,**fields):
    _superuser(user);version=LegalObligationVersion.objects.select_for_update().get(pk=version.pk)
    if version.state!="draft":raise ValidationError("Solo un draft puede editarse.")
    for key in fields:
        if key not in EDITABLE:raise ValidationError(f"Campo no editable: {key}.")
    proposed={key:getattr(version,key) for key in EDITABLE};proposed.update(fields)
    validate_semantic_fields(proposed["modality"],proposed["applicability_level"],proposed["applicability_mode"])
    clean_criteria=[validate_criterion(item,proposed["applicability_level"]) for item in criteria] if criteria is not None else None
    for key,value in fields.items():setattr(version,key,value)
    version.save(update_fields=list(fields))
    if clean_criteria is not None:
        version.criteria.all().delete();_create_criteria(version,clean_criteria)
    return version

def _validate_contract(version):
    validate_semantic_fields(version.modality,version.applicability_level,version.applicability_mode)
    if not version.canonical_statement.strip():raise ValidationError("canonical_statement es obligatorio.")
    if version.applicability_mode=="pending":raise ValidationError("La aplicabilidad sigue pendiente.")
    count=version.criteria.count()
    if version.applicability_mode=="unconditional" and count:raise ValidationError("unconditional no admite criterios.")
    if version.applicability_mode=="conditional" and not count:raise ValidationError("conditional requiere criterios.")
    for criterion in version.criteria.all():validate_criterion({"dimension":criterion.dimension,"operator":criterion.operator,"values":criterion.values,"note":criterion.note},version.applicability_level)
    review=version.source_candidate.review;candidate=version.source_candidate;article=candidate.extraction_run.article;artifact=article.parse.source_document.artifact;p=version.source_provenance
    expected={"source":"BCN/LeyChile","candidate_id":candidate.id,"candidate_key":candidate.candidate_key,"extractor_version":candidate.extraction_run.extractor_version,"modality_hint":candidate.modality_hint,"artifact_id":artifact.id,"artifact_sha256":artifact.content_sha256,"version_uri":artifact.metadata.get("version_uri"),"parser_version":article.parse.parser_version,"article_id":article.id,"article_key":article.article_key,"article_number":article.article_number,"article_text_hash":article.text_hash,"source_quote":candidate.source_quote,"source_start":candidate.source_start,"source_end":candidate.source_end,"trigger_text":candidate.trigger_text,"trigger_start":candidate.trigger_start,"trigger_end":candidate.trigger_end}
    if review.decision!="approved" or review.promoted_version_id!=version.id or any(p.get(key)!=value for key,value in expected.items()):raise ValidationError("Provenance o revision invalida.")

@transaction.atomic
def validate_legal_obligation_version(version,user):
    _superuser(user);version=LegalObligationVersion.objects.select_for_update().get(pk=version.pk)
    if version.state!="draft":raise ValidationError("Solo un draft puede validarse.")
    _validate_contract(version);LegalObligationVersion.objects.filter(pk=version.pk).update(state="validated",validated_by=user,validated_at=timezone.now());version.refresh_from_db();return version

@transaction.atomic
def activate_legal_obligation_version(version,user):
    _superuser(user);version=LegalObligationVersion.objects.select_for_update().get(pk=version.pk)
    if version.state!="validated":raise ValidationError("Solo una version validada puede activarse.")
    _validate_contract(version);now=timezone.now();old=LegalObligationVersion.objects.select_for_update().filter(obligation=version.obligation,state="active").exclude(pk=version.pk)
    old.update(state="obsolete",obsoleted_at=now);LegalObligationVersion.objects.filter(pk=version.pk).update(state="active",activated_by=user,activated_at=now);version.refresh_from_db();return version

@transaction.atomic
def obsolete_legal_obligation_version(version,user):
    _superuser(user);version=LegalObligationVersion.objects.select_for_update().get(pk=version.pk)
    if version.state!="active":raise ValidationError("Solo una version activa puede quedar obsoleta.")
    LegalObligationVersion.objects.filter(pk=version.pk).update(state="obsolete",obsoleted_at=timezone.now());version.refresh_from_db();return version

def evaluate_legal_obligation_applicability(version,context):
    output={"result":"undetermined","matched":[],"failed":[],"missing":[]}
    if version.applicability_mode=="pending":return output
    required=context.get("work") if version.applicability_level=="work" else context.get("organization")
    if not required:return output
    if version.applicability_mode=="unconditional":output["result"]="applicable";return output
    for criterion in version.criteria.all() if hasattr(version.criteria,"all") else version.criteria:
        dimension=criterion.dimension;scope,key,_=DIMENSIONS[dimension];value=(context.get(scope) or {}).get(key);expected=criterion.values
        item={"dimension":dimension,"actual":value,"expected":expected,"operator":criterion.operator}
        if value in (None,""):output["missing"].append(item)
        elif (str(value).casefold()==str(expected[0]).casefold() if criterion.operator=="equals" else str(value).casefold() in {str(v).casefold() for v in expected}):output["matched"].append(item)
        else:output["failed"].append(item)
    output["result"]="not_applicable" if output["failed"] else "undetermined" if output["missing"] else "applicable";return output
