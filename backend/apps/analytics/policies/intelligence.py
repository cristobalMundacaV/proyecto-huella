from django.core.exceptions import ValidationError


def require_human_confirmation(value):
    if value is not True:
        raise ValidationError(
            {"confirmado": "Se requiere confirmacion humana explicita."}
        )


def validate_command_transition(command):
    if command.estado != command.Estado.PREPARADO:
        raise ValidationError("El comando ya fue procesado.")
