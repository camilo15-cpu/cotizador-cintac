from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.auditoria.models import AuditLog
from apps.auditoria.services import registrar
from apps.tarifas.models import Tarifa
from apps.usuarios.permisos import AdminOAnalistaMixin

from .forms import ComparadorForm, CotizacionForm
from .models import Cotizacion
from .services import OpcionTarifa, ahorro_maximo, calcular_cotizacion, comparar


class SimuladorView(AdminOAnalistaMixin, FormView):
    """Simulador de cotización: valida, calcula en el servidor y guarda el historial."""
    template_name = 'cotizaciones/simulador.html'
    form_class = CotizacionForm

    def get_initial(self):
        return {'solicitante': self.request.user.get_full_name() or self.request.user.username}

    @transaction.atomic
    def form_valid(self, form):
        d = form.cleaned_data
        tarifa = d['tarifa']
        resultado = calcular_cotizacion(
            monto_tarifa=tarifa.monto_usd, tipo_cobro=tarifa.tipo_cobro, toneladas=d['toneladas'],
            contenedores=d['contenedores'], fob=d['fob_usd'], dias_transito=d['dias_transito'],
            acogido_tlc=d['acogido_tlc'], tipo_cambio=d['tipo_cambio'])
        cotizacion = Cotizacion.objects.create(
            usuario=self.request.user, tarifa=tarifa, referencia=d['referencia'], solicitante=d['solicitante'],
            embarcador=tarifa.embarcador.nombre, ruta=tarifa.ruta, tipo_cobro=tarifa.tipo_cobro,
            tarifa_usd=tarifa.monto_usd, dias_transito=d['dias_transito'], toneladas=d['toneladas'],
            contenedores=resultado.contenedores, fob_usd=d['fob_usd'], acogido_tlc=d['acogido_tlc'],
            tipo_cambio=d['tipo_cambio'], porcentaje_contingencia=resultado.porcentaje_contingencia,
            flete_base_usd=resultado.flete_base, recargo_usd=resultado.recargo,
            flete_total_usd=resultado.flete_total, cif_usd=resultado.cif, arancel_usd=resultado.arancel,
            iva_usd=resultado.iva, total_usd=resultado.total_usd, total_clp=resultado.total_clp)
        registrar(AuditLog.Accion.CREAR_COTIZACION, request=self.request, objeto=cotizacion,
                  detalle={'numero': cotizacion.numero, 'ruta': cotizacion.ruta,
                           'total_usd': resultado.total_usd, 'total_clp': resultado.total_clp})
        for aviso in form.advertencias:
            messages.warning(self.request, aviso)
        return redirect('cotizaciones:detalle', pk=cotizacion.pk)


class CotizacionDetalleView(AdminOAnalistaMixin, DetailView):
    template_name = 'cotizaciones/detalle.html'
    context_object_name = 'cotizacion'

    def get_queryset(self):
        consulta = Cotizacion.objects.select_related('usuario')
        # El analista solo ve sus propias cotizaciones; el administrador ve todas
        return consulta if self.request.user.es_administrador else consulta.filter(usuario=self.request.user)


class HistorialView(AdminOAnalistaMixin, ListView):
    template_name = 'cotizaciones/historial.html'
    context_object_name = 'cotizaciones'
    paginate_by = 20

    def get_queryset(self):
        consulta = Cotizacion.objects.select_related('usuario')
        return consulta if self.request.user.es_administrador else consulta.filter(usuario=self.request.user)


class ComparadorView(AdminOAnalistaMixin, TemplateView):
    """Compara los embarcadores disponibles para una misma ruta (datos por GET para poder compartir el enlace)."""
    template_name = 'cotizaciones/comparador.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        form = ComparadorForm(self.request.GET or None)
        contexto.update({'form': form, 'comparadas': None, 'ahorro': None})
        if form.is_bound and form.is_valid():
            origen_id, destino_id = form.ids_de_ruta()
            tarifas = (Tarifa.objects.filter(puerto_origen_id=origen_id, puerto_destino_id=destino_id)
                       .select_related('embarcador', 'puerto_origen', 'puerto_destino'))
            opciones = [OpcionTarifa(id=t.pk, embarcador=t.embarcador.nombre, tipo_cobro=t.tipo_cobro,
                                     monto=t.monto_usd, dias_transito=t.dias_transito) for t in tarifas]
            d = form.cleaned_data
            comparadas = comparar(opciones, toneladas=d['toneladas'], fob=d['fob_usd'],
                                  acogido_tlc=d['acogido_tlc'], tipo_cambio=d['tipo_cambio'])
            contexto['comparadas'] = comparadas
            contexto['ahorro'] = ahorro_maximo(comparadas)
        return contexto
