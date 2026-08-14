from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Organizacion, PlantillaMapeo, ProcesoIngesta
from .serializers_ingestion_v2 import PlantillaMapeoSerializer, ProcesoIngestaSerializer
from .services.ingestion_v2 import (analizar_ingesta, confirmar_ingesta, crear_ingesta,
                                    guardar_mapeo, preview_ingesta)


def _organizacion(organizacion_id):
    return get_object_or_404(Organizacion, organizacion_id=organizacion_id)


def _proceso(organizacion, ingesta_id):
    return get_object_or_404(ProcesoIngesta.objects.select_related("version_evidencia__evidencia", "fuente_datos", "plantilla_mapeo"), organizacion=organizacion, id=ingesta_id)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser])
def ingestas(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    if request.method == "GET":
        queryset = organizacion.procesos_ingesta.select_related("version_evidencia__evidencia", "fuente_datos", "plantilla_mapeo")
        return Response(ProcesoIngestaSerializer(queryset, many=True).data)
    upload = request.FILES.get("archivo") or request.FILES.get("file")
    if not upload:
        return Response({"error": "Debe adjuntar un archivo CSV o XLSX."}, status=status.HTTP_400_BAD_REQUEST)
    if not upload.name.lower().endswith((".csv", ".xlsx", ".xls")):
        return Response({"error": "Formato no soportado."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        proceso = crear_ingesta(
            organizacion, upload, fuente_id=request.data.get("fuente_datos"),
            fuente_nombre=request.data.get("fuente_nombre", ""), evidencia_id=request.data.get("evidencia"),
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ProcesoIngestaSerializer(proceso).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def ingesta_detail(request, organizacion_id, ingesta_id):
    proceso = _proceso(_organizacion(organizacion_id), ingesta_id)
    return Response(ProcesoIngestaSerializer(proceso).data)


@api_view(["POST"])
def ingesta_analizar(request, organizacion_id, ingesta_id):
    proceso = _proceso(_organizacion(organizacion_id), ingesta_id)
    try:
        return Response(analizar_ingesta(proceso))
    except Exception as exc:
        proceso.estado = ProcesoIngesta.Estado.FALLIDO; proceso.resumen_errores = str(exc); proceso.save()
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "PATCH"])
def ingesta_mapeo(request, organizacion_id, ingesta_id):
    proceso = _proceso(_organizacion(organizacion_id), ingesta_id)
    try:
        plantilla = guardar_mapeo(proceso, request.data.get("mapeos", []), request.data.get("nombre", "Transporte"))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(PlantillaMapeoSerializer(plantilla).data)


@api_view(["GET"])
def ingesta_preview(request, organizacion_id, ingesta_id):
    return Response(preview_ingesta(_proceso(_organizacion(organizacion_id), ingesta_id)))


@api_view(["POST"])
def ingesta_confirmar(request, organizacion_id, ingesta_id):
    try:
        return Response(confirmar_ingesta(_proceso(_organizacion(organizacion_id), ingesta_id)))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def plantillas_mapeo(request, organizacion_id):
    organizacion = _organizacion(organizacion_id)
    queryset = PlantillaMapeo.objects.filter(organizacion=organizacion).select_related("fuente_datos").prefetch_related("mapeos")
    return Response(PlantillaMapeoSerializer(queryset, many=True).data)
