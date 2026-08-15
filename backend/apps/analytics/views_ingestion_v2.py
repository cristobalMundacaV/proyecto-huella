from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Organizacion, PlantillaMapeo, ProcesoIngesta, UsuarioOrganizacion
from .serializers_ingestion_v2 import PlantillaMapeoSerializer, ProcesoIngestaSerializer
from .services.ingestion_v2 import (analizar_ingesta, confirmar_ingesta, crear_ingesta,
                                    crear_ingesta_estructurada, guardar_mapeo, preview_ingesta)


def _organizacion(request, organizacion_id):
    organization = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(
        user=request.user, organizacion=organization, activo=True,
    ).exists())
    return organization if allowed else None


def _proceso(organizacion, ingesta_id):
    return get_object_or_404(ProcesoIngesta.objects.select_related("version_evidencia__evidencia", "fuente_datos", "plantilla_mapeo"), organizacion=organizacion, id=ingesta_id)


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ingestas(request, organizacion_id):
    organizacion = _organizacion(request, organizacion_id)
    if not organizacion: return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        queryset = organizacion.procesos_ingesta.select_related("version_evidencia__evidencia", "fuente_datos", "plantilla_mapeo")
        return Response(ProcesoIngestaSerializer(queryset, many=True).data)
    upload = request.FILES.get("archivo") or request.FILES.get("file")
    if not upload:
        try:
            proceso = crear_ingesta_estructurada(
                organizacion, request.data.get("payload"), fuente_id=request.data.get("fuente_datos"),
                fuente_nombre=request.data.get("fuente_nombre", "Fuente estructurada"),
                tipo_ingesta=request.data.get("tipo_ingesta", ""),
                destino_operacional=request.data.get("destino_operacional", "actividad_generica"),
                flujo=request.data.get("flujo", ""), contexto_confirmado=request.data.get("contexto", {}),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProcesoIngestaSerializer(proceso).data, status=status.HTTP_201_CREATED)
    ingestion_type = request.data.get("tipo_ingesta", "tabular")
    tabular_extensions = (".csv", ".xlsx", ".xls")
    documentary_extensions = tabular_extensions + (".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg")
    if not upload.name.lower().endswith(documentary_extensions if ingestion_type == "documental" else tabular_extensions):
        return Response({"error": "Formato no soportado."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        proceso = crear_ingesta(
            organizacion, upload, fuente_id=request.data.get("fuente_datos"),
            fuente_nombre=request.data.get("fuente_nombre", ""), evidencia_id=request.data.get("evidencia"),
            tipo_ingesta=request.data.get("tipo_ingesta", "tabular"),
            destino_operacional=request.data.get("destino_operacional", "actividad_generica"), flujo=request.data.get("flujo", ""),
            clasificacion_confirmada=request.data.get("clasificacion_confirmada", ""),
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(ProcesoIngestaSerializer(proceso).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def ingesta_detail(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    proceso = _proceso(organization, ingesta_id)
    return Response(ProcesoIngestaSerializer(proceso).data)


@api_view(["POST"])
def ingesta_analizar(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    proceso = _proceso(organization, ingesta_id)
    try:
        return Response(analizar_ingesta(proceso))
    except Exception as exc:
        proceso.estado = ProcesoIngesta.Estado.FALLIDO; proceso.resumen_errores = str(exc); proceso.save()
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "PATCH"])
def ingesta_mapeo(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    proceso = _proceso(organization, ingesta_id)
    try:
        plantilla = guardar_mapeo(
            proceso, request.data.get("mapeos", []), request.data.get("nombre", "Mapeo ambiental"),
            destino_operacional=request.data.get("destino_operacional"), flujo=request.data.get("flujo"),
            contexto=request.data.get("contexto"),
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(PlantillaMapeoSerializer(plantilla).data)


@api_view(["GET"])
def ingesta_preview(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response(preview_ingesta(_proceso(organization, ingesta_id)))


@api_view(["POST"])
def ingesta_confirmar(request, organizacion_id, ingesta_id):
    try:
        organization = _organizacion(request, organizacion_id)
        if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
        return Response(confirmar_ingesta(_proceso(organization, ingesta_id)))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def plantillas_mapeo(request, organizacion_id):
    organizacion = _organizacion(request, organizacion_id)
    if not organizacion: return Response({"detail": "Recurso no encontrado."}, status=404)
    queryset = PlantillaMapeo.objects.filter(organizacion=organizacion).select_related("fuente_datos").prefetch_related("mapeos")
    return Response(PlantillaMapeoSerializer(queryset, many=True).data)
