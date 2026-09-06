from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.knowledge.models import LegalEvidenceRequirement, LegalEvidenceRequirementVersion
from apps.knowledge.legal_evidence import get_legal_evidence_requirement_freshness
from .models import EvidenciaObra, LegalEvidenceOperationalLink, LegalEvidenceOperationalMappingRevision, Obra, Organizacion, VersionEvidencia
from .permissions import Permission, filter_works_for_user, get_membership, has_tenant_permission
from .services.legal_evidence_mapping import create_operational_evidence_link, get_legal_evidence_link_freshness, get_legal_evidence_mapping_freshness, list_operational_evidence_candidates, publish_legal_evidence_operational_mapping, withdraw_legal_evidence_link


def _org(request, value, permissions):
    org=get_object_or_404(Organizacion,organizacion_id=value)
    if not all(has_tenant_permission(request.user,org,p) for p in permissions):
        if request.user.is_authenticated and get_membership(request.user,org):raise PermissionDenied("Permisos insuficientes.")
        raise Http404
    return org


def _work(request,org,value):return get_object_or_404(filter_works_for_user(Obra.objects.all(),request.user,org),pk=value)
def _mapping_data(item):return {"id":item.id,"requirement_version_id":item.requirement_version_id,"revision":item.revision,"is_latest":item.is_latest,"mapping_items":item.mapping_items,"mapping_hash":item.mapping_hash,"note":item.note,"created_at":item.created_at,"freshness":get_legal_evidence_mapping_freshness(item)}
def _link_data(item):return {"id":item.id,"requirement_code":item.requirement_version.requirement.code,"status":item.status,"evidence_id":item.evidence_id,"evidence_version_id":item.evidence_version_id,"matched_evidence_class":item.matched_evidence_class,"matched_evidence_type":item.matched_evidence_type,"linked_at":item.linked_at,"withdrawn_at":item.withdrawn_at,"withdrawal_reason":item.withdrawal_reason,"freshness":get_legal_evidence_link_freshness(item),"requirement_snapshot":item.requirement_snapshot,"mapping_snapshot":item.mapping_snapshot,"applicability_snapshot":item.applicability_snapshot,"evidence_snapshot":item.evidence_snapshot}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mapping_detail(request,requirement_version_id):
    items=LegalEvidenceOperationalMappingRevision.objects.filter(requirement_version_id=requirement_version_id).select_related("requirement_version__requirement__obligation","requirement_version__legal_obligation_version__obligation").order_by("-revision")
    return Response([_mapping_data(item) for item in items])


@api_view(["POST"])
def mapping_publish(request,requirement_version_id):
    if not request.user.is_authenticated or not request.user.is_superuser:raise PermissionDenied()
    if set(request.data)-{"mapping_items","note"}:return Response({"detail":"Campos no permitidos."},status=400)
    try:item,created=publish_legal_evidence_operational_mapping(get_object_or_404(LegalEvidenceRequirementVersion,pk=requirement_version_id),request.data.get("mapping_items"),request.user,request.data.get("note",""));return Response({**_mapping_data(item),"created":created},status=201 if created else 200)
    except Exception as exc:return Response({"detail":getattr(exc,"messages",[str(exc)])},status=400)


def _requirements(org,work):
    level="work" if work else "organization";versions=LegalEvidenceRequirementVersion.objects.filter(state="active",legal_obligation_version__applicability_level=level).select_related("requirement__obligation","legal_obligation_version__obligation")
    output=[]
    for version in versions:
        readiness="ready"
        if get_legal_evidence_requirement_freshness(version)!="fresh":readiness="requirement_stale"
        else:
            mapping=version.operational_mapping_revisions.filter(is_latest=True).first()
            if not mapping:readiness="no_mapping"
            elif get_legal_evidence_mapping_freshness(mapping)!="fresh":readiness="mapping_stale"
            else:
                assessment=version.requirement.obligation.applicability_assessments.filter(organization=org,work=work,is_latest=True).first()
                if not assessment:readiness="not_evaluated"
                elif assessment.result!="applicable":readiness=assessment.result
                else:
                    from .services.legal_applicability import get_legal_assessment_freshness
                    if get_legal_assessment_freshness(assessment,org,work)!="fresh":readiness="assessment_stale"
        candidates=[]
        if readiness=="ready":candidates=list_operational_evidence_candidates(version.requirement.code,org,work)
        output.append({"code":version.requirement.code,"version":version.version,"title":version.title,"readiness":readiness,"candidate_count":len(candidates),"active_link_count":version.operational_links.filter(organization=org,work=work,status="linked").count()})
    return output


