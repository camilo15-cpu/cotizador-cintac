from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView

from apps.auditoria.models import AuditLog
from apps.auditoria.services import registrar
from apps.usuarios.permisos import SoloAdminMixin

from .forms import TarifaForm
from .models import Tarifa

Accion = AuditLog.Accion


def _consulta():
    return Tarifa.objects.select_related('embarcador', 'puerto_origen', 'puerto_destino')


def _instantanea(tarifa):
    """Datos de la tarifa para guardar en la auditoría."""
    return {'id': tarifa.pk, 'embarcador': tarifa.embarcador.nombre, 'origen': tarifa.puerto_origen.nombre,
            'destino': tarifa.puerto_destino.nombre, 'tipo_cobro': tarifa.tipo_cobro,
            'monto_usd': str(tarifa.monto_usd), 'dias_transito': tarifa.dias_transito}


class TarifaListView(SoloAdminMixin, ListView):
    template_name = 'tarifas/lista.html'
    context_object_name = 'tarifas'

    def get_queryset(self):
        return _consulta()


class TarifaCrearView(SoloAdminMixin, FormView):
    template_name = 'tarifas/form.html'
    form_class = TarifaForm
    success_url = reverse_lazy('tarifas:lista')

    def form_valid(self, form):
        tarifa = form.guardar()
        registrar(Accion.CREAR_TARIFA, request=self.request, objeto=tarifa, detalle=_instantanea(tarifa))
        messages.success(self.request, 'Tarifa creada.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Nueva tarifa'
        return contexto


class TarifaEditarView(SoloAdminMixin, FormView):
    template_name = 'tarifas/form.html'
    form_class = TarifaForm
    success_url = reverse_lazy('tarifas:lista')

    def dispatch(self, request, *args, **kwargs):
        # El rol se verifica en la clase base antes de buscar el objeto
        self._pk = kwargs.get('pk')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.tarifa = get_object_or_404(_consulta(), pk=self._pk)
        kwargs['instance'] = self.tarifa
        return kwargs

    def form_valid(self, form):
        antes = _instantanea(self.tarifa)
        tarifa = form.guardar()
        registrar(Accion.EDITAR_TARIFA, request=self.request, objeto=tarifa,
                  detalle={'antes': antes, 'despues': _instantanea(tarifa)})
        messages.success(self.request, 'Tarifa actualizada.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['titulo'] = 'Editar tarifa'
        return contexto


class TarifaEliminarView(SoloAdminMixin, View):
    http_method_names = ['post']

    def post(self, request, pk):
        tarifa = get_object_or_404(_consulta(), pk=pk)
        datos = _instantanea(tarifa)
        tarifa.delete()
        registrar(Accion.ELIMINAR_TARIFA, request=request, objeto_tipo='Tarifa', objeto_id=str(pk), detalle=datos)
        messages.success(request, 'Tarifa eliminada.')
        return redirect('tarifas:lista')
