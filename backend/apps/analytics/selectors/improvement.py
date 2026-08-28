from ..models import AccionMejoraAmbiental, ProblematicaAmbiental
from ..models_acciones import AccionAmbiental


def problems_for_organization(organization, work=None):
    rows = organization.problematicas_ambientales.all()
    return rows.filter(obra=work) if work is not None else rows


def problem_for_organization(organization, problem_id, work=None):
    rows = ProblematicaAmbiental.objects.filter(
        organizacion=organization, pk=problem_id
    )
    return rows.filter(obra=work) if work is not None else rows


def actions_for_problem(problem):
    return problem.acciones.all()


def action_for_problem(problem, action_id):
    return AccionMejoraAmbiental.objects.filter(problematica=problem, pk=action_id)


def measurements_for_problem(problem):
    return problem.mediciones.all()


def history_for_problem(problem):
    return problem.historial.all()


def scopes_for_problem(problem):
    return problem.alcances_v2.all()


def indicators_for_problem(problem):
    return problem.indicadores_v2.select_related("indicador")


def base_snapshot_for_problem(problem):
    return problem.snapshots_intervencion.filter(tipo="base").order_by("-ciclo").first()


def cycles_for_problem(problem):
    return problem.ciclos_reevaluacion.select_related("resultado")


def active_cycle_for_problem(problem):
    return problem.ciclos_reevaluacion.filter(fecha_cierre=None).exists()


def environmental_action(action_id):
    return AccionAmbiental.objects.select_related("organizacion", "evidencia").filter(
        pk=action_id
    )
