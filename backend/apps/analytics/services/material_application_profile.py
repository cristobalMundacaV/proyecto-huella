"""Lifecycle for the governed MaterialApplicationProfile authority (MI-01A).

A profile answers "what function must a material serve, and with which
explicit, deterministic requirements" for one context (organization, and
optionally one work). It never encodes global material<->material
equivalence. Draft -> approved -> retired/rejected/replaced are the only
transitions; each is recorded as an immutable
MaterialApplicationProfileDecision. An approved profile is immutable in
content; a substantive change requires a new revision via create_revision().
"""

from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models.material_application_profile import (
    MaterialApplicationProfile,
    MaterialApplicationProfileDecision,
    application_profile_write,
)
from ..permissions import Permission, require_tenant_permission
from .material_application_requirements import validate_requirements


@contextmanager
def governed_write():
    token = application_profile_write.set(True)
    try:
        yield
    finally:
        application_profile_write.reset(token)


def _profile_for_update(profile_id, organization):
    return MaterialApplicationProfile.objects.select_for_update().get(
        pk=profile_id, organizacion=organization
    )


@transaction.atomic
def create_profile(
    organization,
    user,
    codigo,
    nombre,
    cantidad_unidad_funcional,
    unidad_funcional,
    descripcion="",
    requisitos=None,
    obra=None,
):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_APPLICATION_PROFILE_MANAGE
    )
    if obra is not None and obra.organizacion_id != organization.id:
        raise ValidationError({"obra": "La obra debe pertenecer a la misma organizacion."})
    normalized_requirements = validate_requirements(requisitos)
    try:
        with governed_write(), transaction.atomic():
            profile = MaterialApplicationProfile(
                organizacion=organization,
                obra=obra,
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                cantidad_unidad_funcional=cantidad_unidad_funcional,
                unidad_funcional=unidad_funcional,
                requisitos=normalized_requirements,
                estado=MaterialApplicationProfile.Estado.BORRADOR,
                version=1,
                created_by=user,
            )
            profile.save()
            MaterialApplicationProfileDecision.objects.create(
                profile=profile,
                decision=MaterialApplicationProfileDecision.Decision.CREADO,
                actor=user,
            )
    except IntegrityError as exc:
        raise ValidationError(
            "Ya existe un perfil con este código y versión inicial."
        ) from exc
    return profile


@transaction.atomic
def update_draft(
    profile_id,
    organization,
    user,
    nombre=None,
    descripcion=None,
    cantidad_unidad_funcional=None,
    unidad_funcional=None,
    requisitos=None,
):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_APPLICATION_PROFILE_MANAGE
    )
    profile = _profile_for_update(profile_id, organization)
    if profile.estado != MaterialApplicationProfile.Estado.BORRADOR:
        raise ValidationError("Sólo un perfil en borrador puede editarse.")
    with governed_write():
        if nombre is not None:
            profile.nombre = nombre
        if descripcion is not None:
            profile.descripcion = descripcion
        if cantidad_unidad_funcional is not None:
            profile.cantidad_unidad_funcional = cantidad_unidad_funcional
        if unidad_funcional is not None:
            profile.unidad_funcional = unidad_funcional
        if requisitos is not None:
            profile.requisitos = validate_requirements(requisitos)
        profile.save()
    return profile


