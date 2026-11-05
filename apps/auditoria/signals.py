"""Registro automático de inicios y cierres de sesión, y de intentos de login fallidos."""
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AuditLog
from .services import registrar


@receiver(user_logged_in)
def al_iniciar_sesion(sender, request, user, **kwargs):
    registrar(AuditLog.Accion.LOGIN, request=request, usuario=user)


@receiver(user_logged_out)
def al_cerrar_sesion(sender, request, user, **kwargs):
    if user is not None:
        registrar(AuditLog.Accion.LOGOUT, request=request, usuario=user)


@receiver(user_login_failed)
def al_fallar_login(sender, credentials, request=None, **kwargs):
    nombre = str(credentials.get('username') or '')[:150]
    usuario = get_user_model().objects.filter(username=nombre.lower()).first()
    registrar(AuditLog.Accion.LOGIN_FALLIDO, request=request, usuario=usuario, usuario_nombre=nombre,
              detalle={'usuario_existe': usuario is not None})
