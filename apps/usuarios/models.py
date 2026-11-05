from django.contrib.auth.models import AbstractUser
from django.db import models, transaction

MAX_INTENTOS = 3


class Usuario(AbstractUser):
    """Usuario del sistema con control de acceso por roles (RBAC) y datos de seguridad."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = 'ADMIN', 'Administrador'
        ANALISTA = 'ANALISTA', 'Analista'

    rol = models.CharField('rol', max_length=10, choices=Rol.choices, default=Rol.ANALISTA, db_index=True)
    primer_ingreso = models.BooleanField(
        'primer ingreso', default=True,
        help_text='Si está activo, el usuario debe cambiar su contraseña temporal antes de usar el sistema.')
    intentos_fallidos = models.PositiveSmallIntegerField('intentos fallidos', default=0)
    bloqueado = models.BooleanField(
        'bloqueado', default=False,
        help_text='Se activa solo tras 3 intentos fallidos consecutivos. Lo desbloquea un administrador.')

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['username']

    def save(self, *args, **kwargs):
        self.username = self.username.lower()          # el login no distingue mayúsculas
        if self.is_superuser:
            self.rol = self.Rol.ADMINISTRADOR
        super().save(*args, **kwargs)

    # ---- propiedades de apoyo
    @property
    def es_administrador(self) -> bool:
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def estado(self) -> str:
        if self.bloqueado:
            return 'Bloqueado'
        return 'Activo' if self.is_active else 'Inactivo'

    # ---- control de intentos fallidos
    @transaction.atomic
    def registrar_fallo(self):
        """Suma un intento fallido y bloquea la cuenta al llegar a MAX_INTENTOS (seguro ante concurrencia)."""
        actual = Usuario.objects.select_for_update().get(pk=self.pk)
        actual.intentos_fallidos += 1
        if actual.intentos_fallidos >= MAX_INTENTOS:
            actual.bloqueado = True
        actual.save(update_fields=['intentos_fallidos', 'bloqueado'])
        self.intentos_fallidos, self.bloqueado = actual.intentos_fallidos, actual.bloqueado
        return self

    def reiniciar_intentos(self):
        if self.intentos_fallidos:
            self.intentos_fallidos = 0
            self.save(update_fields=['intentos_fallidos'])

    def desbloquear(self):
        self.bloqueado = False
        self.intentos_fallidos = 0
        self.save(update_fields=['bloqueado', 'intentos_fallidos'])
