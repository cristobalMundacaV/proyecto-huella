from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors.environmental_flows import organization_available_to_user
from .selectors.materials import (
    event_for_organization,
    events_for_organization,
    lot_for_scope,
    lots_for_organization,
    material_for_organization,
    materials_for_organization,
    work_for_organization,
)
from .serializers_materials_v2 import (
    EventoMaterialSerializer,
    LoteMaterialSerializer,
    MaterialOperacionalSerializer,
)
from .services.materials_v2 import material_balance, material_lineage


def _organization(request, value):
    return organization_available_to_user(request.user, value)


@api_view(["GET", "POST"])
def materials(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(
            MaterialOperacionalSerializer(
                materials_for_organization(organization), many=True, context=context
            ).data
        )
    serializer = MaterialOperacionalSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def material_detail(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(material_for_organization(organization, material_id))
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(MaterialOperacionalSerializer(material, context=context).data)
    serializer = MaterialOperacionalSerializer(
        material, data=request.data, partial=True, context=context
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def lots(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = lots_for_organization(organization, request.query_params.get("material"))
    if request.method == "GET":
        return Response(LoteMaterialSerializer(rows, many=True, context=context).data)
    serializer = LoteMaterialSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def events(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = events_for_organization(organization, request.query_params)
    if request.method == "GET":
        return Response(EventoMaterialSerializer(rows, many=True, context=context).data)
    serializer = EventoMaterialSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def event_detail(request, organizacion_id, event_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    event = get_object_or_404(event_for_organization(organization, event_id))
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(EventoMaterialSerializer(event, context=context).data)
    serializer = EventoMaterialSerializer(
        event, data=request.data, partial=True, context=context
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


def _scope(request, organization, material):
    lot = (
        get_object_or_404(
            lot_for_scope(organization, material, request.query_params["lote"])
        )
        if request.query_params.get("lote")
        else None
    )
    work = (
        get_object_or_404(
            work_for_organization(organization, request.query_params["obra"])
        )
        if request.query_params.get("obra")
        else None
    )
    return lot, work


@api_view(["GET"])
def balance(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(material_for_organization(organization, material_id))
    lot, work = _scope(request, organization, material)
    return Response(
        material_balance(
            organization,
            material,
            lot=lot,
            work=work,
            start=request.query_params.get("desde"),
            end=request.query_params.get("hasta"),
        )
    )


@api_view(["GET"])
def lineage(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(material_for_organization(organization, material_id))
    lot, _ = _scope(request, organization, material)
    return Response(material_lineage(organization, material, lot=lot))


@api_view(["GET"])
def material_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response(
        [
            material_balance(organization, material)
            for material in materials_for_organization(organization)
        ]
    )
