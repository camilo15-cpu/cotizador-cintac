"""
Reglas de complejidad de contraseña (Caso de Prueba CP01).

Módulo de Python puro (sin Django) para poder probarlo de forma aislada.
Cada regla es una expresión regular con su mensaje de error.
"""
import re

SIMBOLOS_PERMITIDOS = '!@#$%^&*'

REGLAS = (
    ('longitud', 'Debe tener al menos 8 caracteres.', re.compile(r'.{8,}', re.DOTALL)),
    ('mayuscula', 'Debe incluir al menos una letra mayúscula (A-Z).', re.compile(r'[A-Z]')),
    ('minuscula', 'Debe incluir al menos una letra minúscula (a-z).', re.compile(r'[a-z]')),
    ('numero', 'Debe incluir al menos un número (0-9).', re.compile(r'[0-9]')),
    ('especial', f'Debe incluir al menos un carácter especial ({SIMBOLOS_PERMITIDOS}).', re.compile(r'[!@#$%^&*]')),
)

# La misma política en una sola expresión regular (lookaheads), útil para documentarla y compararla
PATRON_COMPLETO = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{8,}$', re.DOTALL)


def mensajes_incumplidos(clave: str) -> list:
    """Devuelve los mensajes de las reglas que la clave NO cumple (lista vacía = clave válida)."""
    return [mensaje for _id, mensaje, patron in REGLAS if not patron.search(clave)]


def es_valida(clave: str) -> bool:
    return PATRON_COMPLETO.match(clave) is not None
