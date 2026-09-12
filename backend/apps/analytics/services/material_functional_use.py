"""Lifecycle for MaterialFunctionalUse (MI-01C): the governed quantity of a
material that fulfills one functional unit of an approved application
profile. Never inferred from density/name — always an explicit, evidenced,
human-approved value."""

from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models.material_application_profile import MaterialApplicationProfile
from ..models.material_functional_use import (
    MaterialFunctionalUse,
    MaterialFunctionalUseDecision,
    functional_use_write,
)
from ..permissions import Permission, require_tenant_permission

Estado = MaterialFunctionalUse.Estado


@contextmanager
def governed_write():
    token = functional_use_write.set(True)
    try:
        yield
    finally:
        functional_use_write.reset(token)


def _for_update(functional_use_id, organization):
    return MaterialFunctionalUse.objects.select_for_update().get(
        pk=functional_use_id, organizacion=organization
    )


def _current_approved(organization, material, profile, *, for_update=False):
    qs = MaterialFunctionalUse.objects.filter(
        organizacion=organization, material=material, profile=profile, estado=Estado.APROBADO,
    )
    if for_update:
        qs = qs.select_for_update()
    return qs.first()


@transaction.atomic
def create_functional_use(
    organization, user, material, profile, cantidad_por_unidad_funcional, unidad,
    rationale, evidencia=None,
):
    require_tenant_permission(user, organization, Permission.MATERIAL_APPLICATION_PROFILE_MANAGE)
    if material.organizacion_id != organization.id:
        raise ValidationError({"material": "El material debe pertenecer a la misma organizacion."})
    if profile.organizacion_id != organization.id:
        raise ValidationError({"profile": "El perfil debe pertenecer a la misma organizacion."})
    if profile.estado != MaterialApplicationProfile.Estado.APROBADO:
        raise ValidationError({"profile": "El perfil debe estar aprobado."})
    with governed_write():
        functional_use = MaterialFunctionalUse(
            organizacion=organization,
            material=material,
            profile=profile,
            cantidad_por_unidad_funcional=cantidad_por_unidad_funcional,
            unidad=unidad,
            rationale=rationale,
            evidencia=evidencia,
            estado=Estado.BORRADOR,
            created_by=user,
        )
        functional_use.save()
        MaterialFunctionalUseDecision.objects.create(
            functional_use=functional_use,
            decision=MaterialFunctionalUseDecision.Decision.CREADO,
            actor=user,
        )
    return functional_use


@transaction.atomic
def approve_functional_use(functional_use_id, organization, user, note=""):
    require_tenant_permission(user, organization, Permission.MATERIAL_APPLICATION_PROFILE_APPROVE)
    functional_use = _for_update(functional_use_id, organization)
    if functional_use.estado != Estado.BORRADOR:
        raise ValidationError("Sólo un uso funcional en borrador puede aprobarse.")
    predecessor = _current_approved(
        organization, functional_use.material, functional_use.profile, for_update=True
    )
    try:
        with governed_write():
            if predecessor is not None and predecessor.pk != functional_use.pk:
                predecessor.estado = Estado.REEMPLAZADO
                predecessor.save()
                MaterialFunctionalUseDecision.objects.create(
                    functional_use=predecessor,
                    decision=MaterialFunctionalUseDecision.Decision.REEMPLAZADO,
                    actor=user,
                    nota=note,
                    contexto={"reemplazado_por_id": functional_use.pk},
                )
            functional_use.estado = Estado.APROBADO
            functional_use.reviewed_by = user
            functional_use.reviewed_at = timezone.now()
            functional_use.save()
            MaterialFunctionalUseDecision.objects.create(
                functional_use=functional_use,
                decision=MaterialFunctionalUseDecision.Decision.APROBADO,
                actor=user,
                nota=note,
            )
    except IntegrityError as exc:
        raise ValidationError(
            "Ya existe otro uso funcional aprobado y vigente para este material y perfil."
        ) from exc
    return functional_use


@transaction.atomic
def reject_functional_use(functional_use_id, organization, user, note=""):
    require_tenant_permission(user, organization, Permission.MATERIAL_APPLICATION_PROFILE_APPROVE)
    functional_use = _for_update(functional_use_id, organization)
    if functional_use.estado != Estado.BORRADOR:
        raise ValidationError("Sólo un uso funcional en borrador puede rechazarse.")
    with governed_write():
        functional_use.estado = Estado.RECHAZADO
        functional_use.save()
        MaterialFunctionalUseDecision.objects.create(
            functional_use=functional_use,
            decision=MaterialFunctionalUseDecision.Decision.RECHAZADO,
            actor=user,
            nota=note,
        )
    return functional_use


def approved_functional_use(organization, material, profile):
    return _current_approved(organization, material, profile)
