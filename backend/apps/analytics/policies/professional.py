from django.core.exceptions import ValidationError

from ..models import InformeAmbiental, RevisionProfesionalAmbiental


def validate_review_decision(review, state, authorized):
    if not authorized:
        raise ValidationError("El usuario no tiene capacidad de revision profesional.")
    if review.estado != RevisionProfesionalAmbiental.Estado.PENDIENTE:
        raise ValidationError("La revision ya tiene una decision.")
    if (
        state not in RevisionProfesionalAmbiental.Estado.values
        or state == RevisionProfesionalAmbiental.Estado.PENDIENTE
    ):
        raise ValidationError("Decision profesional invalida.")


def validate_dossier_reopen(dossier, authorized, reason):
    if not authorized:
        raise ValidationError("No autorizado para reabrir expediente.")
    if dossier.estado != "cerrado" or not reason:
        raise ValidationError("La reapertura requiere expediente cerrado y motivo.")


def validate_report_state(report, authorized):
    if not authorized:
        raise ValidationError("El usuario no tiene capacidad de revision profesional.")
    if report.estado == "validado":
        raise ValidationError("El informe ya fue validado.")
    if report.estado not in {
        InformeAmbiental.Estado.GENERADO,
        InformeAmbiental.Estado.REVISADO,
    }:
        raise ValidationError("Solo un informe generado o revisado puede validarse.")
