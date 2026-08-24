from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import (
    AccionMejoraAmbiental,
    AlcanceProblematica,
    IndicadorProblematica,
    Obra,
    Organizacion,
    ProblematicaAmbiental,
)
from .permissions import Permission, filter_works_for_user, has_tenant_permission, require_resource_work_access

from .serializers_problematicas import (
    AccionMejoraAmbientalSerializer,
    HistorialProblematicaAmbientalSerializer,
    AlcanceProblematicaSerializer,
    CicloReevaluacionSerializer,
    IndicadorProblematicaSerializer,
    MedicionSeguimientoAmbientalSerializer,
    ProblematicaAmbientalSerializer,
    ResultadoIntervencionSerializer,
    SnapshotIntervencionSerializer,
)
from .services.environmental_problems import (
    add_measurement,
    evaluate_problem,
    implement_action,
    measure_from_engine,
    recommend_action,
    transition_problem,
)
from .services.intervention_v2 import (
    escalate_problem,
    evaluate_intervention,
    select_action,
    start_action,
)


def _org(
    request,
    value,
    permission=None,
):
    organization = get_object_or_404(
        Organizacion,
        organizacion_id=value,
    )

    permission = permission or (Permission.PROBLEM_VIEW if request.method == "GET" else Permission.PROBLEM_MANAGE)
    allowed = has_tenant_permission(request.user, organization, permission)

    if not allowed:
        raise Http404("Recurso no encontrado.")

    organization._rbac_user = request.user
    return organization


def _requested_work(request, organization):
    work_id = request.query_params.get("obra")
    if not work_id:
        return None
    work = filter_works_for_user(Obra.objects.all(), request.user, organization).filter(id=work_id).first()
    if not work:
        raise Http404("Recurso no encontrado.")
    return work


def _problem(organizacion, problematica_id, work=None):
    filters = {"organizacion": organizacion, "pk": problematica_id}
    if work is not None:
        filters["obra"] = work
    problem = ProblematicaAmbiental.objects.filter(**filters).first()
    if not problem:
        raise Http404("Recurso no encontrado.")
    require_resource_work_access(organizacion._rbac_user, organizacion, problem)
    return problem


