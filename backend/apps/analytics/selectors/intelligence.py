from ..models import ComandoCopiloto, RecomendacionAgenteAmbiental, UsuarioOrganizacion


def user_can_access_organization(user, organization):
    return user.is_authenticated and (
        user.is_superuser
        or UsuarioOrganizacion.objects.filter(
            user=user, organizacion=organization, activo=True, organizacion__activa=True
        ).exists()
    )


def owned_resource(model, resource_id):
    return model.objects.select_related("organizacion").filter(pk=resource_id)


def problem_proposals(problem):
    return problem.recomendaciones_agente.order_by("-created_at")[:20]


def proposal_for_problem(problem, proposal_id):
    return RecomendacionAgenteAmbiental.objects.filter(
        problematica=problem, id=proposal_id
    )


def copilot_command(command_id):
    return ComandoCopiloto.objects.select_related(
        "organizacion", "problematica", "propuesta"
    ).filter(id=command_id)
