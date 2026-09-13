"""CARBONO-ZERO-V1 — obra environmental dashboard + period readiness HTTP surface.

Same RBAC pattern already used by `views_geospatial_context.py`:
tenant-permission check + `require_work_access` (per-obra RBAC, respects
`alcance=OBRAS` scoped memberships) before anything is computed.
"""
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Obra, Organizacion, UsuarioOrganizacion
from .permissions import Permission, require_tenant_permission, require_work_access
from .services.obra_environmental_dashboard import build_obra_dashboard, build_period_readiness
from .services.obra_report import render_report_excel, render_report_pdf


def _scope(request, organizacion_id, obra_id):
    organizacion = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    if not request.user.is_superuser and not UsuarioOrganizacion.objects.filter(
        user=request.user, organizacion=organizacion, activo=True,
    ).exists():
        raise Http404("Recurso no encontrado.")
    require_tenant_permission(request.user, organizacion, Permission.DATA_VIEW)
    obra = get_object_or_404(Obra, pk=obra_id, organizacion=organizacion)
    require_work_access(request.user, organizacion, obra)
    return organizacion, obra


def _period_params(request):
    params = request.query_params
    relative_months = params.get("relative_months")
    return {
        "date_from": parse_date(params["date_from"]) if params.get("date_from") else None,
        "date_to": parse_date(params["date_to"]) if params.get("date_to") else None,
        "relative_months": int(relative_months) if relative_months else None,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def obra_environmental_dashboard(request, organizacion_id, obra_id):
    organizacion, obra = _scope(request, organizacion_id, obra_id)
    data = build_obra_dashboard(organizacion, request.user, obra, **_period_params(request))
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def obra_period_readiness(request, organizacion_id, obra_id):
    organizacion, obra = _scope(request, organizacion_id, obra_id)
    data = build_period_readiness(organizacion, request.user, obra, **_period_params(request))
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def obra_environmental_report_pdf(request, organizacion_id, obra_id):
    organizacion, obra = _scope(request, organizacion_id, obra_id)
    dashboard = build_obra_dashboard(organizacion, request.user, obra, **_period_params(request))
    content = render_report_pdf(dashboard)
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="informe-ambiental-obra-{obra.id}.pdf"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def obra_environmental_report_excel(request, organizacion_id, obra_id):
    organizacion, obra = _scope(request, organizacion_id, obra_id)
    dashboard = build_obra_dashboard(organizacion, request.user, obra, **_period_params(request))
    content = render_report_excel(dashboard)
    response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="informe-ambiental-obra-{obra.id}.xlsx"'
    return response