def _error(exc):
    return Response(
        getattr(exc, "message_dict", {"detail": exc.messages}),
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET", "POST"])
def problematicas(
    request,
    organizacion_id,
):
    org = _org(
        request,
        organizacion_id,
        Permission.PROBLEM_VIEW if request.method == "GET" else Permission.PROBLEM_CREATE,
    )

    work = _requested_work(
        request,
        org,
    )

    if request.method == "GET":
        rows = org.problematicas_ambientales.all()

        if work is not None:
            rows = rows.filter(obra=work)

        return Response(
            ProblematicaAmbientalSerializer(
                rows,
                many=True,
            ).data
        )

    payload = request.data.copy()

    if work is not None:
        supplied_work = payload.get("obra")

        if supplied_work and str(supplied_work) != str(work.id):
            return Response(
                {"obra": ["La obra no coincide con el contexto solicitado."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload["obra"] = work.id

    serializer = ProblematicaAmbientalSerializer(
        data=payload,
        context={
            "organizacion": org,
        },
    )

    serializer.is_valid(raise_exception=True)
    requested_problem = ProblematicaAmbiental(organizacion=org, obra=serializer.validated_data.get("obra"))
    require_resource_work_access(request.user, org, requested_problem)

    problem = serializer.save(organizacion=org)

    problem.historial.create(
        evento="deteccion",
        estado_nuevo=problem.estado,
        usuario=request.user.get_username(),
    )

    return Response(
        ProblematicaAmbientalSerializer(problem).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
def problematica_detail(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    if request.method == "GET":
        return Response(ProblematicaAmbientalSerializer(problem).data)
    if request.method == "DELETE":
        problem.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = ProblematicaAmbientalSerializer(
        problem, data=request.data, partial=True, context={"organizacion": org}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
def problematica_transition(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    try:
        problem = transition_problem(
            _problem(org, problematica_id, _requested_work(request, org)),
            request.data.get("estado", ""),
            user=request.user,
            detail=request.data.get("detalle", ""),
        )
        return Response(ProblematicaAmbientalSerializer(problem).data)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET", "POST"])
def problematica_actions(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    if request.method == "GET":
        return Response(
            AccionMejoraAmbientalSerializer(problem.acciones.all(), many=True).data
        )
    serializer = AccionMejoraAmbientalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        action = recommend_action(
            problem, user=request.user, **serializer.validated_data
        )
        return Response(
            AccionMejoraAmbientalSerializer(action).data, status=status.HTTP_201_CREATED
        )
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_action_implement(request, organizacion_id, problematica_id, action_id):
    org = _org(
        request,
        organizacion_id,
    )
    action = get_object_or_404(
        AccionMejoraAmbiental,
        problematica=_problem(org, problematica_id, _requested_work(request, org)),
        pk=action_id,
    )
    try:
        return Response(
            AccionMejoraAmbientalSerializer(
                implement_action(action, user=request.user)
            ).data
        )
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET", "POST"])
def problematica_measurements(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    if request.method == "GET":
        return Response(
            MedicionSeguimientoAmbientalSerializer(
                problem.mediciones.all(), many=True
            ).data
        )
    serializer = MedicionSeguimientoAmbientalSerializer(
        data=request.data, context={"problematica": problem}
    )
    serializer.is_valid(raise_exception=True)
    action = serializer.validated_data.pop("accion", None)
    try:
        measurement = add_measurement(
            problem, accion=action, user=request.user, **serializer.validated_data
        )
        return Response(
            MedicionSeguimientoAmbientalSerializer(measurement).data,
            status=status.HTTP_201_CREATED,
        )
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_measure_engine(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    try:
        raw_date = request.data.get("fecha")
        if raw_date and not parse_date(raw_date):
            return Response(
                {"fecha": ["Formato de fecha invalido."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        measurement = measure_from_engine(
            _problem(org, problematica_id, _requested_work(request, org)),
            fecha=parse_date(raw_date) if raw_date else None,
            user=request.user,
        )
        return Response(
            MedicionSeguimientoAmbientalSerializer(measurement).data,
            status=status.HTTP_201_CREATED,
        )
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_evaluate(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    try:
        problem = _problem(org, problematica_id, _requested_work(request, org))
        if problem.ciclos_reevaluacion.filter(fecha_cierre=None).exists():
            return Response(
                ResultadoIntervencionSerializer(
                    evaluate_intervention(problem, user=request.user)
                ).data
            )
        problem = evaluate_problem(problem, user=request.user)
        return Response(ProblematicaAmbientalSerializer(problem).data)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET"])
def problematica_history(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    return Response(
        HistorialProblematicaAmbientalSerializer(
            _problem(
                org, problematica_id, _requested_work(request, org)
            ).historial.all(),
            many=True,
        ).data
    )


@api_view(["GET", "POST"])
def problematica_scope(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    if request.method == "GET":
        return Response(
            AlcanceProblematicaSerializer(problem.alcances_v2.all(), many=True).data
        )
    serializer = AlcanceProblematicaSerializer(
        data=request.data, context={"problematica": problem}
    )
    serializer.is_valid(raise_exception=True)
    return Response(
        AlcanceProblematicaSerializer(serializer.save(problematica=problem)).data,
        status=201,
    )


@api_view(["GET", "POST"])
def problematica_indicators(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    if request.method == "GET":
        return Response(
            IndicadorProblematicaSerializer(
                problem.indicadores_v2.select_related("indicador"), many=True
            ).data
        )
    serializer = IndicadorProblematicaSerializer(
        data=request.data, context={"problematica": problem}
    )
    serializer.is_valid(raise_exception=True)
    return Response(
        IndicadorProblematicaSerializer(serializer.save(problematica=problem)).data,
        status=201,
    )


@api_view(["POST"])
def problematica_action_select(request, organizacion_id, problematica_id, action_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    action = get_object_or_404(
        AccionMejoraAmbiental, problematica=problem, id=action_id
    )
    try:
        cycle = select_action(action, user=request.user)
        return Response(CicloReevaluacionSerializer(cycle).data, status=201)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_action_start(request, organizacion_id, problematica_id, action_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    action = get_object_or_404(
        AccionMejoraAmbiental, problematica=problem, id=action_id
    )
    try:
        cycle = start_action(
            action, confirmed=request.data.get("confirmado") is True, user=request.user
        )
        return Response(CicloReevaluacionSerializer(cycle).data)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET"])
def problematica_snapshot_base(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    snapshot = (
        problem.snapshots_intervencion.filter(tipo="base").order_by("-ciclo").first()
    )
    if not snapshot:
        return Response({"detail": "Snapshot BASE no disponible."}, status=404)
    return Response(SnapshotIntervencionSerializer(snapshot).data)


@api_view(["GET"])
def problematica_cycles(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    return Response(
        CicloReevaluacionSerializer(
            problem.ciclos_reevaluacion.select_related("resultado"), many=True
        ).data
    )


@api_view(["POST"])
def problematica_reevaluate(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    action = get_object_or_404(
        AccionMejoraAmbiental, problematica=problem, id=request.data.get("accion")
    )
    try:
        return Response(
            CicloReevaluacionSerializer(select_action(action, user=request.user)).data,
            status=201,
        )
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_escalate(request, organizacion_id, problematica_id):
    org = _org(
        request,
        organizacion_id,
    )
    problem = _problem(org, problematica_id, _requested_work(request, org))
    try:
        return Response(
            ProblematicaAmbientalSerializer(
                escalate_problem(problem, request.data.get("motivo", ""), request.user)
            ).data
        )
    except DjangoValidationError as exc:
        return _error(exc)
