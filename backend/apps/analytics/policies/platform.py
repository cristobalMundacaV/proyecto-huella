from ..permissions import Permission, has_tenant_permission


def can_administer_organization(user, organization):
    return has_tenant_permission(user, organization, Permission.ORGANIZATION_UPDATE)
