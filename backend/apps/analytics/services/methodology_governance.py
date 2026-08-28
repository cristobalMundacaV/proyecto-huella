from django.db import transaction
from django.utils import timezone

from ..models import FormulaAmbiental, VariableFormula, VersionMetodologia
from ..policies.governance import (
    structural_errors,
    validate_applicability,
    validate_transition,
)

__all__ = ["structural_errors", "transition_version", "validate_applicability"]


@transaction.atomic
def transition_version(version, target, user=None, professional_review=None):
    validate_transition(version, target, professional_review)
    if target == VersionMetodologia.Estado.VALIDADA:
        version.validado_por = user
        version.fecha_validacion = timezone.now()
    if target == VersionMetodologia.Estado.ACTIVA:
        VersionMetodologia.objects.filter(
            metodologia=version.metodologia, estado=VersionMetodologia.Estado.ACTIVA
        ).exclude(pk=version.pk).update(estado=VersionMetodologia.Estado.OBSOLETA)
    VersionMetodologia.objects.filter(pk=version.pk).update(
        estado=target,
        validado_por=version.validado_por,
        fecha_validacion=version.fecha_validacion,
    )
    version.refresh_from_db()
    return version


@transaction.atomic
def create_methodology_version(methodology, payload, formula_data, factor, variables):
    version = VersionMetodologia.objects.create(
        metodologia=methodology,
        version=(
            methodology.versiones.order_by("-version")
            .values_list("version", flat=True)
            .first()
            or 0
        )
        + 1,
        descripcion_tecnica=payload.get("descripcion_tecnica", ""),
        fuente_referencia=payload.get("fuente_referencia", ""),
        vigencia_desde=payload.get("vigencia_desde") or None,
        vigencia_hasta=payload.get("vigencia_hasta") or None,
        aplicabilidad=payload.get("aplicabilidad", {}),
        prioridad=payload.get("prioridad", 100),
        requiere_revision_profesional=payload.get(
            "requiere_revision_profesional", False
        ),
        tipo_resultado=payload.get("tipo_resultado", "emision"),
    )
    formula = FormulaAmbiental.objects.create(
        version_metodologia=version,
        factor_ambiental=factor,
        codigo=formula_data.get(
            "codigo", f"formula-{methodology.codigo}-v{version.version}"
        ),
        tipo=formula_data.get("tipo"),
        expresion_legible=formula_data.get("expresion_legible", ""),
        version=formula_data.get("version", 1),
    )
    for data in variables:
        create_formula_variable(formula, data)
    return version


def create_formula_variable(formula, data):
    variable = VariableFormula(formula=formula, **data)
    variable.full_clean()
    variable.save()
    return variable


def update_formula_variable(variable, data):
    for field, value in data.items():
        setattr(variable, field, value)
    variable.full_clean()
    variable.save()
    return variable


def delete_formula_variable(variable):
    variable.delete()
