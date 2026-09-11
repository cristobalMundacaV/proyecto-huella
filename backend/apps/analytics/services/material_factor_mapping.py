"""Lifecycle for the governed material -> factor mapping (01D).

An approved mapping is the only authority the modern material_cantidad
selector may consult (see material_factor_selector.py). No fuzzy or
metadata matching is performed here: propose/approve/reject/revoke are the
only state transitions, each recorded as an immutable
MaterialFactorMappingDecision.
"""

from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from ..models import FactorAmbiental, MaterialOperacional
from ..models.material_factor_mapping import (
    MaterialFactorMapping,
    MaterialFactorMappingDecision,
    mapping_write,
)
from ..permissions import Permission, require_tenant_permission

ALLOWED_CONTEXT_KEYS = {"technical_basis", "approved_use", "specification_reference", "review_note"}


@contextmanager
def governed_write():
    token = mapping_write.set(True)
    try:
        yield
    finally:
        mapping_write.reset(token)


def _validate_context(contexto):
    contexto = {} if contexto is None else contexto
    if not isinstance(contexto, dict):
        raise ValidationError("El contexto del mapeo debe ser un objeto.")
    invalid = set(contexto) - ALLOWED_CONTEXT_KEYS
    if invalid or any(not isinstance(v, str) or len(v) > 2000 for v in contexto.values()):
        raise ValidationError(
            "Contexto permitido: technical_basis, approved_use, "
            "specification_reference y review_note textuales; no equivalencia funcional."
        )
    return contexto


def _mapping_for_update(mapping_id, organization):
    mapping = (
        MaterialFactorMapping.objects.select_for_update()
        .select_related("material", "factor")
        .get(pk=mapping_id, organizacion=organization)
    )
    return mapping


@transaction.atomic
def propose_material_mapping(
    organization, material, factor, vigencia_desde, vigencia_hasta, user, contexto=None
):
    require_tenant_permission(user, organization, Permission.MATERIAL_MAPPING_PROPOSE)
    contexto = _validate_context(contexto)
    material = MaterialOperacional.objects.select_for_update().get(
        pk=material.pk, organizacion=organization
    )
    if factor.organizacion_id not in (None, organization.id):
        raise ValidationError(
            {"factor": "El factor debe ser global o pertenecer a la misma organizacion."}
        )
    factor = FactorAmbiental.objects.select_for_update().get(pk=factor.pk)
    try:
        with governed_write(), transaction.atomic():
            mapping = MaterialFactorMapping(
                organizacion=organization,
                material=material,
                factor=factor,
                estado=MaterialFactorMapping.Estado.PROPUESTO,
                vigencia_desde=vigencia_desde,
                vigencia_hasta=vigencia_hasta,
                contexto=contexto,
                propuesto_por=user,
            )
            mapping.save()
            MaterialFactorMappingDecision.objects.create(
                mapping=mapping,
                decision=MaterialFactorMappingDecision.Decision.PROPUESTO,
                actor=user,
                contexto=contexto,
            )
    except IntegrityError as exc:
        raise ValidationError(
            "Ya existe una propuesta idéntica para este material, factor y vigencia."
        ) from exc
    return mapping


@transaction.atomic
def approve_material_mapping(mapping_id, organization, user, note=""):
    require_tenant_permission(user, organization, Permission.MATERIAL_MAPPING_APPROVE)
    mapping = _mapping_for_update(mapping_id, organization)
    if mapping.estado != MaterialFactorMapping.Estado.PROPUESTO:
        raise ValidationError("Sólo un mapeo propuesto puede aprobarse.")
    try:
        with governed_write():
            mapping.estado = MaterialFactorMapping.Estado.APROBADO
            mapping.save()
            MaterialFactorMappingDecision.objects.create(
                mapping=mapping,
                decision=MaterialFactorMappingDecision.Decision.APROBADO,
                actor=user,
                nota=note,
            )
    except IntegrityError as exc:
        raise ValidationError(
            "Existe otro mapeo aprobado y vigente que se superpone para este material."
        ) from exc
    return mapping


@transaction.atomic
def reject_material_mapping(mapping_id, organization, user, note=""):
    require_tenant_permission(user, organization, Permission.MATERIAL_MAPPING_APPROVE)
    mapping = _mapping_for_update(mapping_id, organization)
    if mapping.estado != MaterialFactorMapping.Estado.PROPUESTO:
        raise ValidationError("Sólo un mapeo propuesto puede rechazarse.")
    with governed_write():
        mapping.estado = MaterialFactorMapping.Estado.RECHAZADO
        mapping.save()
        MaterialFactorMappingDecision.objects.create(
            mapping=mapping,
            decision=MaterialFactorMappingDecision.Decision.RECHAZADO,
            actor=user,
            nota=note,
        )
    return mapping


@transaction.atomic
def revoke_material_mapping(mapping_id, organization, user, note="", replacement=None):
    require_tenant_permission(user, organization, Permission.MATERIAL_MAPPING_APPROVE)
    mapping = _mapping_for_update(mapping_id, organization)
    if mapping.estado != MaterialFactorMapping.Estado.APROBADO:
        raise ValidationError("Sólo un mapeo aprobado puede revocarse.")
    target_state = (
        MaterialFactorMapping.Estado.REEMPLAZADO
        if replacement is not None
        else MaterialFactorMapping.Estado.REVOCADO
    )
    if replacement is not None and replacement.organizacion_id != organization.id:
        raise ValidationError("El mapeo de reemplazo pertenece a otra organizacion.")
    with governed_write():
        mapping.estado = target_state
        mapping.revocado_por = user
        mapping.revocado_en = timezone.now()
        if replacement is not None:
            mapping.reemplazado_por = replacement
        mapping.save()
        MaterialFactorMappingDecision.objects.create(
            mapping=mapping,
            decision=MaterialFactorMappingDecision.Decision(target_state),
            actor=user,
            nota=note,
            contexto={"reemplazado_por_id": replacement.pk} if replacement else {},
        )
    return mapping


def approved_mapping_for_date(organization, material, effective_date):
    """The single approved mapping applicable at ``effective_date``, if any."""
    return (
        MaterialFactorMapping.objects.filter(
            organizacion=organization,
            material=material,
            estado=MaterialFactorMapping.Estado.APROBADO,
            vigencia_desde__lte=effective_date,
        )
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=effective_date))
        .select_related("factor")
        .order_by("-vigencia_desde", "-id")
    )
