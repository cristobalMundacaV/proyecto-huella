"""Authority for material_cantidad factor selection (01D).

The only source of truth is an explicit, approved MaterialFactorMapping
applicable at the reception's effective date. No fuzzy matching, no
metadata/name/category/supplier inference: absence of a governed mapping is
``no_calculable``, never a guess.
"""

from django.db.models import Q

from ..models import VersionFactorAmbiental
from .material_factor_mapping import approved_mapping_for_date
from .unit_conversion import UnitConversionError, convert_value


def _result(*, factor_version, specificity, reason, mapping, decision, status):
    return {
        "factor_version": factor_version,
        "especificidad": specificity,
        "razon": reason,
        "mapping": mapping,
        "mapping_decision": decision,
        "estado": status,
        "status": status,
        "reason": reason,
        "specificity": specificity,
    }


def select_material_factor(organization, material, source_unit, effective_date):
    mappings = list(
        approved_mapping_for_date(organization, material, effective_date)[:2]
    )
    if not mappings:
        return _result(
            factor_version=None,
            specificity=None,
            reason=(
                f"No existe un mapeo material-factor aprobado y vigente para "
                f"{material.nombre}."
            ),
            mapping=None,
            decision=None,
            status="no_calculable",
        )
    if len(mappings) > 1:
        return _result(
            factor_version=None,
            specificity=None,
            reason=(
                "Existen múltiples mapeos aprobados y vigentes para el mismo "
                "material; requiere revisión."
            ),
            mapping=None,
            decision=None,
            status="requiere_revision",
        )
    mapping = mappings[0]
    factor = mapping.factor
    decision = mapping.decisiones.filter(decision="aprobado").order_by("-pk").first()
    active_version = (
        VersionFactorAmbiental.objects.filter(
            factor=factor, estado=VersionFactorAmbiental.Estado.ACTIVO,
        )
        .filter(Q(vigencia_desde__isnull=True) | Q(vigencia_desde__lte=effective_date))
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=effective_date))
        .order_by("-version")
        .first()
    )
    if not active_version:
        return _result(
            factor_version=None,
            specificity="explicit_mapping",
            reason=(
                "El mapeo está aprobado, pero no existe VersionFactorAmbiental "
                "ACTIVA y vigente para el factor referenciado."
            ),
            mapping=mapping,
            decision=decision,
            status="no_calculable",
        )
    # EC3's authoritative data remains subject to local, current scientific governance.
    if (factor.contexto or {}).get("provider") == "EC3" or hasattr(active_version, "ec3_candidate"):
        from apps.ec3.services import factor_block_reason

        block_reason = factor_block_reason(active_version, mapping)
        if block_reason:
            return _result(
                factor_version=None, specificity="explicit_mapping", reason=block_reason,
                mapping=mapping, decision=decision, status="requiere_revision",
            )
    try:
        convert_value(1, source_unit, active_version.factor.unidad_entrada)
    except UnitConversionError as error:
        return _result(
            factor_version=None,
            specificity="explicit_mapping",
            reason=str(error),
            mapping=mapping,
            decision=decision,
            status="no_calculable",
        )
    return _result(
        factor_version=active_version,
        specificity="explicit_mapping",
        reason="Factor seleccionado por mapeo material-factor explícito y gobernado.",
        mapping=mapping,
        decision=decision,
        status="calculable",
    )
