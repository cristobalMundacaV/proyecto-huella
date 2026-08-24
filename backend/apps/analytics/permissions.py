from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import PermissionDenied
from django.http import Http404

from .models import UsuarioOrganizacion


class Permission:
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_UPDATE = "organization.update"
    TEAM_VIEW = "team.view"
    TEAM_MANAGE = "team.manage"
    WORK_VIEW = "works.view"
    WORK_CREATE = "works.create"
    WORK_UPDATE = "works.update"
    WORK_ARCHIVE = "works.archive"
    ASSET_VIEW = "assets.view"
    ASSET_MANAGE = "assets.manage"
    SENSOR_VIEW = "sensors.view"
    SENSOR_MANAGE = "sensors.manage"
    PROFILE_VIEW = "environmental_profile.view"
    PROFILE_MANAGE = "environmental_profile.manage"
    APPLICABILITY_MANAGE = "environmental_profile.applicability_manage"
    DATA_VIEW = "operational_data.view"
    DATA_CREATE = "operational_data.create"
    DATA_UPDATE = "operational_data.update"
    IMPORT_VIEW = "imports.view"
    IMPORT_CREATE = "imports.create"
    IMPORT_REVIEW = "imports.review"
    IMPORT_CONFIRM = "imports.confirm"
    EVIDENCE_VIEW = "evidence.view"
    EVIDENCE_CREATE = "evidence.create"
    EVIDENCE_UPDATE = "evidence.update"
    EVIDENCE_VALIDATE = "evidence.validate"
    INDICATOR_VIEW = "indicators.view"
    INDICATOR_MANAGE = "indicators.manage"
    INDICATOR_APPROVE = "indicators.approve"
    FACTOR_VIEW = "factors.view"
    FACTOR_CUSTOM_CREATE = "factors.custom_create"
    FACTOR_CUSTOM_REVIEW = "factors.custom_review"
    PROBLEM_VIEW = "problems.view"
    PROBLEM_CREATE = "problems.create"
    PROBLEM_MANAGE = "problems.manage"
    PROBLEM_CLOSE = "problems.close"
    ACTION_MANAGE = "actions.manage"
    COMPLIANCE_VIEW = "compliance.view"
    COMPLIANCE_MANAGE = "compliance.manage"
    COMPLIANCE_REVIEW = "compliance.review"
    REPORT_VIEW = "reports.view"
    REPORT_GENERATE = "reports.generate"
    REPORT_APPROVE = "reports.approve"
    REVIEW_PROFESSIONAL = "professional_review.execute"
    AUDIT_VIEW = "audit.view"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"


ALL_PERMISSIONS = frozenset(value for name, value in vars(Permission).items() if name.isupper())
VIEW_PERMISSIONS = {
    Permission.ORGANIZATION_VIEW, Permission.WORK_VIEW, Permission.ASSET_VIEW,
    Permission.SENSOR_VIEW, Permission.PROFILE_VIEW, Permission.DATA_VIEW,
    Permission.EVIDENCE_VIEW, Permission.INDICATOR_VIEW, Permission.PROBLEM_VIEW,
    Permission.COMPLIANCE_VIEW, Permission.REPORT_VIEW,
}

