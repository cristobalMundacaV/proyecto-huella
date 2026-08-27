from ..models import EspacioTrabajoOperacional, EvidenciaObra


def workspaces_for_user(user):
    if not user or not user.is_authenticated:
        return EspacioTrabajoOperacional.objects.none()
    return EspacioTrabajoOperacional.objects.select_related(
        "usuario_organizacion__organizacion", "area", "obra"
    ).filter(
        usuario_organizacion__user=user,
        usuario_organizacion__activo=True,
        area__activa=True,
        activo=True,
    )


def areas_for_organization(organization):
    return organization.areas_operacionales.all()


def workspaces_for_membership(membership):
    return membership.espacios_trabajo.select_related(
        "area", "obra", "usuario_organizacion__organizacion"
    )


def recent_evidence_for_context(context, user, limit=20):
    return EvidenciaObra.objects.filter(
        organizacion=context.organizacion,
        obra=context.obra,
        area_origen=context.area,
        usuario_origen=user,
    ).order_by("-created_at")[:limit]
