"""Validador de contraseñas conectado a AUTH_PASSWORD_VALIDATORS."""
from django.core.exceptions import ValidationError

from .reglas_clave import SIMBOLOS_PERMITIDOS, mensajes_incumplidos


class ComplejidadClaveValidator:
    """Exige 8+ caracteres, mayúscula, minúscula, número y un símbolo (!@#$%^&*)."""

    def validate(self, password, user=None):
        errores = mensajes_incumplidos(password)
        if errores:
            raise ValidationError(errores, code='clave_poco_compleja')

    def get_help_text(self):
        return (f'Mínimo 8 caracteres, con mayúscula, minúscula, número y un carácter especial '
                f'({SIMBOLOS_PERMITIDOS}).')
