from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.analytics.models import (
    AccionMejoraAmbiental,
    HistorialProblematicaAmbiental,
    MedicionSeguimientoAmbiental,
    ProblematicaAmbiental,
)
from apps.analytics.services.environmental_engine import calculate_environmental_metrics


ALLOWED_TRANSITIONS = {
    "detectada": {"en_analisis", "escalada"},
    "en_analisis": {"accion_propuesta", "no_resuelta", "escalada"},
    "accion_propuesta": {"en_implementacion", "escalada"},
    "en_implementacion": {"en_seguimiento", "escalada"},
    "en_seguimiento": {"resuelta", "mejora_insuficiente", "no_resuelta", "escalada"},
    "mejora_insuficiente": {"accion_propuesta", "no_resuelta", "escalada"},
    "no_resuelta": {"en_analisis", "escalada"},
    "escalada": {"en_analisis", "no_resuelta"},
    "resuelta": set(),
}


def _actor(user):
    return user.get_username() if user and getattr(user, "is_authenticated", False) else ""


def _history(problem, event, *, old="", new="", detail="", user=None, metadata=None):
    return HistorialProblematicaAmbiental.objects.create(
        problematica=problem, evento=event, estado_anterior=old, estado_nuevo=new,
        detalle=detail, usuario=_actor(user), metadata=metadata or {},
    )


@transaction.atomic
def transition_problem(problem, new_state, *, user=None, detail=""):
    if new_state not in ALLOWED_TRANSITIONS.get(problem.estado, set()):
        raise ValidationError({"estado": f"Transicion no permitida: {problem.estado} -> {new_state}."})
    old = problem.estado
    problem.estado = new_state
    problem.save(update_fields=["estado", "updated_at"])
    _history(problem, "transicion", old=old, new=new_state, detail=detail, user=user)
    return problem


@transaction.atomic
def recommend_action(problem, *, titulo, descripcion, responsable="", fecha_inicio=None, fecha_objetivo=None,
                     metadata=None, justificacion="", fecha_termino_real=None, responsable_usuario=None,
                     observaciones="", user=None, **kwargs):
    if problem.estado not in {ProblematicaAmbiental.Estado.EN_ANALISIS, ProblematicaAmbiental.Estado.ANALIZANDO, ProblematicaAmbiental.Estado.DETECTADA}:
        raise ValidationError({"estado": "La problematica debe estar en analisis."})
    action = AccionMejoraAmbiental.objects.create(
        problematica=problem, titulo=titulo, descripcion=descripcion, responsable=responsable,
        fecha_inicio=fecha_inicio, fecha_objetivo=fecha_objetivo, metadata=metadata or {},
        justificacion=justificacion, fecha_termino_real=fecha_termino_real,
        responsable_usuario=responsable_usuario, observaciones=observaciones,
    )
    if problem.estado == ProblematicaAmbiental.Estado.EN_ANALISIS:
        transition_problem(problem, ProblematicaAmbiental.Estado.ACCION_PROPUESTA, user=user)
    else:
        problem.estado = ProblematicaAmbiental.Estado.PROPUESTA
        problem.save(update_fields=["estado", "updated_at"])
    _history(problem, "recomendacion", detail=titulo, user=user, metadata={"accion_id": action.id})
    return action


@transaction.atomic
def implement_action(action, *, user=None):
    problem = action.problematica
    if problem.estado != ProblematicaAmbiental.Estado.ACCION_PROPUESTA:
        raise ValidationError({"estado": "La problematica debe tener una accion propuesta."})
    action.implementada_at = timezone.now()
    action.save(update_fields=["implementada_at", "updated_at"])
    transition_problem(problem, ProblematicaAmbiental.Estado.EN_IMPLEMENTACION, user=user)
    _history(problem, "implementacion", detail=action.titulo, user=user, metadata={"accion_id": action.id})
    return action


