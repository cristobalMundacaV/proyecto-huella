from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from .models import (
    AlertaCumplimientoAmbiental,
    DocumentoAmbiental,
    LimiteNormativoAmbiental,
    Obra,
    Organizacion,
    VariableAmbientalExtraida,
)
from .permissions import (
    Permission,
    filter_works_for_user,
    get_membership,
    has_tenant_permission,
    require_resource_work_access,
    require_work_access,
)
from .serializers import (
    AlertaCumplimientoAmbientalSerializer,
    DocumentoAmbientalSerializer,
    LimiteNormativoAmbientalSerializer,
    VariableAmbientalExtraidaSerializer,
)
from .services.compliance import (
    create_compliance_entity,
    delete_compliance_entity,
    update_compliance_entity,
)
from .selectors.compliance import (
    alert_for_organization,
    alerts_for_user,
    compliance_scope,
    compliance_state_counts,
    document_for_organization,
    documents_for_user,
    limit_for_organization,
    limits_for_organization,
    variable_for_organization,
    variables_for_organization,
)


def get_organizacion_or_404(
    request,
    organizacion_id,
    permission=None,
):
    organization = get_object_or_404(
        Organizacion,
        organizacion_id=organizacion_id,
    )

    permission = permission or (
        Permission.COMPLIANCE_VIEW
        if request.method == "GET"
        else Permission.COMPLIANCE_MANAGE
    )
    allowed = has_tenant_permission(request.user, organization, permission)

    if not allowed:
        from django.http import Http404
        from rest_framework.exceptions import PermissionDenied

        if request.user.is_authenticated and get_membership(request.user, organization):
            raise PermissionDenied("No tienes permisos para realizar esta acción.")
        raise Http404("Recurso no encontrado.")

    return organization


def requested_work(
    request,
    organization,
):
    work_id = request.query_params.get("obra")

    if not work_id:
        return None

    return get_object_or_404(
        filter_works_for_user(Obra.objects.all(), request.user, organization),
        id=work_id,
    )


def serialize(serializer_class, instance, request=None, many=False):
    return serializer_class(instance, many=many, context={"request": request}).data


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def documentos_ambientales(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
        (
            Permission.EVIDENCE_VIEW
            if request.method == "GET"
            else Permission.EVIDENCE_CREATE
        ),
    )
    if request.method == "GET":
        work = requested_work(
            request,
            organizacion,
        )

        queryset = documents_for_user(organizacion, request.user, work)

        return Response(
            serialize(
                DocumentoAmbientalSerializer, queryset, request=request, many=True
            )
        )

    data = request.data.copy()

    work = requested_work(
        request,
        organizacion,
    )

    if work is not None:
        supplied_work = data.get("obra")

        if supplied_work and str(supplied_work) != str(work.id):
            return Response(
                {"obra": ["La obra no coincide con el contexto solicitado."]},
                status=400,
            )

        data["obra"] = work.id

    data["organizacion"] = organizacion.id
    data.setdefault("industria", organizacion.preset)
    serializer = DocumentoAmbientalSerializer(
        data=data, context={"request": request, "organizacion": organizacion}
    )
    serializer.is_valid(raise_exception=True)
    if serializer.validated_data.get("obra"):
        require_work_access(
            request.user, organizacion, serializer.validated_data["obra"]
        )
    documento = serializer.save()
    return Response(
        serialize(DocumentoAmbientalSerializer, documento, request=request),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def documento_ambiental_detail(request, organizacion_id, documento_id):
    permission = Permission.EVIDENCE_VIEW
    if request.method != "GET":
        permission = (
            Permission.EVIDENCE_VALIDATE
            if "estado_validacion" in request.data
            else Permission.EVIDENCE_UPDATE
        )
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
        permission,
    )
    documento = get_object_or_404(document_for_organization(organizacion, documento_id))
    require_resource_work_access(request.user, organizacion, documento)
    if request.method == "GET":
        return Response(
            serialize(DocumentoAmbientalSerializer, documento, request=request)
        )
    if request.method == "DELETE":
        documento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = DocumentoAmbientalSerializer(
        documento,
        data=request.data,
        partial=True,
        context={"request": request, "organizacion": organizacion},
    )
    serializer.is_valid(raise_exception=True)
    if serializer.validated_data.get("obra"):
        require_work_access(
            request.user, organizacion, serializer.validated_data["obra"]
        )
    documento = serializer.save()
    return Response(serialize(DocumentoAmbientalSerializer, documento, request=request))


