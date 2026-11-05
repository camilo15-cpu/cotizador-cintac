from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Embarcador, Puerto, Tarifa


def _normalizar(texto: str) -> str:
    return ' '.join(texto.split())


class TarifaForm(forms.Form):
    """Formulario de tarifa. Embarcador y puertos se escriben como texto y se crean si no existen."""
    embarcador = forms.CharField(label='Embarcador', max_length=80)
    puerto_origen = forms.CharField(label='Puerto de origen', max_length=80)
    puerto_destino = forms.CharField(label='Puerto de destino', max_length=80)
    tipo_cobro = forms.ChoiceField(label='Tipo de cobro', choices=Tarifa.TipoCobro.choices)
    monto_usd = forms.DecimalField(label='Tarifa (USD)', min_value=Decimal('0.01'), max_digits=10, decimal_places=2)
    dias_transito = forms.IntegerField(label='Días de tránsito', min_value=1, max_value=365)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        if instance is not None and 'initial' not in kwargs:
            kwargs['initial'] = {
                'embarcador': instance.embarcador.nombre, 'puerto_origen': instance.puerto_origen.nombre,
                'puerto_destino': instance.puerto_destino.nombre, 'tipo_cobro': instance.tipo_cobro,
                'monto_usd': instance.monto_usd, 'dias_transito': instance.dias_transito,
            }
        super().__init__(*args, **kwargs)

    def clean_embarcador(self):
        return _normalizar(self.cleaned_data['embarcador'])

    def clean_puerto_origen(self):
        return _normalizar(self.cleaned_data['puerto_origen'])

    def clean_puerto_destino(self):
        return _normalizar(self.cleaned_data['puerto_destino'])

    def clean(self):
        datos = super().clean()
        origen, destino = datos.get('puerto_origen'), datos.get('puerto_destino')
        if origen and destino and origen.casefold() == destino.casefold():
            self.add_error('puerto_destino', 'El puerto de destino debe ser distinto al de origen.')
        if all(datos.get(c) for c in ('embarcador', 'puerto_origen', 'puerto_destino', 'tipo_cobro')):
            repetidas = Tarifa.objects.filter(
                embarcador__nombre__iexact=datos['embarcador'], puerto_origen__nombre__iexact=origen,
                puerto_destino__nombre__iexact=destino, tipo_cobro=datos['tipo_cobro'])
            if self.instance is not None:
                repetidas = repetidas.exclude(pk=self.instance.pk)
            if repetidas.exists():
                raise ValidationError('Ya existe una tarifa de ese embarcador para esa ruta y tipo de cobro.')
        return datos

    @staticmethod
    def _obtener_o_crear(modelo, nombre):
        return modelo.objects.filter(nombre__iexact=nombre).first() or modelo.objects.create(nombre=nombre)

    @transaction.atomic
    def guardar(self):
        d = self.cleaned_data
        tarifa = self.instance or Tarifa()
        tarifa.embarcador = self._obtener_o_crear(Embarcador, d['embarcador'])
        tarifa.puerto_origen = self._obtener_o_crear(Puerto, d['puerto_origen'])
        tarifa.puerto_destino = self._obtener_o_crear(Puerto, d['puerto_destino'])
        tarifa.tipo_cobro = d['tipo_cobro']
        tarifa.monto_usd = d['monto_usd']
        tarifa.dias_transito = d['dias_transito']
        tarifa.save()
        return tarifa
