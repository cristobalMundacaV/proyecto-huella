from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    CalculoAmbiental,
    FactorAmbiental,
    FormulaAmbiental,
    ImpactoAmbiental,
    MetodologiaAmbiental,
    Organizacion,
    UsuarioOrganizacion,
    VariableFormula,
    VersionMetodologia,
)
from .serializers_calculation_v2 import (
    CalculoAmbientalSerializer,
    FactorAmbientalSerializer,
    ImpactoAmbientalSerializer,
    MetodologiaSerializer,
    VariableFormulaSerializer,
    VersionMetodologiaSerializer,
)
from .services.calculation_v2 import calculate_activity, recalculate
from .services.methodology_governance import transition_version, validate_applicability
from .services.methodology_compatibility import compare_calculations
from .services.methodology_selector import select_methodology


def _org(request, value):
    org = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = request.user.is_authenticated and (
        request.user.is_superuser
        or UsuarioOrganizacion.objects.filter(
            user=request.user,
            organizacion=org,
            activo=True,
        ).exists()
    )
    return org if allowed else None


def _activity(org, value):
    return get_object_or_404(org.actividades_operacionales, id=value)


def _tenant_admin(request, organization):
    return request.user.is_authenticated and (
        request.user.is_superuser
        or UsuarioOrganizacion.objects.filter(
            user=request.user,
            organizacion=organization,
            activo=True,
            rol=UsuarioOrganizacion.Rol.ADMIN,
        ).exists()
    )


def _serialize_selection(selection):
    selected = selection["seleccion"]
    return {
        "estado": selection["estado"],
        "metodologia_seleccionada": (
            {
                "id": selected["version_metodologia"].metodologia_id,
                "nombre": selected["version_metodologia"].metodologia.nombre,
                "version": selected["version_metodologia"].version,
                "formula": selected["formula"].expresion_legible,
                "factor": selected["elegibilidad"]["factor_version"].factor.nombre,
            }
            if selected
            else None
        ),
        "razon": selection["razon"],
        "alternativos": [
            {"metodo": item["metodo"], "estado": item["estado"]}
            for item in selection["alternativos"]
        ],
        "descartados": selection["descartados"],
        "candidatos": [
            {
                "metodo": item["metodo"],
                "estado": item["estado"],
                "motivos": item["motivos"],
            }
            for item in selection["candidatos"]
        ],
        "advertencias": selected["elegibilidad"]["advertencias"] if selected else [],
    }


