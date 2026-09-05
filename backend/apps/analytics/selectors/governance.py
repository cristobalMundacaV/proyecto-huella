from django.db.models import Q

from ..models import (
    FactorAmbiental,
    MetodologiaAmbiental,
    RevisionProfesionalAmbiental,
    VersionMetodologia,
    VersionFactorAmbiental,
)


def methodologies_for_organization(organization):
    return MetodologiaAmbiental.objects.filter(
        Q(organizacion=organization) | Q(organizacion__isnull=True)
    ).prefetch_related(
        "versiones__formula__variables", "versiones__formula__factor_ambiental"
    )


def methodology_for_organization(organization, methodology_id):
    return MetodologiaAmbiental.objects.prefetch_related(
        "versiones__formula__variables"
    ).filter(
        Q(organizacion=organization) | Q(organizacion__isnull=True), id=methodology_id
    )


def methodology_version_for_organization(
    organization, methodology_id, version_id, *, tenant_only=False
):
    scope = Q(metodologia__organizacion=organization)
    if not tenant_only:
        scope |= Q(metodologia__organizacion__isnull=True)
    return VersionMetodologia.objects.filter(
        scope, id=version_id, metodologia_id=methodology_id
    )


def factor_for_organization(organization, factor_id):
    return FactorAmbiental.objects.filter(
        Q(organizacion=organization) | Q(organizacion__isnull=True), id=factor_id
    )


def factors_for_organization(organization):
    return FactorAmbiental.objects.filter(
        Q(organizacion=organization) | Q(organizacion__isnull=True)
    ).prefetch_related("versiones")


def factor_version_for_organization(organization, factor_id, version_id, *, tenant_only=False):
    scope = Q(factor__organizacion=organization)
    if not tenant_only:
        scope |= Q(factor__organizacion__isnull=True)
    return VersionFactorAmbiental.objects.filter(scope, factor_id=factor_id, id=version_id)


def professional_review_for_organization(organization, review_id):
    return RevisionProfesionalAmbiental.objects.filter(
        id=review_id, organizacion=organization
    )
