from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import material_for_organization, work_for_organization
from .services.material_ledger import (ledger_entries, ledger_entry_provenance,
                                       material_ledger_totals)


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _filters(request, organization):
    params = request.query_params
    work = None
    if params.get("obra"):
        work = get_object_or_404(work_for_organization(organization, params["obra"]))
    material = None
    if params.get("material"):
        material = get_object_or_404(material_for_organization(organization, params["material"]))
    return {
        "work": work,
        "material": material,
        "start": parse_date(params["desde"]) if params.get("desde") else None,
        "end": parse_date(params["hasta"]) if params.get("hasta") else None,
        "categoria": params.get("categoria") or None,
        "standard": params.get("standard") or None,
    }


@api_view(["GET"])
def ledger_totals(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    filters = _filters(request, organization)
    group_by = request.query_params.get("agrupar_por") or None
    return Response(material_ledger_totals(organization, group_by=group_by, **filters))


@api_view(["GET"])
def ledger_entry_list(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    filters = _filters(request, organization)
    include_superseded = request.query_params.get("incluir_superseded") == "1"
    entries = ledger_entries(organization, include_superseded=include_superseded, **filters)
    return Response(
        [
            {
                "id": entry.id,
                "actividad_id": entry.actividad_id,
                "resultado": entry.resultado,
                "unidad_resultado": entry.unidad_resultado,
                "fecha_calculo": entry.fecha_calculo,
                "version_interna": entry.version_interna,
                "es_recalculo": entry.recalculo_de_id is not None,
            }
            for entry in entries
        ]
    )


@api_view(["GET"])
def ledger_entry_detail(request, organizacion_id, calculo_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    entry = get_object_or_404(
        ledger_entries(organization, include_superseded=True), pk=calculo_id
    )
    return Response(ledger_entry_provenance(entry))
