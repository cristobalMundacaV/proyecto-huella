from django.core.exceptions import ValidationError


def validate_knowledge_result(result, organization, result_map):
    if result.problematica.organizacion_id != organization.id:
        raise ValidationError("La intervencion pertenece a otra organizacion.")
    if result.estado not in result_map:
        raise ValidationError("El resultado de intervencion no es clasificable.")
