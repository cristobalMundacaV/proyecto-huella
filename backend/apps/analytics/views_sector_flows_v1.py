from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import ActividadOperacional, EvidenciaObra, Obra, RegistroFlujoAmbiental
from .permissions import Permission, filter_works_for_user, require_tenant_permission
from .serializers import EvidenciaObraSerializer
from .serializers_activity_core import ActividadOperacionalSerializer
from .serializers_sector_flows_v1 import (
    PuntoAmbientalSerializer,
    RegistroFlujoAmbientalSerializer,
)
from .services.fuel_classification import FUEL_FLOWS, classify_fuel
from .services.operational_context import resolve_operational_context
from .services.quality_v2 import ensure_current_quality_evaluation
from .services.evidence_taxonomy import (
    evidence_types_for_domain,
    validate_evidence_type,
)
from .services.sector_flows_v1 import sector_summary
from .selectors.environmental_flows import (
    environmental_points_for_organization,
    environmental_record_for_organization,
    environmental_records_for_organization,
    organization_available_to_user,
    work_for_organization,
)


def _organization(request, value):
    return organization_available_to_user(request.user, value)


def _requested_work(request, organization):
    work_id = request.query_params.get("obra")
    if not work_id:
        return None
    work = work_for_organization(organization, work_id).first()
    if not work:
        raise Http404("Recurso no encontrado.")
    return work


@api_view(["GET"])
def evidence_types(request):
    return Response(evidence_types_for_domain(request.query_params.get("dominio")))


@api_view(["GET", "POST"])
def environmental_points(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    if request.query_params.get("obra"):
        _requested_work(request, organization)
    rows = environmental_points_for_organization(organization, request.query_params)
    if request.method == "GET":
        return Response(PuntoAmbientalSerializer(rows, many=True, context=context).data)
    serializer = PuntoAmbientalSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["GET", "POST"])