@api_view(["GET"])
def organization_requirements(request,organization_id):return Response(_requirements(_org(request,organization_id,[Permission.COMPLIANCE_VIEW,Permission.EVIDENCE_VIEW]),None))
@api_view(["GET"])
def work_requirements(request,organization_id,work_id):
    org=_org(request,organization_id,[Permission.COMPLIANCE_VIEW,Permission.EVIDENCE_VIEW]);return Response(_requirements(org,_work(request,org,work_id)))


def _candidates(request,organization_id,code,work_id=None):
    org=_org(request,organization_id,[Permission.COMPLIANCE_VIEW,Permission.EVIDENCE_VIEW]);work=_work(request,org,work_id) if work_id else None
    try:return Response(list_operational_evidence_candidates(code,org,work))
    except Exception as exc:return Response({"detail":getattr(exc,"messages",[str(exc)])},status=400)
@api_view(["GET"])
def organization_candidates(request,organization_id,requirement_code):return _candidates(request,organization_id,requirement_code)
@api_view(["GET"])
def work_candidates(request,organization_id,work_id,requirement_code):return _candidates(request,organization_id,requirement_code,work_id)


def _create_link(request,organization_id,code,work_id=None):
    org=_org(request,organization_id,[Permission.COMPLIANCE_MANAGE,Permission.EVIDENCE_VIEW]);work=_work(request,org,work_id) if work_id else None
    if set(request.data)-{"evidence_id","evidence_version_id","evidence_class","note"}:return Response({"detail":"Campos no permitidos."},status=400)
    try:item,created=create_operational_evidence_link(code,org,work,get_object_or_404(EvidenciaObra,pk=request.data.get("evidence_id")),get_object_or_404(VersionEvidencia,pk=request.data.get("evidence_version_id")),request.user,request.data.get("evidence_class"),request.data.get("note",""));return Response({**_link_data(item),"created":created},status=201 if created else 200)
    except Exception as exc:return Response({"detail":getattr(exc,"messages",[str(exc)])},status=400)
@api_view(["POST"])
def organization_link_create(request,organization_id,requirement_code):return _create_link(request,organization_id,requirement_code)
@api_view(["POST"])
def work_link_create(request,organization_id,work_id,requirement_code):return _create_link(request,organization_id,requirement_code,work_id)


def _links(request,organization_id,work_id=None):
    org=_org(request,organization_id,[Permission.COMPLIANCE_VIEW,Permission.EVIDENCE_VIEW]);work=_work(request,org,work_id) if work_id else None
    items=LegalEvidenceOperationalLink.objects.filter(organization=org,work=work).select_related("requirement_version__requirement__obligation","mapping_revision","applicability_assessment","evidence","evidence_version")
    for param,lookup in {"requirement_code":"requirement_version__requirement__code","evidence_id":"evidence_id","status":"status","evidence_type":"matched_evidence_type"}.items():
        if request.query_params.get(param):items=items.filter(**{lookup:request.query_params[param]})
    data=[_link_data(item) for item in items]
    if request.query_params.get("freshness"):data=[item for item in data if item["freshness"]==request.query_params["freshness"]]
    return Response(data)
@api_view(["GET"])
def organization_links(request,organization_id):return _links(request,organization_id)
@api_view(["GET"])
def work_links(request,organization_id,work_id):return _links(request,organization_id,work_id)


def _withdraw(request,organization_id,link_id,work_id=None):
    org=_org(request,organization_id,[Permission.COMPLIANCE_MANAGE,Permission.EVIDENCE_VIEW]);work=_work(request,org,work_id) if work_id else None
    try:return Response(_link_data(withdraw_legal_evidence_link(get_object_or_404(LegalEvidenceOperationalLink,pk=link_id,organization=org,work=work),request.user,request.data.get("withdrawal_reason",""))))
    except Exception as exc:return Response({"detail":getattr(exc,"messages",[str(exc)])},status=400)
@api_view(["POST"])
def organization_link_withdraw(request,organization_id,link_id):return _withdraw(request,organization_id,link_id)
@api_view(["POST"])
def work_link_withdraw(request,organization_id,work_id,link_id):return _withdraw(request,organization_id,link_id,work_id)
