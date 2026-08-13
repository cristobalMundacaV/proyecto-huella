from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AccionMejoraAmbiental, Organizacion, ProblematicaAmbiental
from .serializers_problematicas import (
    AccionMejoraAmbientalSerializer, HistorialProblematicaAmbientalSerializer,
    MedicionSeguimientoAmbientalSerializer, ProblematicaAmbientalSerializer,
)
from .services.environmental_problems import (
    add_measurement, evaluate_problem, implement_action, measure_from_engine,
    recommend_action, transition_problem,
)


def _problem(organizacion, problematica_id):
    return get_object_or_404(ProblematicaAmbiental, organizacion=organizacion, pk=problematica_id)


def _error(exc):
    return Response(getattr(exc, "message_dict", {"detail": exc.messages}), status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def problematicas(request, organizacion_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    if request.method == "GET":
        return Response(ProblematicaAmbientalSerializer(org.problematicas_ambientales.all(), many=True).data)
    serializer = ProblematicaAmbientalSerializer(data=request.data, context={"organizacion": org})
    serializer.is_valid(raise_exception=True)
    problem = serializer.save(organizacion=org)
    problem.historial.create(evento="deteccion", estado_nuevo=problem.estado, usuario=request.user.get_username())
    return Response(ProblematicaAmbientalSerializer(problem).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def problematica_detail(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    problem = _problem(org, problematica_id)
    if request.method == "GET":
        return Response(ProblematicaAmbientalSerializer(problem).data)
    if request.method == "DELETE":
        problem.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = ProblematicaAmbientalSerializer(problem, data=request.data, partial=True, context={"organizacion": org})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["POST"])
def problematica_transition(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        problem = transition_problem(_problem(org, problematica_id), request.data.get("estado", ""), user=request.user, detail=request.data.get("detalle", ""))
        return Response(ProblematicaAmbientalSerializer(problem).data)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET", "POST"])
def problematica_actions(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    problem = _problem(org, problematica_id)
    if request.method == "GET":
        return Response(AccionMejoraAmbientalSerializer(problem.acciones.all(), many=True).data)
    serializer = AccionMejoraAmbientalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        action = recommend_action(problem, user=request.user, **serializer.validated_data)
        return Response(AccionMejoraAmbientalSerializer(action).data, status=status.HTTP_201_CREATED)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_action_implement(request, organizacion_id, problematica_id, action_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    action = get_object_or_404(AccionMejoraAmbiental, problematica=_problem(org, problematica_id), pk=action_id)
    try:
        return Response(AccionMejoraAmbientalSerializer(implement_action(action, user=request.user)).data)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET", "POST"])
def problematica_measurements(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    problem = _problem(org, problematica_id)
    if request.method == "GET":
        return Response(MedicionSeguimientoAmbientalSerializer(problem.mediciones.all(), many=True).data)
    serializer = MedicionSeguimientoAmbientalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    action = serializer.validated_data.pop("accion", None)
    try:
        measurement = add_measurement(problem, accion=action, user=request.user, **serializer.validated_data)
        return Response(MedicionSeguimientoAmbientalSerializer(measurement).data, status=status.HTTP_201_CREATED)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_measure_engine(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        raw_date = request.data.get("fecha")
        if raw_date and not parse_date(raw_date):
            return Response({"fecha": ["Formato de fecha invalido."]}, status=status.HTTP_400_BAD_REQUEST)
        measurement = measure_from_engine(
            _problem(org, problematica_id), fecha=parse_date(raw_date) if raw_date else None, user=request.user,
        )
        return Response(MedicionSeguimientoAmbientalSerializer(measurement).data, status=status.HTTP_201_CREATED)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["POST"])
def problematica_evaluate(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    try:
        problem = evaluate_problem(_problem(org, problematica_id), user=request.user)
        return Response(ProblematicaAmbientalSerializer(problem).data)
    except DjangoValidationError as exc:
        return _error(exc)


@api_view(["GET"])
def problematica_history(request, organizacion_id, problematica_id):
    org = get_object_or_404(Organizacion, organizacion_id=organizacion_id)
    return Response(HistorialProblematicaAmbientalSerializer(_problem(org, problematica_id).historial.all(), many=True).data)
