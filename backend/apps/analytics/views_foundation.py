from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    AplicabilidadCapacidadObra,
    CapacidadAmbiental,
    CapacidadOrganizacion,
    DiagnosticoAmbientalInicial,
    Organizacion,
    ProcesoOperacional,
    UnidadOperacional,
)
from .serializers_foundation import (
    CapacidadAmbientalSerializer,
    CapacidadOrganizacionSerializer,
    DiagnosticoAmbientalSerializer,
    ProcesoOperacionalSerializer,
    UnidadOperacionalSerializer,
)
from .services.foundation import (
    inicializar_capacidades_preset,
    resumen_preparacion_ambiental,
)
from .permissions import Permission, filter_works_for_user, has_tenant_permission


def _organizacion(request, organizacion_id, permission):
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    if not has_tenant_permission(request.user, organization, permission):
        from django.http import Http404
        raise Http404("Recurso no encontrado.")
    return organization


@api_view(["GET"])
def capacidades_disponibles(request):
    return Response(
        CapacidadAmbientalSerializer(
            CapacidadAmbiental.objects.filter(activa=True), many=True
        ).data
    )


@api_view(["GET", "POST", "PATCH"])
def diagnostico_ambiental(request, organizacion_id):
    permission = Permission.PROFILE_VIEW if request.method == "GET" else Permission.PROFILE_MANAGE
    organizacion = _organizacion(request, organizacion_id, permission)
    obra_id = request.query_params.get("obra") or request.data.get("obra")
    obra = get_object_or_404(filter_works_for_user(organizacion.obras.all(), request.user, organizacion), id=obra_id) if obra_id else None
    diagnostico = DiagnosticoAmbientalInicial.objects.filter(
        organizacion=organizacion, obra=obra
    ).first()
    if request.method == "GET":
        return Response(
            DiagnosticoAmbientalSerializer(diagnostico).data if diagnostico else None
        )
    if request.method == "POST" and diagnostico:
        return Response(
            {"error": "El alcance ya tiene un diagnostico."},
            status=status.HTTP_409_CONFLICT,
        )
    if request.method == "PATCH" and not diagnostico:
        return Response(
            {"error": "Diagnostico no encontrado."}, status=status.HTTP_404_NOT_FOUND
        )
    serializer = DiagnosticoAmbientalSerializer(
        diagnostico,
        data=request.data,
        partial=request.method == "PATCH",
        context={"organizacion": organizacion},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save(organizacion=organizacion, obra=obra)
    return Response(
        serializer.data,
        status=(
            status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK
        ),
    )


@api_view(["PATCH"])
def aplicabilidad_capacidad_obra(
    request,
    organizacion_id,
    obra_id,
    capacidad_id,
):
    organizacion = _organizacion(request, organizacion_id, Permission.APPLICABILITY_MANAGE)

    obra = get_object_or_404(
        filter_works_for_user(organizacion.obras.all(), request.user, organizacion),
        id=obra_id,
    )

    diagnostico = get_object_or_404(
        DiagnosticoAmbientalInicial,
        organizacion=organizacion,
        obra=obra,
    )

    inicializar_capacidades_preset(organizacion)

    relacion = get_object_or_404(
        CapacidadOrganizacion,
        organizacion=organizacion,
        capacidad_id=capacidad_id,
    )

    estado = request.data.get("estado")

    estados_validos = {value for value, _ in AplicabilidadCapacidadObra.Estado.choices}

    if estado not in estados_validos:
        return Response(
            {"estado": ["Estado de aplicabilidad inválido."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    aplicabilidad, _ = AplicabilidadCapacidadObra.objects.update_or_create(
        obra=obra,
        capacidad=relacion.capacidad,
        defaults={
            "diagnostico": diagnostico,
            "estado": estado,
        },
    )

    return Response(
        {
            "id": aplicabilidad.id,
            "capacidad": {
                "id": relacion.capacidad.id,
                "clave": relacion.capacidad.clave,
                "nombre": relacion.capacidad.nombre,
            },
            "estado": aplicabilidad.estado,
            "obra": obra.id,
            "diagnostico": diagnostico.id,
        }
    )


@api_view(["GET"])
def capacidades_organizacion(request, organizacion_id):
    relaciones = inicializar_capacidades_preset(_organizacion(request, organizacion_id, Permission.PROFILE_VIEW))
    return Response(CapacidadOrganizacionSerializer(relaciones, many=True).data)


@api_view(["PATCH"])
def capacidad_organizacion_detail(request, organizacion_id, capacidad_id):
    relacion = get_object_or_404(
        CapacidadOrganizacion,
        id=capacidad_id,
        organizacion=_organizacion(request, organizacion_id, Permission.PROFILE_MANAGE),
    )
    serializer = CapacidadOrganizacionSerializer(
        relacion, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


def _coleccion(request, organizacion, queryset, serializer_class):
    if request.method == "GET":
        return Response(
            serializer_class(
                queryset, many=True, context={"organizacion": organizacion}
            ).data
        )
    serializer = serializer_class(
        data=request.data, context={"organizacion": organizacion}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save(organizacion=organizacion)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def unidades_operacionales(request, organizacion_id):
    permission = Permission.ASSET_VIEW if request.method == "GET" else Permission.ASSET_MANAGE
    organizacion = _organizacion(request, organizacion_id, permission)
    return _coleccion(
        request,
        organizacion,
        organizacion.unidades_operacionales.all(),
        UnidadOperacionalSerializer,
    )


@api_view(["PATCH"])
def unidad_operacional_detail(request, organizacion_id, unidad_id):
    unidad = get_object_or_404(
        UnidadOperacional, id=unidad_id, organizacion=_organizacion(request, organizacion_id, Permission.ASSET_MANAGE)
    )
    serializer = UnidadOperacionalSerializer(unidad, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "POST"])
def procesos_operacionales(request, organizacion_id):
    permission = Permission.ASSET_VIEW if request.method == "GET" else Permission.ASSET_MANAGE
    organizacion = _organizacion(request, organizacion_id, permission)
    return _coleccion(
        request,
        organizacion,
        organizacion.procesos_operacionales.all(),
        ProcesoOperacionalSerializer,
    )


@api_view(["PATCH"])
def proceso_operacional_detail(request, organizacion_id, proceso_id):
    organizacion = _organizacion(request, organizacion_id, Permission.ASSET_MANAGE)
    proceso = get_object_or_404(
        ProcesoOperacional, id=proceso_id, organizacion=organizacion
    )
    serializer = ProcesoOperacionalSerializer(
        proceso, data=request.data, partial=True, context={"organizacion": organizacion}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def preparacion_ambiental(request, organizacion_id):
    organizacion = _organizacion(request, organizacion_id, Permission.PROFILE_VIEW)
    inicializar_capacidades_preset(organizacion)
    return Response(resumen_preparacion_ambiental(organizacion))
