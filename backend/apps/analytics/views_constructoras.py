from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    Constructora,
    EtapaObra,
    EvidenciaObra,
    Obra,
    RegistroEmision,
    TransporteObra,
)
from .serializers import ConstructoraSerializer


def get_constructora_or_404(constructora_id):
    return get_object_or_404(Constructora, constructora_id=constructora_id)


@transaction.atomic
def delete_constructora_with_related_data(constructora):
    """Elimina una constructora de prueba junto con sus datos dependientes.

    El modelo protege algunas relaciones críticas con PROTECT para evitar borrados
    accidentales. Para la acción explícita de la interfaz se borra en orden:
    transportes/evidencias, registros, obras, etapas y finalmente constructora.
    """

    obras = Obra.objects.filter(constructora=constructora)
    etapas = EtapaObra.objects.filter(constructora=constructora)
    registros = RegistroEmision.objects.filter(constructora=constructora)
    evidencias = EvidenciaObra.objects.filter(constructora=constructora)
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
    constructora.delete()

    return deleted_summary


@api_view(["GET", "PATCH", "DELETE"])
def constructora_detail_safe(request, constructora_id):
    constructora = get_constructora_or_404(constructora_id)

    if request.method == "GET":
        return Response(ConstructoraSerializer(constructora).data)

    if request.method == "PATCH":
        serializer = ConstructoraSerializer(constructora, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    try:
        deleted_summary = delete_constructora_with_related_data(constructora)
    except ProtectedError as exc:
        protected_objects = [str(obj) for obj in exc.protected_objects][:5]
        return Response(
            {
                "error": "No se pudo eliminar la constructora porque existen relaciones protegidas.",
                "detalle": protected_objects,
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response({"deleted": True, "resumen": deleted_summary}, status=status.HTTP_200_OK)
