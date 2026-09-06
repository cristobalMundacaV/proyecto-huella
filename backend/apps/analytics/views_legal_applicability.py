from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.knowledge.models import LegalObligationVersion
from .models import LegalObligationApplicabilityAssessment,Obra,Organizacion
from .permissions import Permission,filter_works_for_user,get_membership,has_tenant_permission
from .services.legal_applicability import evaluate_active_legal_obligations_for_organization,evaluate_active_legal_obligations_for_work,get_legal_assessment_freshness

def _organization(request,organization_id,permission):
    organization=get_object_or_404(Organizacion,organizacion_id=organization_id)
    if not has_tenant_permission(request.user,organization,permission):
        if request.user.is_authenticated and get_membership(request.user,organization):raise PermissionDenied("No tienes permisos para realizar esta accion.")
        raise Http404
    return organization
def _work(request,organization,work_id):return get_object_or_404(filter_works_for_user(Obra.objects.all(),request.user,organization),pk=work_id)
def _assessment_data(item,organization,work):return {"id":item.id,"revision":item.revision,"result":item.result,"evaluated_at":item.evaluated_at,"evaluated_by":item.evaluated_by.get_username(),"freshness":get_legal_assessment_freshness(item,organization,work)}
def _row(version,assessment,organization,work):
    source=version.source_provenance
    freshness=_assessment_data(assessment,organization,work) if assessment else None
    return {"obligation":{"code":version.obligation.code,"version":version.version,"modality":version.modality,"canonical_statement":version.canonical_statement,"applicability_level":version.applicability_level,"source":{"norm_number":source.get("norm_number"),"article_number":source.get("article_number"),"artifact_sha256":source.get("artifact_sha256"),"source_quote":source.get("source_quote")}},"assessment":freshness,"evaluation_status":freshness["freshness"] if freshness else "not_evaluated"}
def _catalog(organization,work=None):
    versions=LegalObligationVersion.objects.filter(state="active").select_related("obligation").order_by("obligation_id")
    if work is None:versions=versions.filter(applicability_level="organization")
    rows=[]
    for version in versions:
        target=None if version.applicability_level=="organization" else work
        assessment=LegalObligationApplicabilityAssessment.objects.filter(organization=organization,work=target,obligation=version.obligation,is_latest=True).select_related("evaluated_by","obligation_version").first()
        rows.append(_row(version,assessment,organization,target))
    return rows
@api_view(["GET"])
def organization_legal_applicability(request,organization_id):return Response(_catalog(_organization(request,organization_id,Permission.COMPLIANCE_VIEW)))
@api_view(["POST"])
def evaluate_organization_legal_applicability(request,organization_id):return Response(evaluate_active_legal_obligations_for_organization(_organization(request,organization_id,Permission.COMPLIANCE_MANAGE),request.user).data())
@api_view(["GET"])
def work_legal_applicability(request,organization_id,work_id):
    organization=_organization(request,organization_id,Permission.COMPLIANCE_VIEW);return Response(_catalog(organization,_work(request,organization,work_id)))
@api_view(["POST"])
def evaluate_work_legal_applicability(request,organization_id,work_id):
    organization=_organization(request,organization_id,Permission.COMPLIANCE_MANAGE);return Response(evaluate_active_legal_obligations_for_work(organization,_work(request,organization,work_id),request.user).data())
def _history(request, organization, work, include_organization=False):
    queryset = LegalObligationApplicabilityAssessment.objects.filter(
        organization=organization
    )
    if include_organization:
        queryset = queryset.filter(Q(work=work) | Q(work__isnull=True))
    else:
        queryset = queryset.filter(work=work)
    queryset = queryset.select_related("obligation", "evaluated_by").order_by(
        "-evaluated_at"
    )
    if request.query_params.get("obligation_code"):queryset=queryset.filter(obligation__code=request.query_params["obligation_code"])
    if request.query_params.get("result"):queryset=queryset.filter(result=request.query_params["result"])
    if request.query_params.get("evaluator_version"):queryset=queryset.filter(evaluator_version=request.query_params["evaluator_version"])
    paginator=PageNumberPagination();paginator.page_size=50;page=paginator.paginate_queryset(queryset,request)
    return paginator.get_paginated_response(
        [
            {
                "id": item.id,
                "obligation_code": item.obligation.code,
                "revision": item.revision,
                "scope_level": item.scope_level,
                "result": item.result,
                "evaluator_version": item.evaluator_version,
                "is_latest": item.is_latest,
                "evaluated_at": item.evaluated_at,
                "evaluated_by": item.evaluated_by.get_username(),
                "context_snapshot": item.context_snapshot,
                "criteria_snapshot": item.criteria_snapshot,
                "legal_snapshot": item.legal_snapshot,
                "evaluation_details": item.evaluation_details,
                "context_hash": item.context_hash,
                "input_hash": item.input_hash,
            }
            for item in page
        ]
    )
@api_view(["GET"])
def organization_legal_history(request,organization_id):return _history(request,_organization(request,organization_id,Permission.COMPLIANCE_VIEW),None)
@api_view(["GET"])
def work_legal_history(request,organization_id,work_id):
    organization=_organization(request,organization_id,Permission.COMPLIANCE_VIEW);work=_work(request,organization,work_id)
    queryset_scope=request.query_params.get("scope")
    if queryset_scope == "organization":
        return _history(request, organization, None)
    if queryset_scope == "work":
        return _history(request, organization, work)
    return _history(request, organization, work, include_organization=True)
