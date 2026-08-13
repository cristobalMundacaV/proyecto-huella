from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Organizacion,
    EtapaObra,
    EvidenciaObra,
    Obra,
    RegistroEmision,
    TransporteObra,
)
from .serializers import OrganizacionSerializer


def get_organizacion_or_404(organizacion_id):
    return get_object_or_404(Organizacion, organizacion_id=organizacion_id)


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
def organizacion_detail_safe(request, organizacion_id):
    organizacion = get_organizacion_or_404(organizacion_id)

    if request.method == "GET":
        return Response(OrganizacionSerializer(organizacion).data)

    if request.method == "PATCH":
        serializer = OrganizacionSerializer(organizacion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

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
