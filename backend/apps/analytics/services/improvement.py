from django.db import transaction

from ..policies.improvement import validate_generic_problem_update


@transaction.atomic
def create_problem(organization, data, user=None):
    from ..models import ProblematicaAmbiental

    problem = ProblematicaAmbiental(organizacion=organization, **data)
    problem.full_clean()
    problem.save()
    problem.historial.create(
        evento="deteccion",
        estado_nuevo=problem.estado,
        usuario=user.get_username() if user else "",
    )
    return problem


def update_problem(problem, data, *, requested_data=None):
    validate_generic_problem_update(problem, requested_data or data)
    for field, value in data.items():
        setattr(problem, field, value)
    problem.full_clean()
    problem.save()
    return problem


def delete_problem(problem):
    problem.delete()


def create_problem_scope(problem, data):
    from ..models import AlcanceProblematica

    scope = AlcanceProblematica(problematica=problem, **data)
    scope.full_clean()
    scope.save()
    return scope


def create_problem_indicator(problem, data):
    from ..models import IndicadorProblematica

    link = IndicadorProblematica(problematica=problem, **data)
    link.full_clean()
    link.save()
    return link
