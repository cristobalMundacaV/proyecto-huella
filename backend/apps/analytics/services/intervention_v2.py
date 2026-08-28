from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import (
    AccionMejoraAmbiental,
    CicloReevaluacionProblematica,
    HistorialMetaProblematica,
    ResultadoIntervencion,
    SnapshotIntervencion,
    SnapshotValorIndicador,
)
from ..policies.improvement import (
    validate_action_start,
    validate_cycle_selection,
    validate_verified_resolution,
)


def _scope_snapshot(problem):
    scopes = problem.alcances_v2.all()
    return {
        "obra_id": problem.obra_id,
        "unidades": list(
            scopes.exclude(unidad_operacional=None).values_list(
                "unidad_operacional_id", flat=True
            )
        ),
        "procesos": list(
            scopes.exclude(proceso_operacional=None).values_list(
                "proceso_operacional_id", flat=True
            )
        ),
        "activos": list(
            scopes.exclude(activo_operacional=None).values_list(
                "activo_operacional_id", flat=True
            )
        ),
        "actividades": list(
            scopes.exclude(actividad_operacional=None).values_list(
                "actividad_operacional_id", flat=True
            )
        ),
        "indicadores_alcance": list(
            scopes.exclude(indicador=None).values_list("indicador_id", flat=True)
        ),
    }


def _snapshot(problem, action, cycle_number, kind, frozen=False):
    links = list(problem.indicadores_v2.select_related("indicador"))
    incompatible = [
        link.indicador.codigo
        for link in links
        if link.indicador.obra_id != problem.obra_id
    ]
    if incompatible:
        raise ValidationError(
            f"Los indicadores no comparten el alcance de obra de la problematica: {', '.join(incompatible)}."
        )
    snapshot = SnapshotIntervencion.objects.create(
        problematica=problem,
        accion=action,
        ciclo=cycle_number,
        tipo=kind,
        fecha=timezone.localdate(),
        alcance_congelado=_scope_snapshot(problem),
        indicadores_evaluados=[
            {
                "indicador": link.indicador_id,
                "rol": link.rol,
                "direccion": link.direccion_deseada,
                "meta": (
                    str(link.valor_objetivo)
                    if link.valor_objetivo is not None
                    else None
                ),
            }
            for link in links
        ],
        metadata_tecnica={"servicio": "intervention-v1"},
        congelado=False,
    )
    for link in links:
        value = link.indicador.valores.order_by("-periodo_fin", "-version").first()
        if value:
            SnapshotValorIndicador.objects.create(
                snapshot=snapshot,
                indicador=link.indicador,
                valor=value.valor,
                unidad=value.unidad,
                periodo_inicio=value.periodo_inicio,
                periodo_fin=value.periodo_fin,
                valor_indicador_origen=value,
            )
    if frozen:
        snapshot.congelado = True
        snapshot.save(update_fields=["congelado"])
    return snapshot


@transaction.atomic
def select_action(action, user=None):
    problem = action.problematica
    validate_cycle_selection(problem)
    number = problem.ciclos_reevaluacion.count() + 1
    action.estado = AccionMejoraAmbiental.Estado.SELECCIONADA
    action.fecha_seleccion = timezone.localdate()
    action.save(update_fields=["estado", "fecha_seleccion", "updated_at"])
    base = _snapshot(problem, action, number, SnapshotIntervencion.Tipo.BASE)
    cycle = CicloReevaluacionProblematica.objects.create(
        problematica=problem,
        numero=number,
        accion=action,
        snapshot_base=base,
        fecha_inicio=timezone.localdate(),
        motivo="Accion seleccionada para evaluacion verificable.",
    )
    problem.estado = problem.Estado.ACCION_SELECCIONADA
    problem.save(update_fields=["estado", "updated_at"])
    problem.historial.create(
        evento="accion_seleccionada",
        estado_nuevo=problem.estado,
        usuario=user.get_username() if user else "",
        metadata={"accion": action.id, "ciclo": number, "snapshot_base": base.id},
    )
    return cycle


@transaction.atomic
def start_action(action, confirmed=False, user=None):
    cycle = (
        action.ciclos_reevaluacion.filter(fecha_cierre=None).order_by("-numero").first()
    )
    validate_action_start(confirmed, cycle)
    base = cycle.snapshot_base
    if not base.congelado:
        base.congelado = True
        base.save(update_fields=["congelado"])
    action.estado = AccionMejoraAmbiental.Estado.EN_IMPLEMENTACION
    action.fecha_inicio_efectiva = timezone.localdate()
    action.implementada_at = timezone.now()
    action.save(
        update_fields=[
            "estado",
            "fecha_inicio_efectiva",
            "implementada_at",
            "updated_at",
        ]
    )
    problem = action.problematica
    problem.estado = problem.Estado.IMPLEMENTANDO
    problem.save(update_fields=["estado", "updated_at"])
    problem.historial.create(
        evento="inicio_implementacion",
        estado_nuevo=problem.estado,
        usuario=user.get_username() if user else "",
        metadata={"snapshot_base": base.id},
    )
    return cycle


