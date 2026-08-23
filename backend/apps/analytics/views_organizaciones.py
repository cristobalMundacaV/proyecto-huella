from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Organizacion,
    EtapaObra,
    EvidenciaObra,
    Obra,
    RegistroEmision,
    TransporteObra,
    UsuarioOrganizacion,
)
from .permissions import Permission, has_tenant_permission
from .serializers import OrganizacionSerializer


def get_organizacion_or_404(request, organizacion_id):
    queryset = Organizacion.objects.all()
    if not request.user.is_superuser:
        queryset = queryset.filter(usuarios__user=request.user, usuarios__activo=True)
    return get_object_or_404(queryset.distinct(), organizacion_id=organizacion_id)


def can_administer(user, organization):
    return has_tenant_permission(user, organization, Permission.ORGANIZATION_UPDATE)


@transaction.atomic
def delete_organizacion_with_related_data(organizacion):
    """Elimina una organizacion de prueba junto con sus datos dependientes.

    El modelo protege algunas relaciones críticas con PROTECT para evitar borrados
    accidentales. Para la acción explícita de la interfaz se borra en orden:
    transportes/evidencias, registros, obras, etapas y finalmente organizacion.
    """

    obras = Obra.objects.filter(organizacion=organizacion)
    etapas = EtapaObra.objects.filter(organizacion=organizacion)
    registros = RegistroEmision.objects.filter(organizacion=organizacion)
    evidencias = EvidenciaObra.objects.filter(organizacion=organizacion)
    transportes = TransporteObra.objects.filter(obra__in=obras)

    deleted_summary = {
        "transportes": transportes.count(),
        "evidencias": evidencias.count(),
        "registros_emision": registros.count(),
        "obras": obras.count(),
        "etapas": etapas.count(),
    }

    # Primero se eliminan elementos que apuntan a registros/obras para evitar
    # que las relaciones SET_NULL o PROTECT dejen datos huérfanos en la prueba.
    transportes.delete()
    evidencias.delete()
    registros.delete()
    obras.delete()
    etapas.delete()
    organizacion.delete()

    return deleted_summary


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def organizacion_detail_safe(request, organizacion_id):
    organizacion = get_organizacion_or_404(request, organizacion_id)

    if request.method == "GET":
        if not has_tenant_permission(request.user, organizacion, Permission.ORGANIZATION_VIEW):
            return Response({"detail": "No tienes permisos para consultar esta organización."}, status=status.HTTP_403_FORBIDDEN)
        return Response(OrganizacionSerializer(organizacion).data)

    if request.method == "PATCH":
        if not can_administer(request.user, organizacion):
            return Response({"detail": "No tienes permisos para modificar esta organización."}, status=status.HTTP_403_FORBIDDEN)
        payload = request.data.copy()
        if not request.user.is_superuser:
            payload.pop("activa", None)
            payload.pop("organizacion_id", None)
        serializer = OrganizacionSerializer(organizacion, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    if not request.user.is_superuser:
        return Response({"detail": "La eliminación de organizaciones corresponde a la administración de plataforma."}, status=status.HTTP_403_FORBIDDEN)
    try:
        deleted_summary = delete_organizacion_with_related_data(organizacion)
    except ProtectedError as exc:
        protected_objects = [str(obj) for obj in exc.protected_objects][:5]
        return Response(
            {
                "error": "No se pudo eliminar la organizacion porque existen relaciones protegidas.",
                "detalle": protected_objects,
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response({"deleted": True, "resumen": deleted_summary}, status=status.HTTP_200_OK)