@api_view(["GET"])
def metodologias(request, organizacion_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    queryset = MetodologiaAmbiental.objects.filter(
        Q(organizacion=org) | Q(organizacion__isnull=True)
    ).prefetch_related(
        "versiones__formula__variables", "versiones__formula__factor_ambiental"
    )
    return Response(MetodologiaSerializer(queryset, many=True).data)


@api_view(["GET", "POST"])
def metodologia_detail(request, organizacion_id, metodologia_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    item = get_object_or_404(
        MetodologiaAmbiental.objects.prefetch_related("versiones__formula__variables"),
        Q(organizacion=org) | Q(organizacion__isnull=True),
        id=metodologia_id,
    )
    if request.method == "GET":
        return Response(MetodologiaSerializer(item).data)
    if not _tenant_admin(request, org):
        return Response({"detail": "Permiso insuficiente."}, status=403)
    if item.organizacion_id is None and not request.user.is_superuser:
        return Response(
            {"detail": "Solo un superusuario puede modificar metodologías globales."},
            status=403,
        )
    payload = request.data.copy()
    formula_data = payload.pop("formula", None)
    if not formula_data:
        return Response({"formula": ["Este campo es obligatorio."]}, status=400)
    try:
        validate_applicability(payload.get("aplicabilidad", {}))
    except DjangoValidationError as exc:
        return Response({"aplicabilidad": exc.messages}, status=400)
    with transaction.atomic():
        version = VersionMetodologia.objects.create(
            metodologia=item,
            version=(
                item.versiones.order_by("-version")
                .values_list("version", flat=True)
                .first()
                or 0
            )
            + 1,
            descripcion_tecnica=payload.get("descripcion_tecnica", ""),
            fuente_referencia=payload.get("fuente_referencia", ""),
            vigencia_desde=payload.get("vigencia_desde") or None,
            vigencia_hasta=payload.get("vigencia_hasta") or None,
            aplicabilidad=payload.get("aplicabilidad", {}),
            prioridad=payload.get("prioridad", 100),
            requiere_revision_profesional=payload.get(
                "requiere_revision_profesional", False
            ),
            tipo_resultado=payload.get("tipo_resultado", "emision"),
        )
        factor = get_object_or_404(
            FactorAmbiental.objects.filter(
                Q(organizacion=org) | Q(organizacion__isnull=True)
            ),
            id=formula_data.get("factor_ambiental"),
        )
        formula = FormulaAmbiental.objects.create(
            version_metodologia=version,
            factor_ambiental=factor,
            codigo=formula_data.get(
                "codigo", f"formula-{item.codigo}-v{version.version}"
            ),
            tipo=formula_data.get("tipo"),
            expresion_legible=formula_data.get("expresion_legible", ""),
            version=formula_data.get("version", 1),
        )
        for row in formula_data.get("variables", []):
            serializer = VariableFormulaSerializer(data=row)
            serializer.is_valid(raise_exception=True)
            serializer.save(formula=formula)
    return Response(VersionMetodologiaSerializer(version).data, status=201)


@api_view(["POST"])
def metodologia_transition(request, organizacion_id, metodologia_id, version_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if not _tenant_admin(request, org):
        return Response({"detail": "Permiso insuficiente."}, status=403)
    version = get_object_or_404(
        VersionMetodologia.objects.filter(
            Q(metodologia__organizacion=org) | Q(metodologia__organizacion__isnull=True)
        ),
        id=version_id,
        metodologia_id=metodologia_id,
    )
    if version.metodologia.organizacion_id is None and not request.user.is_superuser:
        return Response(
            {"detail": "Solo un superusuario puede modificar metodologías globales."},
            status=403,
        )
    professional_review = None
    if request.data.get("revision_profesional_id"):
        from .models import RevisionProfesionalAmbiental

        professional_review = get_object_or_404(
            RevisionProfesionalAmbiental,
            id=request.data["revision_profesional_id"],
            organizacion=org,
        )
    try:
        transition_version(
            version, request.data.get("estado"), request.user, professional_review
        )
    except DjangoValidationError as exc:
        return Response({"detail": exc.messages}, status=400)
    return Response(VersionMetodologiaSerializer(version).data)


@api_view(["POST", "PATCH", "DELETE"])
def metodologia_variables(
    request, organizacion_id, metodologia_id, version_id, variable_id=None
):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    if not _tenant_admin(request, org):
        return Response({"detail": "Permiso insuficiente."}, status=403)
    version = get_object_or_404(
        VersionMetodologia,
        id=version_id,
        metodologia_id=metodologia_id,
        metodologia__organizacion=org,
    )
    if version.estado != VersionMetodologia.Estado.BORRADOR:
        return Response(
            {"detail": "Solo una versión borrador puede editarse."}, status=400
        )
    if request.method == "POST":
        serializer = VariableFormulaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(formula=version.formula)
        return Response(serializer.data, status=201)
    variable = get_object_or_404(version.formula.variables, id=variable_id)
    if request.method == "DELETE":
        variable.delete()
        return Response(status=204)
    serializer = VariableFormulaSerializer(variable, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
def factores_ambientales(request, organizacion_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    queryset = FactorAmbiental.objects.filter(
        Q(organizacion=org) | Q(organizacion__isnull=True)
    ).prefetch_related("versiones")
    return Response(FactorAmbientalSerializer(queryset, many=True).data)


@api_view(["GET"])
def elegibilidad_actividad(request, organizacion_id, actividad_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response(
        _serialize_selection(select_methodology(_activity(org, actividad_id)))
    )


@api_view(["POST"])
def calcular_actividad(request, organizacion_id, actividad_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    activity = _activity(org, actividad_id)
    try:
        calculation, selection = calculate_activity(
            activity, result_context=request.data.get("contexto_resultado")
        )
    except (ValueError, DjangoValidationError) as exc:
        detail = exc.messages if isinstance(exc, DjangoValidationError) else str(exc)
        return Response(
            {
                "error": detail,
                "elegibilidad": _serialize_selection(select_methodology(activity)),
            },
            status=400,
        )
    return Response(
        {
            "calculo": CalculoAmbientalSerializer(calculation).data,
            "seleccion": _serialize_selection(selection),
        },
        status=201,
    )


@api_view(["GET"])
def calculos_actividad(request, organizacion_id, actividad_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    activity = _activity(org, actividad_id)
    queryset = activity.calculos_ambientales.select_related(
        "version_metodologia__metodologia",
        "formula__factor_ambiental",
        "version_factor__factor",
    ).prefetch_related("inputs__observacion", "inputs__fuente")
    return Response(CalculoAmbientalSerializer(queryset, many=True).data)


@api_view(["GET"])
def calculo_detail(request, organizacion_id, calculo_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    item = get_object_or_404(
        CalculoAmbiental.objects.select_related(
            "version_metodologia__metodologia",
            "formula__factor_ambiental",
            "version_factor__factor",
        ).prefetch_related("inputs__observacion", "inputs__fuente"),
        organizacion=org,
        id=calculo_id,
    )
    return Response(CalculoAmbientalSerializer(item).data)


@api_view(["POST"])
def calculo_recalculate(request, organizacion_id, calculo_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    calculation = get_object_or_404(CalculoAmbiental, organizacion=org, id=calculo_id)
    try:
        new, selection = recalculate(
            calculation,
            request.data.get("motivo", ""),
            result_context=request.data.get("contexto_resultado"),
        )
    except (ValueError, DjangoValidationError) as exc:
        return Response(
            {
                "detail": (
                    exc.messages if isinstance(exc, DjangoValidationError) else str(exc)
                )
            },
            status=400,
        )
    return Response(
        {
            "calculo": CalculoAmbientalSerializer(new).data,
            "seleccion": _serialize_selection(selection),
        },
        status=201,
    )


@api_view(["GET"])
def calculo_snapshot(request, organizacion_id, calculo_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    calculation = get_object_or_404(CalculoAmbiental, organizacion=org, id=calculo_id)
    return Response(calculation.snapshot_tecnico)


@api_view(["GET"])
def calculo_compare(request, organizacion_id, calculo_id, other_id):
    org = _org(request, organizacion_id)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    left = get_object_or_404(CalculoAmbiental, organizacion=org, id=calculo_id)
    right = get_object_or_404(CalculoAmbiental, organizacion=org, id=other_id)
    return Response(compare_calculations(left, right))


@api_view(["GET"])
def impactos_ambientales(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
    )

    if not org:
        return Response(
            {"detail": "Recurso no encontrado."},
            status=404,
        )

    queryset = org.impactos_ambientales_v2.select_related(
        "actividad",
        "actividad__obra",
        "calculo",
    ).order_by(
        "-timestamp",
        "-created_at",
    )

    obra_id = request.query_params.get("obra")

    if obra_id:
        queryset = queryset.filter(actividad__obra_id=obra_id)

    return Response(
        ImpactoAmbientalSerializer(
            queryset,
            many=True,
        ).data
    )