def sector_records(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    context = {"organizacion": organization, "request": request}
    rows = environmental_records_for_organization(organization, request.query_params)
    if request.method == "GET":
        return Response(
            RegistroFlujoAmbientalSerializer(rows, many=True, context=context).data
        )
    serializer = RegistroFlujoAmbientalSerializer(data=request.data, context=context)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def manual_sector_record(request, organizacion_id):
    """Create evidence, activity and environmental record atomically."""
    organization = _organization(request, organizacion_id)
    if not organization:
        raise Http404("Recurso no encontrado.")
    work_id = request.data.get("obra")
    if not work_id:
        raise ValidationError(
            {"obra": "Selecciona la obra donde registrarÃ¡s la informaciÃ³n."}
        )
    work = get_object_or_404(
        filter_works_for_user(Obra.objects.all(), request.user, organization),
        pk=work_id,
    )
    context = resolve_operational_context(
        request,
        Permission.DATA_CREATE,
        target_work=work,
    )

    uploaded_file = request.FILES.get("evidencia_archivo")
    if uploaded_file:
        require_tenant_permission(
            request.user, context.organizacion, Permission.EVIDENCE_CREATE
        )

    flow = request.data.get("flujo")
    destination = request.data.get("destino_operacional") or ""
    fuel_destinations = {
        "generador",
        "maquinaria",
        "vehiculo",
        "equipo_menor",
        "calefaccion",
        "otro",
    }
    if flow in FUEL_FLOWS and destination not in fuel_destinations:
        raise ValidationError(
            {"destino_operacional": "Selecciona un uso vÃ¡lido para el combustible."}
        )
    waste_destinations = {
        "residuo",
        "reutilizacion",
        "reciclaje",
        "valorizacion",
        "disposicion",
        "subproducto_reutilizado",
    }
    if flow == RegistroFlujoAmbiental.Flujo.RESIDUO and destination not in waste_destinations:
        raise ValidationError(
            {"destino_operacional": "Selecciona un destino valido para el residuo."}
        )
    if flow not in FUEL_FLOWS and flow != RegistroFlujoAmbiental.Flujo.RESIDUO:
        destination = RegistroFlujoAmbiental.DestinoOperacional.SIN_CLASIFICAR
    fuel_classification = classify_fuel(destination) if flow in FUEL_FLOWS else None
    classified_category = (fuel_classification or {}).get("categoria")
    if classified_category == "combustion_estacionaria":
        resolved_flow = RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_ESTACIONARIO
        resolved_activity_type = (
            ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE_ESTACIONARIO
        )
    elif classified_category == "combustion_movil":
        resolved_flow = RegistroFlujoAmbiental.Flujo.COMBUSTIBLE_MOVIL
        resolved_activity_type = ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE
    elif fuel_classification:
        resolved_flow = RegistroFlujoAmbiental.Flujo.COMBUSTIBLE
        resolved_activity_type = ActividadOperacional.Tipo.CONSUMO_COMBUSTIBLE
    else:
        resolved_flow = flow
        resolved_activity_type = request.data.get("tipo_actividad")

    evidence_type = None
    if uploaded_file:
        evidence_type = validate_evidence_type(
            request.data.get("evidencia_tipo") or EvidenciaObra.TipoEvidencia.OTRO,
            resolved_flow,
        )

    evidence = None
    stored_file = None
    stored_version_file = None
    try:
        with transaction.atomic():
            if uploaded_file:
                evidence_serializer = EvidenciaObraSerializer(
                    data={
                        "organizacion": context.organizacion.id,
                        "obra": work.id,
                        "archivo": uploaded_file,
                        "nombre": (
                            request.data.get("evidencia_nombre") or uploaded_file.name
                        )[:240],
                        "tipo_evidencia": evidence_type,
                        "metadata_extraccion": {
                            "workspace_id": context.espacio.id,
                            "origen_operacional": True,
                            "registro_manual": True,
                            "flujo": resolved_flow,
                            "mime_type": uploaded_file.content_type or "",
                            "nombre_original": uploaded_file.name,
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
                evidence_version = evidence._created_version
                stored_file = evidence.archivo
                stored_version_file = evidence_version.archivo
            else:
                evidence_version = None

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
                    "version_evidencia": evidence_version.id if evidence_version else None,
                    "tipo_recurso": request.data.get("tipo_recurso") or "",
                    "metrica": request.data.get("metrica") or "",
                    "destino_operacional": destination,
                    "metadata": (
                        {
                            "clasificacion_ambiental": fuel_classification,
                            "flujo_declarado_cliente": flow,
                        }
                        if fuel_classification
                        else {}
                    ),
                    "metodo_captura": "manual",
                },
                context={"organizacion": context.organizacion, "request": request},
            )
            record_serializer.is_valid(raise_exception=True)
            record = record_serializer.save()
            quality_evaluation = None
            if evidence:
                observation = record.actividad.observaciones.get(evidencia=evidence)
                quality_evaluation = ensure_current_quality_evaluation(observation)

            return Response(
                {
                    "registro": RegistroFlujoAmbientalSerializer(
                        record,
                        context={
                            "organizacion": context.organizacion,
                            "request": request,
                        },
                    ).data,
                    "actividad_id": activity.id,
                    "clasificacion_ambiental": fuel_classification,
                    "validacion_documental": {
                        "veredicto": "indeterminada",
                        "estado_procesamiento": evidence_version.estado_procesamiento,
                        "motivos": ["El respaldo fue guardado y quedó pendiente de procesamiento documental."],
                    } if evidence_version else None,
                    "evaluacion_calidad": (
                        {
                            "id": quality_evaluation.id,
                            "estado": quality_evaluation.estado,
                            "motivos": quality_evaluation.motivos,
                            "version_reglas": quality_evaluation.version_reglas,
                        }
                        if quality_evaluation
                        else None
                    ),
                    "evidencia": (
                        EvidenciaObraSerializer(
                            evidence, context={"request": request}
                        ).data
                        if evidence
                        else None
                    ),
                },
                status=status.HTTP_201_CREATED,
            )
    except Exception:
        if stored_version_file and stored_version_file.name:
            stored_version_file.storage.delete(stored_version_file.name)
        if stored_file and stored_file.name:
            stored_file.storage.delete(stored_file.name)
        raise


@api_view(["GET", "PATCH"])
def sector_record_detail(request, organizacion_id, record_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    record = get_object_or_404(
        environmental_record_for_organization(organization, record_id)
    )
    context = {"organizacion": organization, "request": request}
    if request.method == "GET":
        return Response(RegistroFlujoAmbientalSerializer(record, context=context).data)
    serializer = RegistroFlujoAmbientalSerializer(
        record, data=request.data, partial=True, context=context
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def sector_indicators(request, organizacion_id):
    organization = _organization(request, organizacion_id)
    if not organization:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    filters = {
        key: request.query_params.get(key)
        for key in ("flow", "start", "end")
        if request.query_params.get(key)
    }
    work_id = request.query_params.get("obra")
    if work_id:
        filters["work"] = get_object_or_404(
            filter_works_for_user(Obra.objects.all(), request.user, organization),
            pk=work_id,
        )
    return Response(sector_summary(organization, **filters))
