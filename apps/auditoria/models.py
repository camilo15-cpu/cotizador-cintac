import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLog(models.Model):
    """Registro inmutable de las acciones realizadas en el sistema (trazabilidad para el Administrador)."""

    class Accion(models.TextChoices):
        LOGIN = 'LOGIN', 'Inicio de sesión'
        LOGOUT = 'LOGOUT', 'Cierre de sesión'
        LOGIN_FALLIDO = 'LOGIN_FALLIDO', 'Intento de login fallido'
        LOGIN_RECHAZADO = 'LOGIN_RECHAZADO', 'Login rechazado (cuenta bloqueada/inactiva)'
        CAMBIAR_CLAVE = 'CAMBIAR_CLAVE', 'Cambio de contraseña'
        BLOQUEAR_USUARIO = 'BLOQUEAR_USUARIO', 'Bloqueo de usuario'
        DESBLOQUEAR_USUARIO = 'DESBLOQUEAR_USUARIO', 'Desbloqueo de usuario'
        CREAR_USUARIO = 'CREAR_USUARIO', 'Creación de usuario'
        ELIMINAR_USUARIO = 'ELIMINAR_USUARIO', 'Eliminación de usuario'
        ACTIVAR_USUARIO = 'ACTIVAR_USUARIO', 'Activación de usuario'
        DESACTIVAR_USUARIO = 'DESACTIVAR_USUARIO', 'Desactivación de usuario'
        RESTABLECER_CLAVE = 'RESTABLECER_CLAVE', 'Restablecimiento de clave'
        CREAR_TARIFA = 'CREAR_TARIFA', 'Creación de tarifa'
        EDITAR_TARIFA = 'EDITAR_TARIFA', 'Edición de tarifa'
        ELIMINAR_TARIFA = 'ELIMINAR_TARIFA', 'Eliminación de tarifa'
        CREAR_COTIZACION = 'CREAR_COTIZACION', 'Creación de cotización'
        ACCESO_DENEGADO = 'ACCESO_DENEGADO', 'Acceso denegado por rol'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='registros_auditoria')
    # Copia del nombre: el registro sigue siendo legible aunque el usuario se elimine
    usuario_nombre = models.CharField('usuario', max_length=150, blank=True)
    accion = models.CharField('acción', max_length=30, choices=Accion.choices, db_index=True)
    objeto_tipo = models.CharField('objeto', max_length=60, blank=True)
    objeto_id = models.CharField('id del objeto', max_length=40, blank=True)
    detalle = models.JSONField('detalle', default=dict, blank=True, encoder=DjangoJSONEncoder)
    ip = models.GenericIPAddressField('dirección IP', null=True, blank=True)
    creado_en = models.DateTimeField('fecha y hora', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'registro de auditoría'
        verbose_name_plural = 'registros de auditoría'
        ordering = ['-creado_en', '-id']
        indexes = [
            models.Index(fields=['accion', '-creado_en'], name='ix_audit_accion_fecha'),
            models.Index(fields=['usuario', '-creado_en'], name='ix_audit_usuario_fecha'),
        ]

    def __str__(self):
        return f'{self.creado_en:%Y-%m-%d %H:%M:%S} · {self.usuario_nombre or "anónimo"} · {self.accion}'

    @property
    def detalle_texto(self) -> str:
        return json.dumps(self.detalle, ensure_ascii=False, default=str) if self.detalle else ''

    # Inmutabilidad: un registro de auditoría no se modifica ni se elimina
    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError('Los registros de auditoría no se pueden modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Los registros de auditoría no se pueden eliminar.')
