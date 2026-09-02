from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    FormulaAmbiental,
    Organizacion,
)
from .permissions import (
    Permission,
    get_membership,
    has_tenant_permission,
    require_resource_work_access,
)
from .serializers_calculation_v2 import (
    CalculoAmbientalSerializer,
    FactorAmbientalSerializer,
    ImpactoAmbientalSerializer,
    MetodologiaSerializer,
    VariableFormulaSerializer,
    VersionMetodologiaSerializer,
)
from .selectors.calculation import (
    calculation_for_organization,
    calculations_for_activity,
    impacts_for_user,
)
from .selectors.governance import (
    factor_for_organization,
    factors_for_organization,
    methodologies_for_organization,
    methodology_for_organization,
    methodology_version_for_organization,
    professional_review_for_organization,
)
from .services.calculation_v2 import calculate_activity, recalculate
from .services.methodology_governance import (
    create_formula_variable,
    create_methodology_version,
    delete_formula_variable,
    transition_version,
    update_formula_variable,
    validate_applicability,
)
from .services.methodology_compatibility import compare_calculations
from .services.methodology_selector import select_methodology


def _org(request, value, permission):
    org = get_object_or_404(Organizacion, organizacion_id=value)
    allowed = has_tenant_permission(request.user, org, permission)
    if allowed:
        return org
    if get_membership(request.user, org):
        raise PermissionDenied("No tienes permisos para realizar esta acción.")
    return None


def _activity(request, org, value):
    activity = get_object_or_404(
        org.actividades_operacionales.select_related("obra"), id=value
    )
    return require_resource_work_access(request.user, org, activity)


def _serialize_selection(selection):
    selected = selection["seleccion"]
    candidate = selection.get("candidata")

    def methodology_identity(item):
        if not item:
            return None
        version = item["version_metodologia"]
        return {
            "id": version.metodologia_id,
            "nombre": version.metodologia.nombre,
            "version": version.version,
            "formula": item["formula"].expresion_legible,
            "estado": item["estado"],
        }
    reasons = (
        selected["elegibilidad"]["motivos"]
        if selected
        else list(
            dict.fromkeys(
                reason
                for candidate in selection["candidatos"]
                for reason in candidate.get("motivos", [])
            )
        )
    )
    if not reasons:
        reasons = [
            "No existe una metodología activa y vigente configurada para esta actividad."
            if not selection["candidatos"]
            else selection["razon"]
        ]
    return {
        "estado": selection["estado"],
        "metodologia_seleccionada": (
            {
                **methodology_identity(selected),
                "factor": selected["elegibilidad"]["factor_version"].factor.nombre,
            }
            if selected
            else None
        ),
        "metodologia_candidata": methodology_identity(candidate),
        "requiere_revision_metodologica": selection.get(
            "requiere_revision_metodologica", False
        ),
        "razon": selection["razon"],
        "motivos": reasons,
        "alternativos": [
            {"metodo": item["metodo"], "estado": item["estado"]}
            for item in selection["alternativos"]
        ],
        "descartados": selection["descartados"],
        "candidatos": [
            {
                **(
                    (methodology_identity(item) or {})
                    if item.get("formula")
                    else {}
                ),
                "metodo": item["metodo"],
                "motivos": item["motivos"],
                "estado": item["estado"],
            }
            for item in selection["candidatos"]
        ],
        "advertencias": selected["elegibilidad"]["advertencias"] if selected else [],
    }