@api_view(["GET", "POST"])
def variables_ambientales(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
        (
            Permission.COMPLIANCE_VIEW
            if request.method == "GET"
            else Permission.COMPLIANCE_MANAGE
        ),
    )
    if request.method == "GET":
        work = requested_work(
            request,
            organizacion,
        )

        estado = request.query_params.get("estado")
        queryset = variables_for_organization(organizacion, work, estado)
        return Response(VariableAmbientalExtraidaSerializer(queryset, many=True).data)

    data = request.data.copy()
    data["organizacion"] = organizacion.id
    serializer = VariableAmbientalExtraidaSerializer(
        data=data, context={"organizacion": organizacion}
    )
    serializer.is_valid(raise_exception=True)
    if serializer.validated_data.get("documento"):
        require_resource_work_access(
            request.user, organizacion, serializer.validated_data["documento"]
        )
    variable = create_compliance_entity(
        VariableAmbientalExtraida, serializer.validated_data
    )
    return Response(
        VariableAmbientalExtraidaSerializer(variable).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
def variable_ambiental_detail(request, organizacion_id, variable_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
        (
            Permission.COMPLIANCE_VIEW
            if request.method == "GET"
            else Permission.COMPLIANCE_MANAGE
        ),
    )
    variable = get_object_or_404(variable_for_organization(organizacion, variable_id))
    require_resource_work_access(request.user, organizacion, variable)
    if request.method == "GET":
        return Response(VariableAmbientalExtraidaSerializer(variable).data)
    if request.method == "DELETE":
        delete_compliance_entity(variable)
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = VariableAmbientalExtraidaSerializer(
        variable,
        data=request.data,
        partial=True,
        context={"organizacion": organizacion},
    )
    serializer.is_valid(raise_exception=True)
    variable = update_compliance_entity(variable, serializer.validated_data)
    return Response(VariableAmbientalExtraidaSerializer(variable).data)


@api_view(["GET", "POST"])
def limites_ambientales(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    if request.method == "GET":
        activo = request.query_params.get("activo")
        active_value = (
            str(activo).lower() in {"1", "true", "si", "yes"}
            if activo not in (None, "")
            else None
        )
        queryset = limits_for_organization(organizacion, active_value)
        return Response(LimiteNormativoAmbientalSerializer(queryset, many=True).data)

    data = request.data.copy()
    data["organizacion"] = organizacion.id
    data.setdefault("industria", organizacion.preset)
    serializer = LimiteNormativoAmbientalSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    limite = create_compliance_entity(
        LimiteNormativoAmbiental, serializer.validated_data
    )
    return Response(
        LimiteNormativoAmbientalSerializer(limite).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
def limite_ambiental_detail(request, organizacion_id, limite_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    limite = get_object_or_404(limit_for_organization(organizacion, limite_id))
    if request.method == "GET":
        return Response(LimiteNormativoAmbientalSerializer(limite).data)
    if request.method == "DELETE":
        delete_compliance_entity(limite)
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = LimiteNormativoAmbientalSerializer(
        limite, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    limite = update_compliance_entity(limite, serializer.validated_data)
    return Response(LimiteNormativoAmbientalSerializer(limite).data)


@api_view(["GET"])
def alertas_cumplimiento(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    work = requested_work(
        request,
        organizacion,
    )

    estado = request.query_params.get("estado")
    queryset = alerts_for_user(organizacion, request.user, work, estado)
    return Response(AlertaCumplimientoAmbientalSerializer(queryset, many=True).data)


@api_view(["PATCH"])
def alerta_cumplimiento_detail(request, organizacion_id, alerta_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
        Permission.COMPLIANCE_REVIEW,
    )
    alerta = get_object_or_404(alert_for_organization(organizacion, alerta_id))
    require_resource_work_access(request.user, organizacion, alerta)
    serializer = AlertaCumplimientoAmbientalSerializer(
        alerta, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    alerta = update_compliance_entity(alerta, serializer.validated_data)
    return Response(AlertaCumplimientoAmbientalSerializer(alerta).data)


@api_view(["GET"])
def cumplimiento_ambiental_resumen(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    work = requested_work(
        request,
        organizacion,
    )

    documentos, variables, alertas = compliance_scope(organizacion, request.user, work)
    alertas_abiertas_q = Q(
        estado__in=[
            AlertaCumplimientoAmbiental.Estado.ABIERTA,
            AlertaCumplimientoAmbiental.Estado.EN_REVISION,
        ]
    )

    total_variables = variables.count()
    cumplen = variables.filter(
        estado_cumplimiento=VariableAmbientalExtraida.EstadoCumplimiento.CUMPLE
    ).count()
    compliance_pct = (
        round((cumplen / total_variables) * 100, 2) if total_variables else None
    )

    latest_critical = alertas.filter(
        alertas_abiertas_q, severidad__in=["rojo", "amarillo"]
    ).order_by("-created_at")[:5]
    recent_documents = documentos.order_by("-created_at")[:5]
    estados_map = compliance_state_counts(variables)

    return Response(
        {
            "organizacion_id": organizacion.organizacion_id,
            "obra_id": work.id if work else None,
            "industria": organizacion.preset,
            "total_documentos": documentos.count(),
            "documentos_pendientes": documentos.filter(
                estado_validacion=DocumentoAmbiental.EstadoValidacion.PENDIENTE
            ).count(),
            "documentos_validados": documentos.filter(
                estado_validacion=DocumentoAmbiental.EstadoValidacion.VALIDO
            ).count(),
            "total_variables": total_variables,
            "variables_cumplen": estados_map.get(
                VariableAmbientalExtraida.EstadoCumplimiento.CUMPLE, 0
            ),
            "variables_alerta": estados_map.get(
                VariableAmbientalExtraida.EstadoCumplimiento.ALERTA, 0
            ),
            "variables_incumplen": estados_map.get(
                VariableAmbientalExtraida.EstadoCumplimiento.INCUMPLE, 0
            ),
            "variables_sin_limite": estados_map.get(
                VariableAmbientalExtraida.EstadoCumplimiento.SIN_LIMITE, 0
            ),
            "alertas_abiertas": alertas.filter(alertas_abiertas_q).count(),
            "alertas_rojas": alertas.filter(
                alertas_abiertas_q, severidad="rojo"
            ).count(),
            "alertas_amarillas": alertas.filter(
                alertas_abiertas_q, severidad="amarillo"
            ).count(),
            "compliance_pct": compliance_pct,
            "critical_alerts": AlertaCumplimientoAmbientalSerializer(
                latest_critical, many=True
            ).data,
            "recent_documents": DocumentoAmbientalSerializer(
                recent_documents, many=True
            ).data,
        }
    )
