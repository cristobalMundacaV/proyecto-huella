from ..models import EvaluacionCalidadDato, Observacion
from ..services.evidence_documents import current_document_result, current_evidence_version


def evidence_health(observation):
    evidence = observation.evidencia
    if not evidence:
        return "sin_evidencia", "Sin evidencia documental adjunta; la procedencia permanece declarativa."
    version = current_evidence_version(evidence, observation)
    if not version:
        state = evidence.estado_documental
        if state == evidence.EstadoDocumental.VALIDADA:
            return "validada", "La evidencia histórica fue validada y fortalece la procedencia del dato."
        if state == evidence.EstadoDocumental.RECHAZADA:
            return "rechazada", "La evidencia histórica fue rechazada; el dato manual se conserva y requiere revisión."
        if state == evidence.EstadoDocumental.OBSERVADA:
            return "observada", "La evidencia histórica tiene observaciones y requiere revisión."
        return "pendiente", "La evidencia histórica está adjunta, pero su validación documental continúa pendiente."
    validation = current_document_result(evidence, observation)
    validation_state = validation.get("veredicto")
    if version and version.estado_procesamiento in {"recibida", "analizando"}:
        return "pendiente_procesamiento", "El respaldo está adjunto y su procesamiento documental continúa en segundo plano."
    if version and version.estado_procesamiento == "error":
        return "revision_tecnica", "El procesamiento del respaldo presentó un fallo técnico; el dato manual se conserva y el documento puede reintentarse."
    if validation_state == "verificada":
        return "verificada", "El respaldo fue contrastado con el dato declarado y sus campos relevantes son compatibles."
    if validation_state == "contradiccion":
        unresolved = observation.discrepancias.exclude(
            estado__in=["resuelta", "descartada"]
        ).filter(concepto__startswith="evidencia_").exists()
        if not unresolved:
            return "compatible_incompleta", "Las contradicciones documentales fueron revisadas y resueltas; se conserva la decisión humana auditada."
        return "contradiccion", "El respaldo documental contradice uno o más campos declarados; el dato requiere revisión prioritaria."
    if validation_state == "no_pertinente":
        return "no_pertinente", "El archivo no corresponde al tipo de respaldo esperado y no mejora la calidad del dato."
    if validation_state == "compatible_incompleta":
        return "compatible_incompleta", "El respaldo es compatible, pero no contiene todos los campos necesarios para verificar el dato completamente."
    if validation_state == "indeterminada":
        return "indeterminada", "No fue posible verificar de forma segura el contenido del respaldo documental."
    return "indeterminada", "La versión no contiene un resultado documental canónico utilizable."


def source_health(observation):
    source = observation.fuente
    if not source.activa:
        return "fuera_servicio", "La fuente esta inactiva."
    try:
        reading = observation.lectura_sensor_v2
    except Exception:
        reading = None
    if reading:
        sensor = reading.sensor
        if sensor.estado in {
            "fuera_servicio",
            "calibracion_vencida",
            "requiere_revision",
        }:
            return (
                sensor.estado,
                f"El sensor esta {sensor.get_estado_display().lower()}.",
            )
        if reading.calidad_tecnica == "requiere_revision":
            return "requiere_revision", "La lectura requiere revision tecnica."
        return "operativo", "Sensor operativo y lectura tecnicamente valida."
    if source.tipo == "manual":
        return "declarativa", "Dato manual con procedencia declarativa."
    return "disponible", "Fuente disponible; no se infiere certeza adicional."


def quality_assessment(observation, reviewed_by_user=False):
    health, reason = source_health(observation)
    evidence_state, evidence_reason = evidence_health(observation)
    reasons = [reason, evidence_reason]
    if observation.estado == Observacion.Estado.RECHAZADA:
        state = EvaluacionCalidadDato.Estado.NO_CONFIABLE
        reasons.append("La observacion fue rechazada.")
    elif observation.valor_numerico is None and not observation.valor_texto:
        state = EvaluacionCalidadDato.Estado.INCOMPLETO
        reasons.append("La observacion no contiene valor.")
    elif health == "fuera_servicio":
        state = EvaluacionCalidadDato.Estado.NO_CONFIABLE
    elif health in {"calibracion_vencida", "requiere_revision"}:
        state = EvaluacionCalidadDato.Estado.REQUIERE_REVISION
    elif evidence_state in {"rechazada", "observada", "contradiccion", "no_pertinente", "indeterminada", "revision_tecnica"}:
        state = EvaluacionCalidadDato.Estado.REQUIERE_REVISION
    elif evidence_state in {"validada", "verificada"}:
        state = EvaluacionCalidadDato.Estado.CONFIABLE
    elif (
        health == "declarativa"
        or evidence_state in {"pendiente", "pendiente_procesamiento"}
        or observation.estado == Observacion.Estado.PENDIENTE
    ):
        state = EvaluacionCalidadDato.Estado.CONFIABLE_OBSERVACIONES
    else:
        state = EvaluacionCalidadDato.Estado.CONFIABLE
    return {
        "estado": state,
        "motivos": reasons,
        "dimensiones": {
            "procedencia": (
                "documental_validada"
                if evidence_state in {"validada", "verificada"}
                else observation.naturaleza
            ),
            "estado_fuente": health,
            "estado_observacion": observation.estado,
            "respaldo_documental": evidence_state,
            "efecto_respaldo": evidence_reason,
            "completitud": (
                "completa"
                if observation.valor_numerico is not None or observation.valor_texto
                else "incompleta"
            ),
            "coherencia": "sin_alertas",
            "discrepancia": "no_evaluada",
            "elegibilidad_calculo": "evaluable",
            "revision_humana": reviewed_by_user,
        },
    }


def discrepancy_errors(discrepancy, data):
    errors = {}
    selected = data.get(
        "observacion_seleccionada", discrepancy.observacion_seleccionada
    )
    if selected and selected.organizacion_id != discrepancy.organizacion_id:
        errors["observacion_seleccionada"] = (
            "La observacion pertenece a otra organizacion."
        )
    elif selected and not discrepancy.observaciones.filter(pk=selected.pk).exists():
        errors["observacion_seleccionada"] = (
            "La observacion no pertenece a esta discrepancia."
        )
    if data.get("estado", discrepancy.estado) == "resuelta":
        if not selected:
            errors["observacion_seleccionada"] = (
                "Debe seleccionar la observacion que resuelve la discrepancia."
            )
        if not str(data.get("resolucion", discrepancy.resolucion) or "").strip():
            errors["resolucion"] = "Debe documentar la resolucion."
    return errors