ROLE_PERMISSIONS = {
    UsuarioOrganizacion.Rol.ADMIN: ALL_PERMISSIONS,
    UsuarioOrganizacion.Rol.RESPONSABLE_AMBIENTAL: VIEW_PERMISSIONS | {
        Permission.WORK_CREATE, Permission.WORK_UPDATE, Permission.ASSET_MANAGE,
        Permission.SENSOR_MANAGE, Permission.PROFILE_MANAGE, Permission.APPLICABILITY_MANAGE,
        Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.IMPORT_VIEW,
        Permission.IMPORT_CREATE, Permission.IMPORT_REVIEW, Permission.IMPORT_CONFIRM,
        Permission.EVIDENCE_CREATE, Permission.EVIDENCE_UPDATE, Permission.EVIDENCE_VALIDATE,
        Permission.INDICATOR_MANAGE, Permission.FACTOR_VIEW, Permission.FACTOR_CUSTOM_CREATE,
        Permission.PROBLEM_CREATE, Permission.PROBLEM_MANAGE, Permission.PROBLEM_CLOSE,
        Permission.ACTION_MANAGE, Permission.COMPLIANCE_MANAGE, Permission.REPORT_GENERATE,
        Permission.AUDIT_VIEW,
    },
    UsuarioOrganizacion.Rol.ANALISTA: VIEW_PERMISSIONS | {
        Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.IMPORT_VIEW,
        Permission.IMPORT_CREATE, Permission.IMPORT_REVIEW, Permission.EVIDENCE_CREATE,
        Permission.EVIDENCE_UPDATE, Permission.INDICATOR_MANAGE, Permission.FACTOR_VIEW,
        Permission.FACTOR_CUSTOM_CREATE, Permission.PROBLEM_CREATE, Permission.PROBLEM_MANAGE,
        Permission.ACTION_MANAGE, Permission.REPORT_GENERATE,
    },
    UsuarioOrganizacion.Rol.OPERADOR: VIEW_PERMISSIONS | {
        Permission.DATA_CREATE, Permission.DATA_UPDATE, Permission.EVIDENCE_CREATE,
        Permission.EVIDENCE_UPDATE, Permission.PROBLEM_CREATE, Permission.ACTION_MANAGE,
    },
    UsuarioOrganizacion.Rol.REVISOR_AMBIENTAL: VIEW_PERMISSIONS | {
        Permission.IMPORT_VIEW, Permission.IMPORT_REVIEW, Permission.IMPORT_CONFIRM,
        Permission.EVIDENCE_VALIDATE, Permission.INDICATOR_APPROVE, Permission.FACTOR_VIEW,
        Permission.FACTOR_CUSTOM_REVIEW, Permission.PROBLEM_MANAGE, Permission.PROBLEM_CLOSE,
        Permission.COMPLIANCE_REVIEW, Permission.REPORT_GENERATE, Permission.REPORT_APPROVE,
        Permission.REVIEW_PROFESSIONAL, Permission.AUDIT_VIEW,
    },
    UsuarioOrganizacion.Rol.LECTOR: VIEW_PERMISSIONS | {
        Permission.IMPORT_VIEW, Permission.FACTOR_VIEW,
    },
}


def get_membership(user, organization):
    if not user or not user.is_authenticated or user.is_superuser:
        return None
    return UsuarioOrganizacion.objects.filter(user=user, organizacion=organization, activo=True).first()


def has_tenant_permission(user, organization, permission):
    if not user or not user.is_authenticated or permission not in ALL_PERMISSIONS:
        return False
    if user.is_superuser:
        return True
    membership = get_membership(user, organization)
    return bool(membership and permission in ROLE_PERMISSIONS.get(membership.rol, ()))


def has_any_tenant_permission(user, permission):
    if not user or not user.is_authenticated or permission not in ALL_PERMISSIONS:
        return False
    if user.is_superuser:
        return True
    roles = UsuarioOrganizacion.objects.filter(user=user, activo=True).values_list("rol", flat=True)
    return any(permission in ROLE_PERMISSIONS.get(role, ()) for role in roles)


def require_tenant_permission(user, organization, permission):
    if not has_tenant_permission(user, organization, permission):
        raise PermissionDenied("No tienes permisos para realizar esta acción.")


def filter_works_for_user(queryset, user, organization):
    base = queryset.filter(organizacion=organization)
    if user.is_superuser:
        return base
    membership = get_membership(user, organization)
    if not membership or Permission.WORK_VIEW not in ROLE_PERMISSIONS.get(membership.rol, ()):
        return queryset.none()
    if membership.alcance == UsuarioOrganizacion.Alcance.ORGANIZACION:
        return base
    return base.filter(accesos_usuario__usuario_organizacion=membership).distinct()


def user_can_access_work(user, organization, work):
    if work.organizacion_id != organization.id:
        return False
    queryset = work.__class__.objects.all()
    return filter_works_for_user(queryset, user, organization).filter(pk=work.pk).exists()


def require_work_access(user, organization, work):
    if work is not None and not user_can_access_work(user, organization, work):
        raise Http404("Recurso no encontrado.")
    return work


def resource_work(resource):
    """Resuelve la obra de recursos críticos sin consultar IDs aportados por el cliente."""
    paths = (
        "obra", "actividad.obra", "observacion.actividad.obra", "calculo.actividad.obra",
        "indicador.obra", "documento.obra", "variable.documento.obra", "problematica.obra", "intervencion.problematica.obra",
        "expediente.problematica.obra", "version_evidencia.evidencia.obra",
    )
    for path in paths:
        current = resource
        try:
            for part in path.split("."):
                current = getattr(current, part)
        except (AttributeError, ObjectDoesNotExist):
            continue
        if current is not None:
            return current
    return None


def require_resource_work_access(user, organization, resource):
    require_work_access(user, organization, resource_work(resource))
    return resource
