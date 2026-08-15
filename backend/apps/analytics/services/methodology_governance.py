from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import VersionFactorAmbiental, VersionMetodologia
from .eligibility_v2 import active_factor_version


TRANSITIONS = {
    VersionMetodologia.Estado.BORRADOR: {VersionMetodologia.Estado.PRUEBAS},
    VersionMetodologia.Estado.PRUEBAS: {VersionMetodologia.Estado.BORRADOR, VersionMetodologia.Estado.VALIDADA},
    VersionMetodologia.Estado.VALIDADA: {VersionMetodologia.Estado.ACTIVA},
    VersionMetodologia.Estado.ACTIVA: {VersionMetodologia.Estado.OBSOLETA},
    VersionMetodologia.Estado.OBSOLETA: set(),
}

RESULT_TYPES = {"emision", "reduccion", "emision_evitada", "remocion", "compensacion", "otro"}


def validate_applicability(value):
    if not isinstance(value, dict):
        raise ValidationError("La aplicabilidad debe ser un objeto JSON.")
    allowed = {"tipos_actividad", "flujos", "regiones", "atributos", "unidad_operacional_ids"}
    unknown = set(value) - allowed
    if unknown:
        raise ValidationError(f"Claves de aplicabilidad no soportadas: {', '.join(sorted(unknown))}.")
    for key in {"tipos_actividad", "flujos", "regiones", "unidad_operacional_ids"} & set(value):
        if not isinstance(value[key], list):
            raise ValidationError(f"{key} debe ser una lista.")
    if "atributos" in value and not isinstance(value["atributos"], dict):
        raise ValidationError("atributos debe ser un objeto.")
    allowed_attributes = {"estado", "tipo", "proceso_operacional_id", "unidad_operacional_id"}
    if isinstance(value.get("atributos"), dict) and set(value["atributos"]) - allowed_attributes:
        raise ValidationError("La aplicabilidad contiene atributos de actividad no soportados.")
    return value


def structural_errors(version):
    errors = []
    try:
        formula = version.formula
    except Exception:
        return ["La versión no tiene fórmula."]
    variables = list(formula.variables.all())
    if formula.tipo not in {choice for choice, _ in formula.Tipo.choices}:
        errors.append("La fórmula no tiene una estrategia registrada y segura.")
    if not variables:
        errors.append("La fórmula no tiene variables declaradas.")
    for variable in variables:
        if not variable.concepto_observacion or not variable.unidad_esperada:
            errors.append(f"La variable {variable.clave} no declara concepto y unidad esperada.")
    if not version.fuente_referencia.strip():
        errors.append("La versión no declara fuente o referencia técnica.")
    if version.tipo_resultado not in RESULT_TYPES:
        errors.append("El tipo de resultado no está soportado.")
    if version.vigencia_desde and version.vigencia_hasta and version.vigencia_desde > version.vigencia_hasta:
        errors.append("La vigencia de la metodología es inválida.")
    if not active_factor_version(formula, version.metodologia.organizacion):
        errors.append("No existe un factor activo, vigente y aplicable.")
    validate_applicability(version.aplicabilidad)
    return errors


@transaction.atomic
def transition_version(version, target, user=None):
    if target not in TRANSITIONS.get(version.estado, set()):
        raise ValidationError(f"Transición no permitida: {version.estado} -> {target}.")
    if target in {VersionMetodologia.Estado.VALIDADA, VersionMetodologia.Estado.ACTIVA}:
        errors = structural_errors(version)
        if errors:
            raise ValidationError(errors)
    if target == VersionMetodologia.Estado.VALIDADA:
        if version.requiere_revision_profesional and not (user and (user.is_staff or user.is_superuser)):
            raise ValidationError("Esta metodología requiere validación profesional.")
        version.validado_por = user
        version.fecha_validacion = timezone.now()
    if target == VersionMetodologia.Estado.ACTIVA:
        VersionMetodologia.objects.filter(
            metodologia=version.metodologia, estado=VersionMetodologia.Estado.ACTIVA,
        ).exclude(pk=version.pk).update(estado=VersionMetodologia.Estado.OBSOLETA)
    VersionMetodologia.objects.filter(pk=version.pk).update(
        estado=target, validado_por=version.validado_por, fecha_validacion=version.fecha_validacion,
    )
    version.refresh_from_db()
    return version
