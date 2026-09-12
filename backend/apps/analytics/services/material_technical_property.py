"""Lifecycle for MaterialTechnicalPropertyAssertion (MI-01B).

Only an approved assertion may back automatic suitability evaluation
(MI-01C). Creating/approving never infers a value from the material's name
or category: every assertion must state its provenance. Approving a new
assertion for a (material, property_key) that already has a current
approved one supersedes it explicitly (REEMPLAZADO), never silently.
"""

from contextlib import contextmanager
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models.material_technical_property import (
    MaterialTechnicalPropertyAssertion,
    MaterialTechnicalPropertyAssertionDecision,
    property_assertion_write,
)
from ..permissions import Permission, require_tenant_permission
from .unit_conversion import UnitConversionError, convert_value

Estado = MaterialTechnicalPropertyAssertion.Estado
Tipo = MaterialTechnicalPropertyAssertion.TipoPropiedad


@contextmanager
def governed_write():
    token = property_assertion_write.set(True)
    try:
        yield
    finally:
        property_assertion_write.reset(token)


def _assertion_for_update(assertion_id, organization):
    return MaterialTechnicalPropertyAssertion.objects.select_for_update().get(
        pk=assertion_id, organizacion=organization
    )


def _current_approved(organization, material, property_key, *, for_update=False):
    qs = MaterialTechnicalPropertyAssertion.objects.filter(
        organizacion=organization, material=material, property_key=property_key,
        estado=Estado.APROBADO,
    )
    if for_update:
        qs = qs.select_for_update()
    return qs.first()


def _check_unit_compatible_with_current(organization, material, property_key, unit):
    if not unit:
        return
    current = _current_approved(organization, material, property_key)
    if not current or not current.unit or current.unit == unit:
        return
    try:
        convert_value(Decimal("1"), current.unit, unit)
    except UnitConversionError as exc:
        raise ValidationError(
            f"Unidad incompatible con la aserción vigente para '{property_key}': {exc}"
        )


@transaction.atomic
def create_assertion(
    organization,
    user,
    material,
    property_key,
    property_type,
    provenance_type,
    effective_date,
    value_numeric=None,
    value_text="",
    value_boolean=None,
    unit="",
    evidencia=None,
    version_evidencia=None,
    fuente=None,
    rationale="",
):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_PROPERTY_ASSERTION_MANAGE
    )
    if material.organizacion_id != organization.id:
        raise ValidationError({"material": "El material debe pertenecer a la misma organizacion."})
    if property_type == Tipo.NUMERIC:
        _check_unit_compatible_with_current(organization, material, property_key, unit)
    with governed_write():
        assertion = MaterialTechnicalPropertyAssertion(
            organizacion=organization,
            material=material,
            property_key=property_key,
            property_type=property_type,
            value_numeric=value_numeric,
            value_text=value_text,
            value_boolean=value_boolean,
            unit=unit,
            provenance_type=provenance_type,
            evidencia=evidencia,
            version_evidencia=version_evidencia,
            fuente=fuente,
            rationale=rationale,
            effective_date=effective_date,
            estado=Estado.BORRADOR,
            asserted_by=user,
        )
        assertion.save()
        MaterialTechnicalPropertyAssertionDecision.objects.create(
            assertion=assertion,
            decision=MaterialTechnicalPropertyAssertionDecision.Decision.CREADO,
            actor=user,
        )
    return assertion


@transaction.atomic
def approve_assertion(assertion_id, organization, user, note=""):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_PROPERTY_ASSERTION_APPROVE
    )
    assertion = _assertion_for_update(assertion_id, organization)
    if assertion.estado != Estado.BORRADOR:
        raise ValidationError("Sólo una aserción en borrador puede aprobarse.")
    predecessor = _current_approved(
        organization, assertion.material, assertion.property_key, for_update=True
    )
    try:
        with governed_write():
            if predecessor is not None and predecessor.pk != assertion.pk:
                predecessor.estado = Estado.REEMPLAZADO
                predecessor.save()
                MaterialTechnicalPropertyAssertionDecision.objects.create(
                    assertion=predecessor,
                    decision=MaterialTechnicalPropertyAssertionDecision.Decision.REEMPLAZADO,
                    actor=user,
                    nota=note,
                    contexto={"reemplazado_por_id": assertion.pk},
                )
            assertion.estado = Estado.APROBADO
            assertion.reviewed_by = user
            assertion.reviewed_at = timezone.now()
            assertion.save()
            MaterialTechnicalPropertyAssertionDecision.objects.create(
                assertion=assertion,
                decision=MaterialTechnicalPropertyAssertionDecision.Decision.APROBADO,
                actor=user,
                nota=note,
            )
    except IntegrityError as exc:
        raise ValidationError(
            "Ya existe otra aserción aprobada y vigente para esta propiedad."
        ) from exc
    return assertion


@transaction.atomic
def reject_assertion(assertion_id, organization, user, note=""):
    require_tenant_permission(
        user, organization, Permission.MATERIAL_PROPERTY_ASSERTION_APPROVE
    )
    assertion = _assertion_for_update(assertion_id, organization)
    if assertion.estado != Estado.BORRADOR:
        raise ValidationError("Sólo una aserción en borrador puede rechazarse.")
    with governed_write():
        assertion.estado = Estado.RECHAZADO
        assertion.save()
        MaterialTechnicalPropertyAssertionDecision.objects.create(
            assertion=assertion,
            decision=MaterialTechnicalPropertyAssertionDecision.Decision.RECHAZADO,
            actor=user,
            nota=note,
        )
    return assertion


def approved_property(organization, material, property_key):
    """The single current approved assertion for a property, or None (unknown)."""
    return _current_approved(organization, material, property_key)
