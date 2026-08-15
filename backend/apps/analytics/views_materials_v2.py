from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (EventoMaterial, LoteMaterial, MaterialOperacional, Obra,
                     Organizacion, UsuarioOrganizacion)
from .serializers_materials_v2 import (EventoMaterialSerializer,
                                       LoteMaterialSerializer,
                                       MaterialOperacionalSerializer)
from .services.materials_v2 import material_balance, material_lineage


def _organization(request, value):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(user=request.user, organizacion=organization, activo=True).exists())
    return organization if allowed else None


@api_view(["GET", "POST"])
def materials(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(MaterialOperacionalSerializer(organization.materiales_operacionales.all(), many=True, context=context).data)
    serializer = MaterialOperacionalSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def material_detail(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(MaterialOperacional, organizacion=organization, id=material_id)
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(MaterialOperacionalSerializer(material, context=context).data)
    serializer = MaterialOperacionalSerializer(material, data=request.data, partial=True, context=context)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def lots(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = organization.lotes_materiales.select_related("material", "fuente", "evidencia", "version_evidencia")
    if request.query_params.get("material"):
        rows = rows.filter(material_id=request.query_params["material"])
    if request.method == "GET":
        return Response(LoteMaterialSerializer(rows, many=True, context=context).data)
    serializer = LoteMaterialSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def events(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = organization.eventos_materiales.select_related(
        "material", "lote", "actividad", "evento_origen", "obra", "proceso", "fuente",
        "evidencia", "version_evidencia", "observacion_cantidad__fuente",
    )
    for parameter, field in (("material", "material_id"), ("lote", "lote_id"), ("obra", "obra_id"), ("tipo", "tipo")):
        if request.query_params.get(parameter):
            rows = rows.filter(**{field: request.query_params[parameter]})
    if request.method == "GET":
        return Response(EventoMaterialSerializer(rows, many=True, context=context).data)
    serializer = EventoMaterialSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH"])
def event_detail(request, organizacion_id, event_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    event = get_object_or_404(EventoMaterial, organizacion=organization, id=event_id)
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(EventoMaterialSerializer(event, context=context).data)
    serializer = EventoMaterialSerializer(event, data=request.data, partial=True, context=context)
    serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


def _scope(request, organization, material):
    lot = get_object_or_404(LoteMaterial, organizacion=organization, material=material, id=request.query_params["lote"]) if request.query_params.get("lote") else None
    work = get_object_or_404(Obra, organizacion=organization, id=request.query_params["obra"]) if request.query_params.get("obra") else None
    return lot, work


@api_view(["GET"])
def balance(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(MaterialOperacional, organizacion=organization, id=material_id)
    lot, work = _scope(request, organization, material)
    return Response(material_balance(organization, material, lot=lot, work=work, start=request.query_params.get("desde"), end=request.query_params.get("hasta")))


@api_view(["GET"])
def lineage(request, organizacion_id, material_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    material = get_object_or_404(MaterialOperacional, organizacion=organization, id=material_id)
    lot, _ = _scope(request, organization, material)
    return Response(material_lineage(organization, material, lot=lot))


@api_view(["GET"])
def material_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response([material_balance(organization, material) for material in organization.materiales_operacionales.all()])
