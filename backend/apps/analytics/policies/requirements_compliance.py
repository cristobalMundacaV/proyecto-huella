from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping


class RequirementClass(str, Enum):
    NORMATIVE_LIMIT = "normative_limit"
    OPERATIONAL_RESTRICTION = "operational_restriction"
    INTERNAL_TARGET = "internal_target"


class EvaluationState(str, Enum):
    COMPLIES = "cumple"
    DOES_NOT_COMPLY = "incumple"
    NO_DATA = "sin_dato"
    NOT_APPLICABLE = "no_aplica"
    REQUIRES_REVIEW = "requiere_revision"


@dataclass(frozen=True)
class RequirementContract:
    requirement_class: RequirementClass
    requirement_id: str
    scope: Mapping[str, Any]
    variable: str
    comparator: str
    threshold: Any
    unit: str
    valid_from: date | None
    valid_until: date | None
    authority: str
    evaluation_method: str
    evidence_refs: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ComplianceResult:
    requirement_id: str
    requirement_class: RequirementClass
    state: EvaluationState
    explanation: str
    observed_value: Decimal | None
    observed_unit: str
    evidence_refs: tuple[str, ...]
    result_refs: tuple[str, ...]


def _decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _result(requirement, state, explanation, value, unit, evidence_refs, result_refs):
    return ComplianceResult(
        requirement_id=requirement.requirement_id,
        requirement_class=requirement.requirement_class,
        state=state,
        explanation=explanation,
        observed_value=value,
        observed_unit=unit,
        evidence_refs=tuple(evidence_refs),
        result_refs=tuple(result_refs),
    )


def evaluate_requirement(
    requirement,
    *,
    observed_value,
    observed_unit="",
    evaluated_on=None,
    evidence_refs=(),
    result_refs=(),
):
    """Compare an existing result with a requirement without deriving measurements."""
    evaluated_on = evaluated_on or date.today()
    if requirement.valid_from and evaluated_on < requirement.valid_from:
        return _result(
            requirement,
            EvaluationState.NOT_APPLICABLE,
            "El requerimiento todavía no se encuentra vigente.",
            _decimal(observed_value),
            observed_unit,
            evidence_refs,
            result_refs,
        )
    if requirement.valid_until and evaluated_on > requirement.valid_until:
        return _result(
            requirement,
            EvaluationState.NOT_APPLICABLE,
            "El requerimiento ya no se encuentra vigente.",
            _decimal(observed_value),
            observed_unit,
            evidence_refs,
            result_refs,
        )
    if observed_value is None:
        return _result(
            requirement,
            EvaluationState.NO_DATA,
            "No existe un resultado verificable para evaluar este requerimiento.",
            None,
            observed_unit,
            evidence_refs,
            result_refs,
        )
    value = _decimal(observed_value)
    if value is None:
        return _result(
            requirement,
            EvaluationState.REQUIRES_REVIEW,
            "El resultado disponible no es numérico y requiere revisión.",
            None,
            observed_unit,
            evidence_refs,
            result_refs,
        )
    observed_unit = str(observed_unit or "")
    if requirement.unit and observed_unit.casefold() != requirement.unit.casefold():
        return _result(
            requirement,
            EvaluationState.REQUIRES_REVIEW,
            "La unidad del resultado no coincide con la unidad del requerimiento.",
            value,
            observed_unit,
            evidence_refs,
            result_refs,
        )

    comparator = requirement.comparator
    if comparator == "rango":
        try:
            lower, upper = (_decimal(item) for item in requirement.threshold)
        except (TypeError, ValueError):
            lower = upper = None
        complies = lower is not None and upper is not None and lower <= value <= upper
    else:
        threshold = _decimal(requirement.threshold)
        operations = {
            "<=": lambda: value <= threshold,
            ">=": lambda: value >= threshold,
            "<": lambda: value < threshold,
            ">": lambda: value > threshold,
            "=": lambda: value == threshold,
            "==": lambda: value == threshold,
        }
        if threshold is None or comparator not in operations:
            return _result(
                requirement,
                EvaluationState.REQUIRES_REVIEW,
                "La condición no permite una evaluación automática determinística.",
                value,
                observed_unit,
                evidence_refs,
                result_refs,
            )
        complies = operations[comparator]()

    state = EvaluationState.COMPLIES if complies else EvaluationState.DOES_NOT_COMPLY
    explanation = (
        "El resultado satisface la condición definida por el requerimiento."
        if complies
        else "El resultado no satisface la condición definida por el requerimiento."
    )
    return _result(
        requirement,
        state,
        explanation,
        value,
        observed_unit,
        evidence_refs,
        result_refs,
    )
