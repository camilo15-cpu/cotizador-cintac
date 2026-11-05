from decimal import Decimal

from django import forms
from django.conf import settings

from apps.tarifas.models import Tarifa

from .services import MAX_TON_POR_CONTENEDOR, contenedores_sugeridos, excede_decreto_75


class CotizacionForm(forms.Form):
    tarifa = forms.ModelChoiceField(queryset=Tarifa.objects.none(), label='Tarifa (ruta · embarcador)',
                                    empty_label='Selecciona una tarifa')
    referencia = forms.CharField(label='Referencia / N° de importación', max_length=60, required=False)
    solicitante = forms.CharField(label='Solicitante', max_length=120)
    toneladas = forms.DecimalField(label='Toneladas', min_value=Decimal('0.01'), max_digits=12, decimal_places=2)
    contenedores = forms.IntegerField(label='Contenedores (opcional)', min_value=1, required=False,
                                      help_text='Si lo dejas vacío se usa el mínimo sugerido (25 t por contenedor).')
    fob_usd = forms.DecimalField(label='Valor FOB (USD)', min_value=Decimal('0'), max_digits=14, decimal_places=2)
    dias_transito = forms.IntegerField(label='Días de tránsito (opcional)', min_value=1, max_value=365,
                                       required=False, help_text='Si lo dejas vacío se usan los días de la tarifa.')
    acogido_tlc = forms.BooleanField(label='Acogido a TLC (arancel 0 %)', required=False)
    tipo_cambio = forms.DecimalField(label='Tipo de cambio (CLP por USD)', min_value=Decimal('0.01'),
                                     max_digits=10, decimal_places=2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tarifa'].queryset = Tarifa.objects.select_related('embarcador', 'puerto_origen', 'puerto_destino')
        self.advertencias = []

    def clean(self):
        datos = super().clean()
        tarifa, toneladas = datos.get('tarifa'), datos.get('toneladas')
        if tarifa is None or toneladas is None:
            return datos
        sugeridos = contenedores_sugeridos(toneladas)
        contenedores = datos.get('contenedores') or sugeridos
        if excede_decreto_75(toneladas, contenedores):
            mensaje = (f'Con {contenedores} contenedor(es) la carga supera el máximo de {MAX_TON_POR_CONTENEDOR} t '
                       f'por contenedor (Decreto 75): {toneladas / contenedores:.2f} t por contenedor. '
                       f'Se requieren al menos {sugeridos}.')
            if settings.COTIZADOR_BLOQUEAR_EXCESO_PESO:
                self.add_error('contenedores', mensaje)
            else:
                self.advertencias.append(mensaje)
        datos['contenedores'] = contenedores
        datos['dias_transito'] = datos.get('dias_transito') or tarifa.dias_transito
        return datos


class ComparadorForm(forms.Form):
    ruta = forms.ChoiceField(label='Ruta')
    toneladas = forms.DecimalField(label='Toneladas', min_value=Decimal('0.01'), max_digits=12, decimal_places=2)
    fob_usd = forms.DecimalField(label='Valor FOB (USD)', min_value=Decimal('0'), max_digits=14, decimal_places=2)
    tipo_cambio = forms.DecimalField(label='Tipo de cambio (CLP por USD)', min_value=Decimal('0.01'),
                                     max_digits=10, decimal_places=2)
    acogido_tlc = forms.BooleanField(label='Acogido a TLC (arancel 0 %)', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rutas = (Tarifa.objects.values_list('puerto_origen_id', 'puerto_destino_id',
                                            'puerto_origen__nombre', 'puerto_destino__nombre')
                 .distinct().order_by('puerto_origen__nombre', 'puerto_destino__nombre'))
        self.fields['ruta'].choices = [(f'{o}-{d}', f'{no} → {nd}') for o, d, no, nd in rutas]

    def ids_de_ruta(self):
        origen, destino = self.cleaned_data['ruta'].split('-')
        return int(origen), int(destino)
