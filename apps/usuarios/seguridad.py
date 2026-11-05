"""Utilidades de seguridad sin dependencias de Django."""
import secrets

_MAYUS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
_MINUS = 'abcdefghijkmnpqrstuvwxyz'
_DIGITOS = '23456789'
_SIMBOLOS = '!@#$%&*'


def generar_clave_temporal(largo: int = 12) -> str:
    """Clave temporal aleatoria (módulo secrets) que cumple todas las reglas de complejidad."""
    largo = max(largo, 8)
    caracteres = [
        secrets.choice(_MAYUS), secrets.choice(_MINUS),
        secrets.choice(_DIGITOS), secrets.choice(_SIMBOLOS),
    ]
    todos = _MAYUS + _MINUS + _DIGITOS + _SIMBOLOS
    caracteres += [secrets.choice(todos) for _ in range(largo - 4)]
    secrets.SystemRandom().shuffle(caracteres)
    return ''.join(caracteres)
