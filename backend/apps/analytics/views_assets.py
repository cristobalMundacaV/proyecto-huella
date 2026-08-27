from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors.assets import (
    asset_for_organization,
    assets_for_organization,
    conditions_for_asset,
    maintenance_for_organization,
    maintenances_for_asset,
    organization_by_public_id,
)
from .serializers_assets import (
    ActivoOperacionalSerializer,
    CondicionOperacionalSerializer,
    MantenimientoActivoSerializer,
)


def _org(value):
    return get_object_or_404(organization_by_public_id(value))


@api_view(["GET", "POST"])
def activos(request, organizacion_id):
    org = _org(organizacion_id)
    queryset = assets_for_organization(org, request.query_params)
    if request.method == "GET":
        return Response(ActivoOperacionalSerializer(queryset, many=True).data)
    serializer = ActivoOperacionalSerializer(
        data=request.data, context={"organizacion": org}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def activo_detail(request, organizacion_id, activo_id):
    org = _org(organizacion_id)
    activo = get_object_or_404(asset_for_organization(org, activo_id, detailed=True))
    if request.method == "GET":
        return Response(ActivoOperacionalSerializer(activo).data)
    serializer = ActivoOperacionalSerializer(
        activo, data=request.data, partial=True, context={"organizacion": org}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def mantenimientos_activo(request, organizacion_id, activo_id):
    org = _org(organizacion_id)
    activo = get_object_or_404(asset_for_organization(org, activo_id))
    if request.method == "GET":
        return Response(
            MantenimientoActivoSerializer(
                maintenances_for_asset(activo), many=True
            ).data
        )
    serializer = MantenimientoActivoSerializer(
        data=request.data, context={"organizacion": org, "activo": activo}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def mantenimiento_detail(request, organizacion_id, mantenimiento_id):
    org = _org(organizacion_id)
    item = get_object_or_404(maintenance_for_organization(org, mantenimiento_id))
    if request.method == "GET":
        return Response(MantenimientoActivoSerializer(item).data)
    serializer = MantenimientoActivoSerializer(
        item,
        data=request.data,
        partial=True,
        context={"organizacion": org, "activo": item.activo},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def condiciones_activo(request, organizacion_id, activo_id):
    org = _org(organizacion_id)
    activo = get_object_or_404(asset_for_organization(org, activo_id))
    if request.method == "GET":
        return Response(
            CondicionOperacionalSerializer(conditions_for_asset(activo), many=True).data
        )
    serializer = CondicionOperacionalSerializer(
        data=request.data, context={"organizacion": org, "activo": activo}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)
