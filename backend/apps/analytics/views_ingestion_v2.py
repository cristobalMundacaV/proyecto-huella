from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .permissions import Permission, has_tenant_permission
from .policies.ingestion import (
    parse_ingestion_context,
    user_can_access_ingestion_context,
)
from .selectors.ingestion import (
    ingestion_process_for_organization,
    ingestion_processes_for_user,
    mapping_templates_for_organization,
    organization_by_public_id,
)
from .serializers_ingestion_v2 import PlantillaMapeoSerializer, ProcesoIngestaSerializer
from .services.ingestion_v2 import (
    analizar_ingesta,
    confirmar_ingesta,
    crear_ingesta,
    crear_ingesta_estructurada,
    guardar_mapeo,
    mark_ingestion_failed,
    preview_ingesta,
)


def _organizacion(request, organizacion_id, permission):
    organization = get_object_or_404(organization_by_public_id(organizacion_id))
    allowed = has_tenant_permission(request.user, organization, permission)
    return organization if allowed else None


def _validate_context_scope(request, organization, context):
    if not user_can_access_ingestion_context(request.user, organization, context):
        raise Http404("Recurso no encontrado.")


def _proceso(request, organizacion, ingesta_id):
    process = get_object_or_404(
        ingestion_process_for_organization(organizacion, ingesta_id)
    )
    _validate_context_scope(request, organizacion, process.contexto_confirmado or {})
    return process


def _contexto(request):
    return parse_ingestion_context(request.data.get("contexto", {}))


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def ingestas(request, organizacion_id):
    permission = (
        Permission.IMPORT_VIEW if request.method == "GET" else Permission.IMPORT_CREATE
    )
    organizacion = _organizacion(request, organizacion_id, permission)
    if not organizacion:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if request.method == "GET":
        queryset = ingestion_processes_for_user(organizacion, request.user)
        return Response(ProcesoIngestaSerializer(queryset, many=True).data)

    context = _contexto(request)
    _validate_context_scope(request, organizacion, context)
    upload = request.FILES.get("archivo") or request.FILES.get("file")
    if not upload:
        try:
            process = crear_ingesta_estructurada(
                organizacion,
                request.data.get("payload"),
                fuente_id=request.data.get("fuente_datos"),
                fuente_nombre=request.data.get("fuente_nombre", "Fuente estructurada"),
                tipo_ingesta=request.data.get("tipo_ingesta", ""),
                destino_operacional=request.data.get(
                    "destino_operacional", "actividad_generica"
                ),
                flujo=request.data.get("flujo", ""),
                contexto_confirmado=context,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ProcesoIngestaSerializer(process).data,
            status=status.HTTP_201_CREATED,
        )

    ingestion_type = request.data.get("tipo_ingesta", "tabular")
    tabular_extensions = (".csv", ".xlsx", ".xls")
    documentary_extensions = tabular_extensions + (
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg",
    )
    allowed_extensions = (
        documentary_extensions if ingestion_type == "documental" else tabular_extensions
    )
    if not upload.name.lower().endswith(allowed_extensions):
        return Response(
            {"error": "Formato no soportado."}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        process = crear_ingesta(
            organizacion,
            upload,
            fuente_id=request.data.get("fuente_datos"),
            fuente_nombre=request.data.get("fuente_nombre", ""),
            evidencia_id=request.data.get("evidencia"),
            tipo_ingesta=request.data.get("tipo_ingesta", "tabular"),
            destino_operacional=request.data.get(
                "destino_operacional", "actividad_generica"
            ),
            flujo=request.data.get("flujo", ""),
            clasificacion_confirmada=request.data.get("clasificacion_confirmada", ""),
            contexto_confirmado=context,
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        ProcesoIngestaSerializer(process).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def ingesta_detail(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id, Permission.IMPORT_VIEW)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    process = _proceso(request, organization, ingesta_id)
    return Response(ProcesoIngestaSerializer(process).data)


@api_view(["POST"])
def ingesta_analizar(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id, Permission.IMPORT_REVIEW)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    process = _proceso(request, organization, ingesta_id)
    try:
        return Response(analizar_ingesta(process))
    except Exception as exc:
        mark_ingestion_failed(process, exc)
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "PATCH"])
def ingesta_mapeo(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id, Permission.IMPORT_REVIEW)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    process = _proceso(request, organization, ingesta_id)
    try:
        template = guardar_mapeo(
            process,
            request.data.get("mapeos", []),
            request.data.get("nombre", "Mapeo ambiental"),
            destino_operacional=request.data.get("destino_operacional"),
            flujo=request.data.get("flujo"),
            contexto=request.data.get("contexto"),
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(PlantillaMapeoSerializer(template).data)


@api_view(["GET"])
def ingesta_preview(request, organizacion_id, ingesta_id):
    organization = _organizacion(request, organizacion_id, Permission.IMPORT_VIEW)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response(preview_ingesta(_proceso(request, organization, ingesta_id)))


@api_view(["POST"])
def ingesta_confirmar(request, organizacion_id, ingesta_id):
    try:
        organization = _organizacion(
            request, organizacion_id, Permission.IMPORT_CONFIRM
        )
        if not organization:
            return Response({"detail": "Recurso no encontrado."}, status=404)
        return Response(confirmar_ingesta(_proceso(request, organization, ingesta_id)))
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def plantillas_mapeo(request, organizacion_id):
    organization = _organizacion(request, organizacion_id, Permission.IMPORT_VIEW)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    queryset = mapping_templates_for_organization(organization)
    return Response(PlantillaMapeoSerializer(queryset, many=True).data)