@transaction.atomic
def approve_profile(profile_id, organization, user, note=""):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_APPLICATION_PROFILE_APPROVE
    )
    profile = _profile_for_update(profile_id, organization)
    if profile.estado != MaterialApplicationProfile.Estado.BORRADOR:
        raise ValidationError("Sólo un perfil en borrador puede aprobarse.")
    predecessor = None
    if profile.reemplaza_a_id:
        predecessor = MaterialApplicationProfile.objects.select_for_update().get(
            pk=profile.reemplaza_a_id, organizacion=organization
        )
        if predecessor.estado != MaterialApplicationProfile.Estado.APROBADO:
            raise ValidationError(
                "El perfil predecesor debe estar aprobado para reemplazarse."
            )
    try:
        with governed_write():
            if predecessor is not None:
                predecessor.estado = MaterialApplicationProfile.Estado.REEMPLAZADO
                predecessor.retired_by = user
                predecessor.retired_at = timezone.now()
                predecessor.save()
                MaterialApplicationProfileDecision.objects.create(
                    profile=predecessor,
                    decision=MaterialApplicationProfileDecision.Decision.REEMPLAZADO,
                    actor=user,
                    nota=note,
                    contexto={"reemplazado_por_id": profile.pk},
                )
            profile.estado = MaterialApplicationProfile.Estado.APROBADO
            profile.reviewed_by = user
            profile.reviewed_at = timezone.now()
            profile.save()
            MaterialApplicationProfileDecision.objects.create(
                profile=profile,
                decision=MaterialApplicationProfileDecision.Decision.APROBADO,
                actor=user,
                nota=note,
            )
    except IntegrityError as exc:
        raise ValidationError(
            "Ya existe otro perfil aprobado y vigente para este código."
        ) from exc
    return profile


@transaction.atomic
def reject_profile(profile_id, organization, user, note=""):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_APPLICATION_PROFILE_APPROVE
    )
    profile = _profile_for_update(profile_id, organization)
    if profile.estado != MaterialApplicationProfile.Estado.BORRADOR:
        raise ValidationError("Sólo un perfil en borrador puede rechazarse.")
    with governed_write():
        profile.estado = MaterialApplicationProfile.Estado.RECHAZADO
        profile.save()
        MaterialApplicationProfileDecision.objects.create(
            profile=profile,
            decision=MaterialApplicationProfileDecision.Decision.RECHAZADO,
            actor=user,
            nota=note,
        )
    return profile


@transaction.atomic
def retire_profile(profile_id, organization, user, note=""):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_APPLICATION_PROFILE_APPROVE
    )
    profile = _profile_for_update(profile_id, organization)
    if profile.estado != MaterialApplicationProfile.Estado.APROBADO:
        raise ValidationError("Sólo un perfil aprobado puede retirarse.")
    with governed_write():
        profile.estado = MaterialApplicationProfile.Estado.RETIRADO
        profile.retired_by = user
        profile.retired_at = timezone.now()
        profile.save()
        MaterialApplicationProfileDecision.objects.create(
            profile=profile,
            decision=MaterialApplicationProfileDecision.Decision.RETIRADO,
            actor=user,
            nota=note,
        )
    return profile


@transaction.atomic
def create_revision(profile_id, organization, user):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_APPLICATION_PROFILE_MANAGE
    )
    source = _profile_for_update(profile_id, organization)
    if source.estado != MaterialApplicationProfile.Estado.APROBADO:
        raise ValidationError("Sólo un perfil aprobado puede tener una nueva revisión.")
    with governed_write():
        revision = MaterialApplicationProfile(
            organizacion=organization,
            obra=source.obra,
            codigo=source.codigo,
            nombre=source.nombre,
            descripcion=source.descripcion,
            cantidad_unidad_funcional=source.cantidad_unidad_funcional,
            unidad_funcional=source.unidad_funcional,
            requisitos=source.requisitos,
            estado=MaterialApplicationProfile.Estado.BORRADOR,
            version=source.version + 1,
            reemplaza_a=source,
            created_by=user,
        )
        revision.save()
        MaterialApplicationProfileDecision.objects.create(
            profile=revision,
            decision=MaterialApplicationProfileDecision.Decision.CREADO,
            actor=user,
            contexto={"revision_de_id": source.pk},
        )
    return revision


def approved_profile_for_code(organization, codigo, obra=None):
    """The single approved profile for (organization, obra, codigo), if any."""
    return MaterialApplicationProfile.objects.filter(
        organizacion=organization,
        obra=obra,
        codigo=codigo,
        estado=MaterialApplicationProfile.Estado.APROBADO,
    ).first()
