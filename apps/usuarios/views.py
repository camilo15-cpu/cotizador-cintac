from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView

from apps.auditoria.models import AuditLog
from apps.auditoria.services import registrar

from .forms import CambioClaveForm, LoginForm, UsuarioCrearForm
from .models import Usuario
from .permisos import SoloAdminMixin
from .reglas_clave import REGLAS
from .seguridad import generar_clave_temporal

Accion = AuditLog.Accion


# ------------------------------------------------------------------ Login / cambio de clave
class LoginView(auth_views.LoginView):
    template_name = 'usuarios/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # Primer ingreso: se envía directo al cambio obligatorio de contraseña
        if self.request.user.primer_ingreso:
            return reverse('usuarios:cambiar_clave')
        return super().get_default_redirect_url()


class CambiarClaveView(LoginRequiredMixin, FormView):
    template_name = 'usuarios/cambiar_clave.html'
    form_class = CambioClaveForm
    success_url = reverse_lazy('cotizaciones:simulador')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['obligatorio'] = self.request.user.primer_ingreso
        contexto['reglas'] = [mensaje for _id, mensaje, _patron in REGLAS]
        return contexto

    def form_valid(self, form):
        era_primer_ingreso = self.request.user.primer_ingreso
        form.guardar()
        update_session_auth_hash(self.request, self.request.user)   # mantiene la sesión abierta
        registrar(Accion.CAMBIAR_CLAVE, request=self.request, detalle={'primer_ingreso': era_primer_ingreso})
        messages.success(self.request, 'Contraseña actualizada correctamente.')
        return super().form_valid(form)


# ------------------------------------------------------------------ Gestión de usuarios (solo Administrador)
class UsuarioListView(SoloAdminMixin, ListView):
    model = Usuario
    template_name = 'usuarios/lista.html'
    context_object_name = 'usuarios'


class UsuarioCrearView(SoloAdminMixin, FormView):
    template_name = 'usuarios/crear.html'
    form_class = UsuarioCrearForm
    success_url = reverse_lazy('usuarios:lista')

    def form_valid(self, form):
        temporal = generar_clave_temporal()
        usuario = form.save(commit=False)
        usuario.set_password(temporal)
        usuario.primer_ingreso = True
        usuario.save()
        registrar(Accion.CREAR_USUARIO, request=self.request, objeto=usuario,
                  detalle={'usuario': usuario.username, 'rol': usuario.rol})
        messages.warning(
            self.request,
            f'Usuario «{usuario.username}» creado. Contraseña temporal: {temporal} — '
            'entrégala por un canal seguro; no se volverá a mostrar.')
        return super().form_valid(form)


class UsuarioAccionView(SoloAdminMixin, View):
    """Acciones del administrador sobre un usuario (siempre por POST y con auditoría)."""
    http_method_names = ['post']

    def post(self, request, pk, accion):
        objetivo = get_object_or_404(Usuario, pk=pk)
        manejadores = {
            'desbloquear': self._desbloquear,
            'activar': self._activar,
            'desactivar': self._desactivar,
            'restablecer': self._restablecer,
            'eliminar': self._eliminar,
        }
        manejador = manejadores.get(accion)
        if manejador is None:
            raise Http404
        manejador(request, objetivo)
        return redirect('usuarios:lista')

    # ---- reglas de protección
    @staticmethod
    def _es_el_mismo(request, objetivo):
        return objetivo.pk == request.user.pk

    @staticmethod
    def _ultimo_admin(objetivo):
        return (objetivo.es_administrador and objetivo.is_active and not objetivo.bloqueado and
                not Usuario.objects.filter(rol=Usuario.Rol.ADMINISTRADOR, is_active=True, bloqueado=False)
                .exclude(pk=objetivo.pk).exists())

    # ---- acciones
    def _desbloquear(self, request, objetivo):
        if not objetivo.bloqueado:
            messages.info(request, f'«{objetivo.username}» no está bloqueado.')
            return
        objetivo.desbloquear()
        registrar(Accion.DESBLOQUEAR_USUARIO, request=request, objeto=objetivo,
                  detalle={'usuario': objetivo.username})
        messages.success(request, f'Usuario «{objetivo.username}» desbloqueado.')

    def _activar(self, request, objetivo):
        objetivo.is_active = True
        objetivo.save(update_fields=['is_active'])
        registrar(Accion.ACTIVAR_USUARIO, request=request, objeto=objetivo, detalle={'usuario': objetivo.username})
        messages.success(request, f'Usuario «{objetivo.username}» activado.')

    def _desactivar(self, request, objetivo):
        if self._es_el_mismo(request, objetivo):
            messages.error(request, 'No puedes desactivar tu propio usuario.')
            return
        if self._ultimo_admin(objetivo):
            messages.error(request, 'Debe existir al menos un administrador activo.')
            return
        objetivo.is_active = False
        objetivo.save(update_fields=['is_active'])
        registrar(Accion.DESACTIVAR_USUARIO, request=request, objeto=objetivo,
                  detalle={'usuario': objetivo.username})
        messages.success(request, f'Usuario «{objetivo.username}» desactivado.')

    def _restablecer(self, request, objetivo):
        if self._es_el_mismo(request, objetivo):
            messages.error(request, 'No puedes restablecer tu propia contraseña desde aquí.')
            return
        temporal = generar_clave_temporal()
        objetivo.set_password(temporal)
        objetivo.primer_ingreso = True
        objetivo.intentos_fallidos = 0
        objetivo.save(update_fields=['password', 'primer_ingreso', 'intentos_fallidos'])
        registrar(Accion.RESTABLECER_CLAVE, request=request, objeto=objetivo,
                  detalle={'usuario': objetivo.username})
        messages.warning(
            request,
            f'Nueva contraseña temporal de «{objetivo.username}»: {temporal} — no se volverá a mostrar.')

    def _eliminar(self, request, objetivo):
        if self._es_el_mismo(request, objetivo):
            messages.error(request, 'No puedes eliminar tu propio usuario.')
            return
        if objetivo.es_administrador and not Usuario.objects.filter(
                rol=Usuario.Rol.ADMINISTRADOR).exclude(pk=objetivo.pk).exists():
            messages.error(request, 'Debe existir al menos un administrador.')
            return
        datos = {'usuario': objetivo.username, 'rol': objetivo.rol}
        pk = objetivo.pk
        try:
            objetivo.delete()
        except ProtectedError:
            messages.error(request, f'«{objetivo.username}» tiene cotizaciones registradas y no se puede eliminar. '
                                    'Desactívalo en su lugar.')
            return
        registrar(Accion.ELIMINAR_USUARIO, request=request, objeto_tipo='Usuario', objeto_id=str(pk), detalle=datos)
        messages.success(request, f'Usuario «{datos["usuario"]}» eliminado.')
