def closure_errors(status, payload):
    errors = []
    warning = bool(payload.get("close_with_warning"))
    result = str(payload.get("closure_result") or "").strip()
    if not status["closure_readiness"]["can_close"] and not warning:
        errors.append("Falta evidencia o justificacion para cerrar la accion.")
    if warning and not result:
        errors.append(
            "Para cerrar con advertencia debes registrar un resultado de cierre."
        )
    return errors


def work_payload_error(supplied_work, requested_work):
    if (
        requested_work is not None
        and supplied_work
        and str(supplied_work) != str(requested_work.id)
    ):
        return "La obra no coincide con el contexto solicitado."
    return None
