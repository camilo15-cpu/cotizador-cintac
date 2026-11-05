"""Control de acceso por rol para las vistas basadas en clases."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from apps.auditoria.models import AuditLog
from apps.auditoria.services import registrar

from .models import Usuario


class RolRequeridoMixin(LoginRequiredMixin):
    """Exige sesión iniciada y que el rol del usuario esté en `roles_permitidos`.

    Un acceso no permitido responde 403 y queda registrado en la auditoría.
    """
    roles_permitidos = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.rol not in self.roles_permitidos:
            registrar(AuditLog.Accion.ACCESO_DENEGADO, request=request, detalle={'ruta': request.path})
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class SoloAdminMixin(RolRequeridoMixin):
    roles_permitidos = (Usuario.Rol.ADMINISTRADOR,)


class AdminOAnalistaMixin(RolRequeridoMixin):
    roles_permitidos = (Usuario.Rol.ADMINISTRADOR, Usuario.Rol.ANALISTA)
