from django.db.models import Q

from ..models import (
    ActividadOperacional,
    ExpedienteAmbiental,
    InformeAmbiental,
    ProblematicaAmbiental,
    ResultadoIntervencion,
    RevisionProfesionalAmbiental,
)


def reviews_for_organization(organization, work=None, state=None, review_type=None):
    rows = organization.revisiones_profesionales.prefetch_related("hallazgos").order_by(
        "-created_at"
    )
    if work is not None:
        rows = rows.filter(
            Q(evidencia__obra=work)
            | Q(observacion__actividad__obra=work)
            | Q(calculo__actividad__obra=work)
            | Q(indicador__obra=work)
            | Q(problematica__obra=work)
            | Q(intervencion__problematica__obra=work)
            | Q(expediente__problematica__obra=work)
        ).distinct()
    if state:
        rows = rows.filter(estado=state)
    return rows.filter(tipo=review_type) if review_type else rows


def review_for_organization(organization, review_id, state=None):
    rows = RevisionProfesionalAmbiental.objects.filter(
        organizacion=organization, id=review_id
    )
    return rows.filter(estado=state) if state else rows


def audit_events(organization, event_type=None):
    rows = organization.eventos_auditoria_ambiental.select_related("actor")
    return rows.filter(tipo=event_type) if event_type else rows


def dossiers_for_organization(organization, work=None):
    rows = ExpedienteAmbiental.objects.filter(
        problematica__organizacion=organization
    ).select_related("problematica", "responsable")
    return rows.filter(problematica__obra=work) if work is not None else rows


def dossier_for_organization(organization, dossier_id, work=None, detailed=False):
    rows = ExpedienteAmbiental.objects.filter(
        problematica__organizacion=organization, id=dossier_id
    )
    if detailed:
        rows = rows.select_related("problematica", "responsable")
    return rows.filter(problematica__obra=work) if work is not None else rows


def problem_for_dossier(organization, problem_id, work=None):
    rows = ProblematicaAmbiental.objects.filter(
        organizacion=organization, id=problem_id
    )
    return rows.filter(obra=work) if work is not None else rows


def report_reference(organization, model, reference_id):
    if model is ActividadOperacional:
        return model.objects.filter(organizacion=organization, id=reference_id)
    return (
        model.objects.filter(problematica__organizacion=organization, id=reference_id)
        if model in {ResultadoIntervencion, ExpedienteAmbiental}
        else model.objects.filter(organizacion=organization, id=reference_id)
    )


def report_for_organization(organization, report_id, detailed=False):
    rows = InformeAmbiental.objects.filter(organizacion=organization, id=report_id)
    return rows.select_related("snapshot") if detailed else rows
