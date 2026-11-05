from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.auditoria.models import AuditLog
from apps.auditoria.services import registrar

from .models import MAX_INTENTOS, Usuario


class LoginForm(AuthenticationForm):
    """Login con control de intentos fallidos: al 3er error consecutivo la cuenta se bloquea."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Correo / Usuario'
        self.fields['password'].label = 'Contraseña'

    def clean(self):
        username = (self.cleaned_data.get('username') or '').strip().lower()
        password = self.cleaned_data.get('password')
        if not username or not password:
            return self.cleaned_data

        usuario = Usuario.objects.filter(username=username).first()

        # Cuenta bloqueada o inactiva: se niega el acceso aunque la clave sea correcta
        if usuario is not None and (usuario.bloqueado or not usuario.is_active):
            registrar(AuditLog.Accion.LOGIN_RECHAZADO, request=self.request, usuario=usuario,
                      usuario_nombre=username,
                      detalle={'motivo': 'cuenta bloqueada' if usuario.bloqueado else 'cuenta inactiva'})
            if usuario.bloqueado:
                raise ValidationError(
                    'La cuenta está bloqueada por intentos fallidos. Contacta a un administrador para desbloquearla.',
                    code='bloqueado')
            raise ValidationError('La cuenta está inactiva. Contacta a un administrador.', code='inactivo')

        self.user_cache = authenticate(self.request, username=username, password=password)

        if self.user_cache is None:
            if usuario is None:
                raise ValidationError('Usuario o contraseña incorrectos.', code='invalid_login')
            usuario.registrar_fallo()
            if usuario.bloqueado:
                registrar(AuditLog.Accion.BLOQUEAR_USUARIO, request=self.request, usuario_nombre='sistema',
                          objeto=usuario, detalle={'motivo': f'{MAX_INTENTOS} intentos fallidos consecutivos'})
                raise ValidationError(
                    f'Contraseña incorrecta. Superaste los {MAX_INTENTOS} intentos permitidos: '
                    'la cuenta fue bloqueada. Contacta a un administrador.', code='bloqueado')
            restantes = MAX_INTENTOS - usuario.intentos_fallidos
            raise ValidationError(
                f'Contraseña incorrecta. Te {"queda 1 intento" if restantes == 1 else f"quedan {restantes} intentos"} '
                'antes del bloqueo.', code='invalid_login')

        usuario.reiniciar_intentos()                    # acierto: se reinicia el contador consecutivo
        return self.cleaned_data


class CambioClaveForm(forms.Form):
    """Cambio de contraseña con confirmación idéntica y las reglas de complejidad (regex)."""
    nueva_clave = forms.CharField(label='Nueva contraseña', strip=False,
                                  widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    confirmar_clave = forms.CharField(label='Repetir contraseña', strip=False,
                                      widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        datos = super().clean()
        nueva, confirmar = datos.get('nueva_clave'), datos.get('confirmar_clave')
        if nueva:
            try:
                validate_password(nueva, self.user)      # ejecuta todos los AUTH_PASSWORD_VALIDATORS
            except ValidationError as error:
                self.add_error('nueva_clave', error)
            if self.user.check_password(nueva):
                self.add_error('nueva_clave', 'La nueva contraseña debe ser distinta de la actual (temporal).')
        if nueva and confirmar and nueva != confirmar:
            self.add_error('confirmar_clave', 'Las contraseñas no coinciden.')
        return datos

    def guardar(self):
        usuario = self.user
        usuario.set_password(self.cleaned_data['nueva_clave'])
        usuario.primer_ingreso = False
        usuario.intentos_fallidos = 0
        usuario.save(update_fields=['password', 'primer_ingreso', 'intentos_fallidos'])
        return usuario


class UsuarioCrearForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'username', 'rol']
        labels = {'first_name': 'Nombres', 'last_name': 'Apellidos',
                  'username': 'Correo / Usuario', 'rol': 'Rol'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['username'].help_text = 'Se guarda en minúsculas. Sin espacios.'

    def clean_username(self):
        username = self.cleaned_data['username'].strip().lower()
        if '@' in username:
            try:
                forms.EmailField().clean(username)
            except ValidationError:
                raise ValidationError('El correo ingresado no tiene un formato válido.')
        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError('Ya existe un usuario con ese nombre.')
        return username
