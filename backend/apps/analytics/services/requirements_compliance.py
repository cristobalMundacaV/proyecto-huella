from ..policies.requirements_compliance import (
    RequirementClass,
    RequirementContract,
    evaluate_requirement,
)


def normative_limit_contract(limit):
    return RequirementContract(
        requirement_class=RequirementClass.NORMATIVE_LIMIT,
        requirement_id=f"normative-limit:{limit.pk}",
        scope={
            "organization_id": str(limit.organizacion_id),
            "industry": limit.industria,
            "region": limit.region,
            "installation_type": limit.tipo_instalacion,
        },
        variable=limit.variable_id,
        comparator=limit.comparador,
        threshold=limit.limite,
        unit=limit.unidad,
        valid_from=limit.vigencia_desde,
        valid_until=limit.vigencia_hasta,
        authority=limit.fuente_normativa or limit.normativa,
        evaluation_method="deterministic_threshold_comparison",
        metadata={"validated": limit.validado, "active": limit.activo},
    )


def operational_restriction_contract(restriction):
    content = restriction.contenido or {}
    return RequirementContract(
        requirement_class=RequirementClass.OPERATIONAL_RESTRICTION,
        requirement_id=f"operational-restriction:{restriction.pk}",
        scope={
            "organization_id": str(restriction.organizacion_id),
            "problem_id": restriction.problematica_id,
        },
        variable=str(content.get("variable") or ""),
        comparator=str(content.get("comparator") or content.get("comparador") or ""),
        threshold=content.get("threshold", content.get("umbral")),
        unit=str(content.get("unit") or content.get("unidad") or ""),
        valid_from=restriction.vigente_desde.date(),
        valid_until=(
            restriction.vigente_hasta.date() if restriction.vigente_hasta else None
        ),
        authority=str(content.get("authority") or content.get("fuente") or "Operación"),
        evaluation_method=str(
            content.get("evaluation_method") or "deterministic_threshold_comparison"
        ),
        metadata={"description": restriction.descripcion},
    )


def internal_target_contract(
    *,
    target_id,
    organization_id,
    variable,
    comparator,
    threshold,
    unit,
    valid_from=None,
    valid_until=None,
    authority="Organización",
    scope=None,
):
    """Adapt an explicitly governed target without making Improvement its authority."""
    return RequirementContract(
        requirement_class=RequirementClass.INTERNAL_TARGET,
        requirement_id=f"internal-target:{target_id}",
        scope={"organization_id": str(organization_id), **(scope or {})},
        variable=variable,
        comparator=comparator,
        threshold=threshold,
        unit=unit,
        valid_from=valid_from,
        valid_until=valid_until,
        authority=authority,
        evaluation_method="deterministic_threshold_comparison",
    )


def explain_requirement_result(
    requirement,
    *,
    observed_value,
    observed_unit="",
    evaluated_on=None,
    evidence_refs=(),
    result_refs=(),
):
    return evaluate_requirement(
        requirement,
        observed_value=observed_value,
        observed_unit=observed_unit,
        evaluated_on=evaluated_on,
        evidence_refs=evidence_refs,
        result_refs=result_refs,
    )