def _metric_state(link, base, result):
    difference = result.valor - base.valor
    if difference == 0:
        state = "sin_cambio"
    elif link.direccion_deseada == "menor_es_mejor":
        state = "mejoro" if difference < 0 else "empeoro"
    elif link.direccion_deseada == "mayor_es_mejor":
        state = "mejoro" if difference > 0 else "empeoro"
    else:
        state = "sin_cambio"
    percent = difference / abs(base.valor) * Decimal("100") if base.valor else None
    target_met = None
    if link.valor_objetivo is not None:
        target_met = (
            result.valor <= link.valor_objetivo
            if link.direccion_deseada == "menor_es_mejor"
            else result.valor >= link.valor_objetivo
        )
    return {
        "indicador": link.indicador_id,
        "base": str(base.valor),
        "resultado": str(result.valor),
        "diferencia": str(difference),
        "porcentaje": str(percent) if percent is not None else None,
        "estado": state,
        "meta_cumplida": target_met,
    }


@transaction.atomic
def evaluate_intervention(problem, user=None):
    cycle = (
        problem.ciclos_reevaluacion.filter(fecha_cierre=None)
        .select_related("accion", "snapshot_base")
        .order_by("-numero")
        .first()
    )
    if not cycle:
        raise ValidationError("No existe un ciclo activo.")
    result_snapshot = _snapshot(
        problem,
        cycle.accion,
        cycle.numero,
        SnapshotIntervencion.Tipo.RESULTADO,
        frozen=True,
    )
    metrics, limitations = [], []
    for link in problem.indicadores_v2.select_related("indicador"):
        base = cycle.snapshot_base.valores.filter(indicador=link.indicador).first()
        result = result_snapshot.valores.filter(indicador=link.indicador).first()
        if not base or not result:
            limitations.append(f"Sin valores comparables para {link.indicador.codigo}.")
            continue
        metrics.append(_metric_state(link, base, result))
    if not metrics or any(
        link.obligatorio
        and not any(item["indicador"] == link.indicador_id for item in metrics)
        for link in problem.indicadores_v2.all()
    ):
        state = ResultadoIntervencion.Estado.INCONCLUSA
    elif all(item["estado"] == "mejoro" for item in metrics):
        state = ResultadoIntervencion.Estado.POSITIVA
    elif any(item["estado"] == "empeoro" for item in metrics):
        state = ResultadoIntervencion.Estado.NEGATIVA
    elif any(item["estado"] == "mejoro" for item in metrics):
        state = ResultadoIntervencion.Estado.PARCIAL
    else:
        state = ResultadoIntervencion.Estado.SIN_EFECTO
    result = ResultadoIntervencion.objects.create(
        problematica=problem,
        accion=cycle.accion,
        ciclo=cycle.numero,
        snapshot_base=cycle.snapshot_base,
        snapshot_resultado=result_snapshot,
        estado=state,
        fecha_evaluacion=timezone.localdate(),
        metricas_comparadas=metrics,
        limitaciones=limitations,
        conclusion_estructurada={
            "resultado": state,
            "texto": "Resultado observado durante el periodo de seguimiento; no implica causalidad por si solo.",
        },
    )
    cycle.snapshot_resultado = result_snapshot
    cycle.resultado = result
    cycle.fecha_cierre = timezone.localdate()
    cycle.save(update_fields=["snapshot_resultado", "resultado", "fecha_cierre"])
    cycle.accion.estado = AccionMejoraAmbiental.Estado.EVALUADA
    cycle.accion.save(update_fields=["estado", "updated_at"])
    problem.estado = (
        problem.Estado.RESUELTA
        if state == ResultadoIntervencion.Estado.POSITIVA
        else problem.Estado.NO_RESUELTA
    )
    if problem.estado == problem.Estado.RESUELTA:
        validate_verified_resolution(cycle, result)
    problem.save(update_fields=["estado", "updated_at"])
    problem.historial.create(
        evento="evaluacion_intervencion",
        estado_nuevo=problem.estado,
        usuario=user.get_username() if user else "",
        metadata={"resultado": result.id, "ciclo": cycle.numero},
    )
    return result


def change_target(link, new_value, justification, reason, user):
    if not justification or not reason or not user or not user.is_authenticated:
        raise ValidationError(
            "Cambiar una meta exige justificacion tecnica, motivo y usuario."
        )
    history = HistorialMetaProblematica.objects.create(
        problematica=link.problematica,
        indicador_problematica=link,
        valor_anterior=link.valor_objetivo,
        valor_nuevo=new_value,
        justificacion_tecnica=justification,
        motivo=reason,
        usuario=user,
    )
    link.valor_objetivo = new_value
    link.save(update_fields=["valor_objetivo"])
    return history


def escalate_problem(problem, reason, user=None):
    if problem.ciclos_reevaluacion.count() < 3:
        raise ValidationError(
            "El escalamiento automatico requiere tres ciclos cerrados."
        )
    problem.estado = problem.Estado.ESCALADA_PROFESIONAL
    problem.requiere_evaluacion_profesional = True
    problem.escalada_at = timezone.now()
    problem.criterios_escalamiento = [
        reason or "Tres ciclos sin resolucion satisfactoria."
    ]
    problem.save(
        update_fields=[
            "estado",
            "requiere_evaluacion_profesional",
            "escalada_at",
            "criterios_escalamiento",
            "updated_at",
        ]
    )
    problem.historial.create(
        evento="escalamiento_profesional",
        estado_nuevo=problem.estado,
        usuario=user.get_username() if user else "",
        detalle=reason,
    )
    return problem