@api_view(["GET"])
def metodologias(request, organizacion_id):
    org = _org(request, organizacion_id, Permission.FACTOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    queryset = methodologies_for_organization(org)
    return Response(MetodologiaSerializer(queryset, many=True).data)


@api_view(["GET", "POST"])
def metodologia_detail(request, organizacion_id, metodologia_id):
    permission = (
        Permission.FACTOR_VIEW
        if request.method == "GET"
        else Permission.FACTOR_CUSTOM_CREATE
    )
    org = _org(request, organizacion_id, permission)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    item = get_object_or_404(
        methodology_for_organization(org, metodologia_id),
    )
    if request.method == "GET":
        return Response(MetodologiaSerializer(item).data)
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
    if formula_data.get("tipo") == FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO:
        factor = None
    else:
        factor = get_object_or_404(
            factor_for_organization(org, formula_data.get("factor_ambiental"))
        )
    variables = []
    for row in formula_data.get("variables", []):
        serializer = VariableFormulaSerializer(data=row)
        serializer.is_valid(raise_exception=True)
        variables.append(serializer.validated_data)
    version = create_methodology_version(item, payload, formula_data, factor, variables)
    return Response(VersionMetodologiaSerializer(version).data, status=201)


@api_view(["POST"])
def metodologia_transition(request, organizacion_id, metodologia_id, version_id):
    org = _org(request, organizacion_id, Permission.FACTOR_CUSTOM_REVIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    version = get_object_or_404(
        methodology_version_for_organization(org, metodologia_id, version_id),
    )
    if version.metodologia.organizacion_id is None and not request.user.is_superuser:
        return Response(
            {"detail": "Solo un superusuario puede modificar metodologías globales."},
            status=403,
        )
    professional_review = None
    if request.data.get("revision_profesional_id"):
        professional_review = get_object_or_404(
            professional_review_for_organization(
                org, request.data["revision_profesional_id"]
            )
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
    org = _org(request, organizacion_id, Permission.FACTOR_CUSTOM_CREATE)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    version = get_object_or_404(
        methodology_version_for_organization(
            org, metodologia_id, version_id, tenant_only=True
        ),
    )
    if version.estado != VersionMetodologia.Estado.BORRADOR:
        return Response(
            {"detail": "Solo una versión borrador puede editarse."}, status=400
        )
    if request.method == "POST":
        serializer = VariableFormulaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        create_formula_variable(version.formula, serializer.validated_data)
        return Response(serializer.data, status=201)
    variable = get_object_or_404(version.formula.variables, id=variable_id)
    if request.method == "DELETE":
        delete_formula_variable(variable)
        return Response(status=204)
    serializer = VariableFormulaSerializer(variable, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    update_formula_variable(variable, serializer.validated_data)
    return Response(serializer.data)


@api_view(["GET"])
def factores_ambientales(request, organizacion_id):
    org = _org(request, organizacion_id, Permission.FACTOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    queryset = factors_for_organization(org)
    return Response(FactorAmbientalSerializer(queryset, many=True).data)


@api_view(["GET"])
def elegibilidad_actividad(request, organizacion_id, actividad_id):
    org = _org(request, organizacion_id, Permission.INDICATOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    return Response(
        _serialize_selection(select_methodology(_activity(request, org, actividad_id)))
    )


@api_view(["POST"])
def calcular_actividad(request, organizacion_id, actividad_id):
    org = _org(request, organizacion_id, Permission.INDICATOR_MANAGE)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    activity = _activity(request, org, actividad_id)
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
    org = _org(request, organizacion_id, Permission.INDICATOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    activity = _activity(request, org, actividad_id)
    queryset = calculations_for_activity(activity)
    return Response(CalculoAmbientalSerializer(queryset, many=True).data)


@api_view(["GET"])
def calculo_detail(request, organizacion_id, calculo_id):
    org = _org(request, organizacion_id, Permission.INDICATOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    item = get_object_or_404(
        calculation_for_organization(org, calculo_id, detailed=True),
    )
    require_resource_work_access(request.user, org, item)
    return Response(CalculoAmbientalSerializer(item).data)


@api_view(["POST"])
def calculo_recalculate(request, organizacion_id, calculo_id):
    org = _org(request, organizacion_id, Permission.INDICATOR_MANAGE)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    calculation = require_resource_work_access(
        request.user,
        org,
        get_object_or_404(calculation_for_organization(org, calculo_id)),
    )
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
    org = _org(request, organizacion_id, Permission.INDICATOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    calculation = require_resource_work_access(
        request.user,
        org,
        get_object_or_404(calculation_for_organization(org, calculo_id)),
    )
    return Response(calculation.snapshot_tecnico)


@api_view(["GET"])
def calculo_compare(request, organizacion_id, calculo_id, other_id):
    org = _org(request, organizacion_id, Permission.INDICATOR_VIEW)
    if not org:
        return Response({"detail": "Recurso no encontrado."}, status=404)
    left = require_resource_work_access(
        request.user,
        org,
        get_object_or_404(calculation_for_organization(org, calculo_id)),
    )
    right = require_resource_work_access(
        request.user,
        org,
        get_object_or_404(calculation_for_organization(org, other_id)),
    )
    return Response(compare_calculations(left, right))


@api_view(["GET"])
def impactos_ambientales(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
        Permission.INDICATOR_VIEW,
    )

    if not org:
        return Response(
            {"detail": "Recurso no encontrado."},
            status=404,
        )

    queryset = impacts_for_user(org, request.user, request.query_params.get("obra"))

    return Response(
        ImpactoAmbientalSerializer(
            queryset,
            many=True,
        ).data
    )