@transaction.atomic
def add_measurement(problem, *, fecha, valor, unidad=None, fuente="manual", accion=None, metadata=None,
                    indicador_v2=None, valor_indicador=None, referencia="", observaciones="", evidencia=None,
                    user=None, **kwargs):
    if problem.estado not in {ProblematicaAmbiental.Estado.EN_IMPLEMENTACION, ProblematicaAmbiental.Estado.EN_SEGUIMIENTO,
                              ProblematicaAmbiental.Estado.IMPLEMENTANDO, ProblematicaAmbiental.Estado.SEGUIMIENTO}:
        raise ValidationError({"estado": "La problematica debe estar en implementacion o seguimiento."})
    if fecha <= problem.fecha_deteccion:
        raise ValidationError({"fecha": "La medicion posterior debe ser posterior a la deteccion."})
    if accion and accion.problematica_id != problem.id:
        raise ValidationError({"accion": "La accion no pertenece a la problematica."})
    implemented = problem.acciones.filter(implementada_at__isnull=False).order_by("-implementada_at").first()
    if implemented and fecha < implemented.implementada_at.date():
        raise ValidationError({"fecha": "La medicion debe ser posterior a la implementacion."})
    measurement = MedicionSeguimientoAmbiental.objects.create(
        problematica=problem, accion=accion, fecha=fecha, valor=valor,
        unidad=unidad or problem.unidad_indicador, fuente=fuente, metadata=metadata or {},
        indicador_v2=indicador_v2, valor_indicador=valor_indicador, referencia=referencia,
        observaciones=observaciones, evidencia=evidencia,
    )
    if problem.estado == ProblematicaAmbiental.Estado.EN_IMPLEMENTACION:
        transition_problem(problem, ProblematicaAmbiental.Estado.EN_SEGUIMIENTO, user=user)
    elif problem.estado == ProblematicaAmbiental.Estado.IMPLEMENTANDO:
        problem.estado = ProblematicaAmbiental.Estado.SEGUIMIENTO
        problem.save(update_fields=["estado", "updated_at"])
    _history(problem, "medicion", detail=str(valor), user=user, metadata={"medicion_id": measurement.id, "fuente": fuente})
    return measurement


def indicator_value_from_engine(problem, *, start=None, end=None):
    metrics = calculate_environmental_metrics(problem.organizacion, start=start, end=end)
    if problem.indicador == "co2e_total_kg":
        return metrics["co2e_total_kg"]
    if problem.indicador.startswith("categoria:"):
        return metrics["por_categoria"].get(problem.indicador.split(":", 1)[1], Decimal("0"))
    if problem.indicador.startswith("actividad:"):
        return metrics["por_actividad"].get(problem.indicador.split(":", 1)[1], Decimal("0"))
    raise ValidationError({"indicador": "Indicador no soportado por el motor ambiental."})


def measure_from_engine(problem, *, fecha=None, start=None, end=None, accion=None, user=None):
    return add_measurement(
        problem, fecha=fecha or timezone.localdate(), valor=indicator_value_from_engine(problem, start=start, end=end),
        unidad=problem.unidad_indicador, fuente="motor_ambiental", accion=accion,
        metadata={"periodo_desde": str(start or ""), "periodo_hasta": str(end or "")}, user=user,
    )


@transaction.atomic
def evaluate_problem(problem, *, measurement=None, user=None):
    if problem.estado != ProblematicaAmbiental.Estado.EN_SEGUIMIENTO:
        raise ValidationError({"estado": "La problematica debe estar en seguimiento."})
    measurement = measurement or problem.mediciones.order_by("-fecha", "-created_at").first()
    if not measurement:
        raise ValidationError({"medicion": "Se requiere una medicion posterior para verificar la accion."})
    if measurement.problematica_id != problem.id:
        raise ValidationError({"medicion": "La medicion no pertenece a la problematica."})
    posterior = Decimal(measurement.valor)
    initial = Decimal(problem.valor_inicial)
    improvement = initial - posterior
    percentage = (improvement / initial * Decimal("100")).quantize(Decimal("0.01")) if initial else None
    if posterior <= problem.objetivo_meta:
        result, state = ProblematicaAmbiental.Resultado.EFECTIVA, ProblematicaAmbiental.Estado.RESUELTA
    elif posterior < initial:
        result, state = ProblematicaAmbiental.Resultado.PARCIAL, ProblematicaAmbiental.Estado.MEJORA_INSUFICIENTE
    else:
        result, state = ProblematicaAmbiental.Resultado.NO_EFECTIVA, ProblematicaAmbiental.Estado.NO_RESUELTA
    problem.valor_posterior = posterior
    problem.mejora_absoluta = improvement
    problem.mejora_porcentaje = percentage
    problem.resultado_evaluacion = result
    problem.save(update_fields=["valor_posterior", "mejora_absoluta", "mejora_porcentaje", "resultado_evaluacion", "updated_at"])
    transition_problem(problem, state, user=user)
    _history(problem, "verificacion", detail=result, user=user, metadata={"medicion_id": measurement.id})
    return problem
