from django.db.models import Count, Q
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
    UsuarioOrganizacion,
    VariableAmbientalExtraida,
)
from .serializers import (
    AlertaCumplimientoAmbientalSerializer,
    DocumentoAmbientalSerializer,
    LimiteNormativoAmbientalSerializer,
    VariableAmbientalExtraidaSerializer,
)


def get_organizacion_or_404(
    request,
    organizacion_id,
):
    organization = get_object_or_404(
        Organizacion,
        organizacion_id=organizacion_id,
    )

    allowed = request.user.is_authenticated and (
        request.user.is_superuser
        or UsuarioOrganizacion.objects.filter(
            user=request.user,
            organizacion=organization,
            activo=True,
        ).exists()
    )

    if not allowed:
        from django.http import Http404

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
        Obra,
        organizacion=organization,
        id=work_id,
    )


def serialize(serializer_class, instance, request=None, many=False):
    return serializer_class(instance, many=many, context={"request": request}).data


def filter_alerts_for_work(queryset, work):
    """Limit alerts to relations that consistently belong to the requested work."""
    return queryset.filter(
        Q(documento__obra=work, variable__isnull=True)
        | Q(documento__isnull=True, variable__documento__obra=work)
        | Q(documento__obra=work, variable__documento__obra=work)
    ).distinct()


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def documentos_ambientales(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    if request.method == "GET":
        queryset = (
            DocumentoAmbiental.objects.filter(organizacion=organizacion)
            .select_related(
                "organizacion",
                "obra",
                "etapa",
            )
            .prefetch_related("registros_emision")
        )

        work = requested_work(
            request,
            organizacion,
        )

        if work is not None:
            queryset = queryset.filter(obra=work)

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
    documento = serializer.save()
    return Response(
        serialize(DocumentoAmbientalSerializer, documento, request=request),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def documento_ambiental_detail(request, organizacion_id, documento_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    documento = get_object_or_404(
        DocumentoAmbiental, pk=documento_id, organizacion=organizacion
    )
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
    documento = serializer.save()
    return Response(serialize(DocumentoAmbientalSerializer, documento, request=request))


@api_view(["GET", "POST"])
def variables_ambientales(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    if request.method == "GET":
        queryset = VariableAmbientalExtraida.objects.filter(
            organizacion=organizacion
        ).select_related(
            "organizacion",
            "documento",
        )

        work = requested_work(
            request,
            organizacion,
        )

        if work is not None:
            queryset = queryset.filter(documento__obra=work)

        estado = request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado_cumplimiento=estado)
        return Response(VariableAmbientalExtraidaSerializer(queryset, many=True).data)

    data = request.data.copy()
    data["organizacion"] = organizacion.id
    serializer = VariableAmbientalExtraidaSerializer(
        data=data, context={"organizacion": organizacion}
    )
    serializer.is_valid(raise_exception=True)
    variable = serializer.save()
    return Response(
        VariableAmbientalExtraidaSerializer(variable).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
def variable_ambiental_detail(request, organizacion_id, variable_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    variable = get_object_or_404(
        VariableAmbientalExtraida, pk=variable_id, organizacion=organizacion
    )
    if request.method == "GET":
        return Response(VariableAmbientalExtraidaSerializer(variable).data)
    if request.method == "DELETE":
        variable.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = VariableAmbientalExtraidaSerializer(
        variable,
        data=request.data,
        partial=True,
        context={"organizacion": organizacion},
    )
    serializer.is_valid(raise_exception=True)
    variable = serializer.save()
    return Response(VariableAmbientalExtraidaSerializer(variable).data)


@api_view(["GET", "POST"])
def limites_ambientales(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    if request.method == "GET":
        queryset = LimiteNormativoAmbiental.objects.filter(organizacion=organizacion)
        activo = request.query_params.get("activo")
        if activo not in (None, ""):
            queryset = queryset.filter(
                activo=str(activo).lower() in {"1", "true", "si", "yes"}
            )
        return Response(LimiteNormativoAmbientalSerializer(queryset, many=True).data)

    data = request.data.copy()
    data["organizacion"] = organizacion.id
    data.setdefault("industria", organizacion.preset)
    serializer = LimiteNormativoAmbientalSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    limite = serializer.save()
    return Response(
        LimiteNormativoAmbientalSerializer(limite).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "DELETE"])
def limite_ambiental_detail(request, organizacion_id, limite_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    limite = get_object_or_404(
        LimiteNormativoAmbiental, pk=limite_id, organizacion=organizacion
    )
    if request.method == "GET":
        return Response(LimiteNormativoAmbientalSerializer(limite).data)
    if request.method == "DELETE":
        limite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = LimiteNormativoAmbientalSerializer(
        limite, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    limite = serializer.save()
    return Response(LimiteNormativoAmbientalSerializer(limite).data)


@api_view(["GET"])
def alertas_cumplimiento(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    queryset = AlertaCumplimientoAmbiental.objects.filter(
        organizacion=organizacion
    ).select_related(
        "documento",
        "variable",
    )

    work = requested_work(
        request,
        organizacion,
    )

    if work is not None:
        queryset = filter_alerts_for_work(queryset, work)

    estado = request.query_params.get("estado")
    if estado:
        queryset = queryset.filter(estado=estado)
    return Response(AlertaCumplimientoAmbientalSerializer(queryset, many=True).data)


@api_view(["PATCH"])
def alerta_cumplimiento_detail(request, organizacion_id, alerta_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    alerta = get_object_or_404(
        AlertaCumplimientoAmbiental, pk=alerta_id, organizacion=organizacion
    )
    serializer = AlertaCumplimientoAmbientalSerializer(
        alerta, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    alerta = serializer.save()
    return Response(AlertaCumplimientoAmbientalSerializer(alerta).data)


@api_view(["GET"])
def cumplimiento_ambiental_resumen(request, organizacion_id):
    organizacion = get_organizacion_or_404(
        request,
        organizacion_id,
    )
    documentos = DocumentoAmbiental.objects.filter(organizacion=organizacion)
    variables = VariableAmbientalExtraida.objects.filter(organizacion=organizacion)
    alertas = AlertaCumplimientoAmbiental.objects.filter(organizacion=organizacion)
    work = requested_work(
        request,
        organizacion,
    )

    if work is not None:
        documentos = documentos.filter(obra=work)

        variables = variables.filter(documento__obra=work)

        alertas = filter_alerts_for_work(alertas, work)
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
    estados = variables.values("estado_cumplimiento").annotate(total=Count("id"))
    estados_map = {item["estado_cumplimiento"]: item["total"] for item in estados}

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
