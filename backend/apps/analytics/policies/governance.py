from django.core.exceptions import ValidationError

from ..models import FormulaAmbiental, RevisionProfesionalAmbiental, VersionMetodologia
from ..services.eligibility_v2 import active_factor_version

TRANSITIONS = {
    VersionMetodologia.Estado.BORRADOR: {VersionMetodologia.Estado.PRUEBAS},
    VersionMetodologia.Estado.PRUEBAS: {
        VersionMetodologia.Estado.BORRADOR,
        VersionMetodologia.Estado.VALIDADA,
    },
    VersionMetodologia.Estado.VALIDADA: {VersionMetodologia.Estado.ACTIVA},
    VersionMetodologia.Estado.ACTIVA: {VersionMetodologia.Estado.OBSOLETA},
    VersionMetodologia.Estado.OBSOLETA: set(),
}
RESULT_TYPES = {
    "emision",
    "reduccion",
    "emision_evitada",
    "remocion",
    "compensacion",
    "otro",
}


def validate_applicability(value):
    if not isinstance(value, dict):
        raise ValidationError("La aplicabilidad debe ser un objeto JSON.")
    allowed = {
        "tipos_actividad",
        "flujos",
        "tipos_recurso",
        "regiones",
        "atributos",
        "unidad_operacional_ids",
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValidationError(
            f"Claves de aplicabilidad no soportadas: {', '.join(sorted(unknown))}."
        )
    for key in {
        "tipos_actividad",
        "flujos",
        "tipos_recurso",
        "regiones",
        "unidad_operacional_ids",
    } & set(value):
        if not isinstance(value[key], list):
            raise ValidationError(f"{key} debe ser una lista.")
    if "atributos" in value and not isinstance(value["atributos"], dict):
        raise ValidationError("atributos debe ser un objeto.")
    allowed_attributes = {
        "estado",
        "tipo",
        "proceso_operacional_id",
        "unidad_operacional_id",
    }
    if (
        isinstance(value.get("atributos"), dict)
        and set(value["atributos"]) - allowed_attributes
    ):
        raise ValidationError(
            "La aplicabilidad contiene atributos de actividad no soportados."
        )
    return value


def structural_errors(version):
    errors = []
    try:
        formula = version.formula
    except Exception:
        return ["La versiÃ³n no tiene fÃ³rmula."]
    variables = list(formula.variables.all())
    if formula.tipo not in {choice for choice, _ in formula.Tipo.choices}:
        errors.append("La fÃ³rmula no tiene una estrategia registrada y segura.")
    if not variables:
        errors.append("La fÃ³rmula no tiene variables declaradas.")
    for variable in variables:
        if not variable.concepto_observacion or not variable.unidad_esperada:
            errors.append(
                f"La variable {variable.clave} no declara concepto y unidad esperada."
            )
    if not version.fuente_referencia.strip():
        errors.append("La versiÃ³n no declara fuente o referencia tÃ©cnica.")
    if version.tipo_resultado not in RESULT_TYPES:
        errors.append("El tipo de resultado no estÃ¡ soportado.")
    if (
        version.vigencia_desde
        and version.vigencia_hasta
        and version.vigencia_desde > version.vigencia_hasta
    ):
        errors.append("La vigencia de la metodologÃ­a es invÃ¡lida.")
    dynamic_fuel_formula = (
        formula.tipo == FormulaAmbiental.Tipo.COMBUSTIBLE_CONSUMIDO
        or (
            formula.tipo == FormulaAmbiental.Tipo.TRANSPORTE_COMBUSTIBLE
            and formula.factor_ambiental_id is None
        )
    )
    if dynamic_fuel_formula and formula.factor_ambiental_id is not None:
        errors.append(
            "La formula de combustible consumido debe seleccionar el factor dinamicamente."
        )
    if not dynamic_fuel_formula and not active_factor_version(
        formula, version.metodologia.organizacion
    ):
        errors.append("No existe un factor activo, vigente y aplicable.")
    validate_applicability(version.aplicabilidad)
    return errors


def validate_transition(version, target, professional_review=None):
    if target not in TRANSITIONS.get(version.estado, set()):
        raise ValidationError(
            f"TransiciÃ³n no permitida: {version.estado} -> {target}."
        )
    if target in {VersionMetodologia.Estado.VALIDADA, VersionMetodologia.Estado.ACTIVA}:
        errors = structural_errors(version)
        if errors:
            raise ValidationError(errors)
    if (
        target == VersionMetodologia.Estado.VALIDADA
        and version.requiere_revision_profesional
    ):
        valid_states = {
            RevisionProfesionalAmbiental.Estado.VALIDADA,
            RevisionProfesionalAmbiental.Estado.VALIDADA_OBSERVACIONES,
        }
        valid = (
            isinstance(professional_review, RevisionProfesionalAmbiental)
            and professional_review.tipo
            == RevisionProfesionalAmbiental.Tipo.METODOLOGIA
            and professional_review.version_metodologia_id == version.id
            and (
                version.metodologia.organizacion_id is None
                or professional_review.organizacion_id
                == version.metodologia.organizacion_id
            )
            and professional_review.estado in valid_states
            and professional_review.profesional_id is not None
            and professional_review.fecha is not None
        )
        if not valid:
            raise ValidationError(
                "Esta metodologÃ­a requiere una revisiÃ³n profesional vÃ¡lida y trazable."
            )
