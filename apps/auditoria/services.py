"""Servicio central para escribir en la auditoría."""
import ipaddress

from .models import AuditLog


def obtener_ip(request):
    """IP del cliente. Detrás del proxy de Render llega en X-Forwarded-For (primer valor)."""
    if request is None:
        return None
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    candidata = reenviada.split(',')[0].strip() if reenviada else request.META.get('REMOTE_ADDR', '')
    try:
        return str(ipaddress.ip_address(candidata))
    except ValueError:
        return None


def registrar(accion, request=None, usuario=None, usuario_nombre='', objeto=None,
              objeto_tipo='', objeto_id='', detalle=None):
    """Crea un registro de auditoría.

    - usuario: quien ejecuta la acción (por defecto, el usuario autenticado de la petición).
    - objeto: instancia afectada (se guardan su tipo e id); alternativamente objeto_tipo / objeto_id.
    - detalle: diccionario con el detalle del cambio (se guarda como JSON).
    """
    if usuario is None and request is not None:
        autor = getattr(request, 'user', None)
        if autor is not None and autor.is_authenticated:
            usuario = autor
    if usuario is not None and not usuario_nombre:
        usuario_nombre = usuario.get_username()
    if objeto is not None:
        objeto_tipo, objeto_id = objeto.__class__.__name__, str(objeto.pk)
    return AuditLog.objects.create(
        usuario=usuario, usuario_nombre=(usuario_nombre or '')[:150], accion=accion,
        objeto_tipo=objeto_tipo, objeto_id=objeto_id, detalle=detalle or {}, ip=obtener_ip(request))
