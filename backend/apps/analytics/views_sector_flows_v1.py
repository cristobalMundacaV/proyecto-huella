from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import (ActividadOperacional, EvidenciaObra, Obra, Organizacion, PuntoAmbientalOperacional,
                     RegistroFlujoAmbiental, UsuarioOrganizacion)
from .permissions import Permission, filter_works_for_user, require_tenant_permission
from .serializers import EvidenciaObraSerializer
from .serializers_activity_core import ActividadOperacionalSerializer
from .serializers_sector_flows_v1 import (PuntoAmbientalSerializer,
                                          RegistroFlujoAmbientalSerializer)
from .services.fuel_classification import FUEL_FLOWS, classify_fuel
from .services.operational_context import resolve_operational_context
from .services.sector_flows_v1 import sector_summary


def _organization(request, value):
    organization = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = request.user.is_authenticated and (request.user.is_superuser or UsuarioOrganizacion.objects.filter(user=request.user, organizacion=organization, activo=True).exists())
    return organization if allowed else None


def _requested_work(request, organization):
    work_id = request.query_params.get("obra")
    if not work_id:
        return None
    work = Obra.objects.filter(organizacion=organization, id=work_id).first()
    if not work:
        raise Http404("Recurso no encontrado.")
    return work


@api_view(["GET", "POST"])
def environmental_points(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = organization.puntos_ambientales.select_related("activo", "unidad_operacional", "proceso_operacional", "obra")
    work = _requested_work(request, organization)
    if work: rows = rows.filter(obra=work)
    if request.query_params.get("tipo"): rows = rows.filter(tipo=request.query_params["tipo"])
    if request.method == "GET": return Response(PuntoAmbientalSerializer(rows, many=True, context=context).data)
    serializer = PuntoAmbientalSerializer(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def sector_records(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = organization.registros_flujos_ambientales.select_related("actividad", "punto", "unidad_operacional", "proceso", "activo", "obra", "evento_material").prefetch_related("actividad__observaciones__fuente", "actividad__observaciones__evidencia", "actividad__observaciones__version_evidencia")
    for parameter, field in (("flujo", "flujo"), ("obra", "obra_id"), ("proceso", "proceso_id"), ("activo", "activo_id"), ("punto", "punto_id")):
        if request.query_params.get(parameter): rows = rows.filter(**{field: request.query_params[parameter]})
    if request.method == "GET": return Response(RegistroFlujoAmbientalSerializer(rows, many=True, context=context).data)
    serializer = RegistroFlujoAmbientalSerializer(data=request.data, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data, status=201)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def manual_sector_record(request, organizacion_id):
    """Create evidence, activity and environmental record atomically."""
    context = resolve_operational_context(request, Permission.DATA_CREATE)
    if str(context.organizacion.organizacion_id) != str(organizacion_id):
        raise Http404("Recurso no encontrado.")

    work_id = request.data.get("obra")
    if not work_id:
        raise ValidationError({"obra": "Selecciona la obra donde registrarÃ¡s la informaciÃ³n."})
    work = get_object_or_404(
        filter_works_for_user(Obra.objects.all(), request.user, context.organizacion),
        pk=work_id,
    )
    if context.obra and context.obra.id != work.id:
        raise ValidationError({"obra": "La obra no corresponde al espacio de trabajo activo."})

    uploaded_file = request.FILES.get("evidencia_archivo")
    if uploaded_file:
        require_tenant_permission(request.user, context.organizacion, Permission.EVIDENCE_CREATE)

    flow = request.data.get("flujo")
    destination = request.data.get("destino_operacional") or ""
    fuel_destinations = {"generador", "maquinaria", "vehiculo", "equipo_menor", "calefaccion", "otro"}
    if flow in FUEL_FLOWS and destination not in fuel_destinations:
        raise ValidationError({"destino_operacional": "Selecciona un uso vÃ¡lido para el combustible."})
    fuel_classification = classify_fuel(destination) if flow in FUEL_FLOWS else None
    classified_category = (fuel_classification or {}).get("categoria")
    if classified_category == "combustion_estacionaria":
        resolved_flow = RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO
        resolved_activity_type = ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO
    elif classified_category == "combustion_movil":
        resolved_flow = RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_MOVIL
        resolved_activity_type = ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE
    elif fuel_classification:
        resolved_flow = RegistroFlujoAmbiental.Flujo.COMBUSTIBLE
        resolved_activity_type = ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE
    else:
        resolved_flow = flow
        resolved_activity_type = request.data.get("tipo_actividad")

    evidence = None
    stored_file = None
    try:
        with transaction.atomic():
            if uploaded_file:
                evidence_serializer = EvidenciaObraSerializer(
                    data={
                        "organizacion": context.organizacion.id,
                        "obra": work.id,
                        "archivo": uploaded_file,
                        "nombre": (request.data.get("evidencia_nombre") or uploaded_file.name)[:240],
                        "tipo_evidencia": request.data.get("evidencia_tipo") or EvidenciaObra.TipoEvidencia.OTRO,
                        "estado_documental": EvidenciaObra.EstadoDocumental.PENDIENTE,
                        "metadata_extraccion": {
                            "workspace_id": context.espacio.id,
                            "origen_operacional": True,
                            "registro_manual": True,
                            "flujo": resolved_flow,
                        },
                    },
                    context={"request": request},
                )
                evidence_serializer.is_valid(raise_exception=True)
                evidence = evidence_serializer.save(
                    area_origen=context.area,
                    usuario_origen=context.usuario,
                    metodo_captura="manual",
                )
                stored_file = evidence.archivo

            activity_serializer = ActividadOperacionalSerializer(
                data={
                    "obra": work.id,
                    "tipo": resolved_activity_type,
                    "codigo": request.data.get("codigo_actividad"),
                    "nombre": request.data.get("nombre_actividad"),
                    "timestamp_inicio": request.data.get("periodo_inicio"),
                    "metadata": {
                        "workspace_id": context.espacio.id,
                        "area_origen_id": context.area.id,
                        "usuario_origen_id": context.usuario.id,
                        "metodo_captura": "manual",
                        "clasificacion_ambiental": fuel_classification,
                    },
                },
                context={"organizacion": context.organizacion, "request": request},
            )
            activity_serializer.is_valid(raise_exception=True)
            activity = activity_serializer.save()

            record_serializer = RegistroFlujoAmbientalSerializer(
                data={
                    "actividad": activity.id,
                    "obra": work.id,
                    "punto": request.data.get("punto") or None,
                    "flujo": resolved_flow,
                    "periodo_inicio": request.data.get("periodo_inicio"),
                    "granularidad": "punto" if request.data.get("punto") else "obra",
                    "concepto": request.data.get("concepto"),
                    "valor_numerico": request.data.get("valor_numerico") or None,
                    "valor_texto": request.data.get("valor_texto") or "",
                    "unidad": request.data.get("unidad") or "",
                    "fuente": request.data.get("fuente"),
                    "evidencia": evidence.id if evidence else None,
                    "tipo_recurso": request.data.get("tipo_recurso") or "",
                    "metrica": request.data.get("metrica") or "",
                    "destino_operacional": request.data.get("destino_operacional") or "",
                    "metadata": {
                        "clasificacion_ambiental": fuel_classification,
                        "flujo_declarado_cliente": flow,
                    } if fuel_classification else {},
                    "metodo_captura": "manual",
                },
                context={"organizacion": context.organizacion, "request": request},
            )
            record_serializer.is_valid(raise_exception=True)
            record = record_serializer.save()

            return Response(
                {
                    "registro": RegistroFlujoAmbientalSerializer(
                        record,
                        context={"organizacion": context.organizacion, "request": request},
                    ).data,
                    "actividad_id": activity.id,
                    "clasificacion_ambiental": fuel_classification,
                    "evidencia": EvidenciaObraSerializer(evidence, context={"request": request}).data if evidence else None,
                },
                status=status.HTTP_201_CREATED,
            )
    except Exception:
        if stored_file and stored_file.name:
            stored_file.storage.delete(stored_file.name)
        raise


@api_view(["GET", "PATCH"])
def sector_record_detail(request, organizacion_id, record_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    record = get_object_or_404(RegistroFlujoAmbiental, organizacion=organization, id=record_id)
    context = {"organizacion": organization, "request": request}
    if request.method == "GET": return Response(RegistroFlujoAmbientalSerializer(record, context=context).data)
    serializer = RegistroFlujoAmbientalSerializer(record, data=request.data, partial=True, context=context); serializer.is_valid(raise_exception=True); serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def sector_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization: return Response({"detail": "Recurso no encontrado."}, status=404)
    filters = {key: request.query_params.get(key) for key in ("flow", "start", "end") if request.query_params.get(key)}
    return Response(sector_summary(organization, **filters))
