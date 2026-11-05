import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Cotizacion(models.Model):
    """Historial de simulaciones. Guarda una copia de la tarifa usada para que el histórico no cambie
    aunque la tarifa se modifique o elimine después (desnormalización intencional de datos históricos)."""

    numero = models.CharField('N° de cotización', max_length=24, unique=True, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cotizaciones')
    tarifa = models.ForeignKey('tarifas.Tarifa', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='cotizaciones')
    referencia = models.CharField('referencia', max_length=60, blank=True)
    solicitante = models.CharField('solicitante', max_length=120)

    # Copia de la tarifa al momento de cotizar
    embarcador = models.CharField(max_length=80)
    ruta = models.CharField(max_length=170)
    tipo_cobro = models.CharField(max_length=10)
    tarifa_usd = models.DecimalField(max_digits=10, decimal_places=2)
    dias_transito = models.PositiveSmallIntegerField()

    # Datos ingresados
    toneladas = models.DecimalField(max_digits=12, decimal_places=2)
    contenedores = models.PositiveIntegerField()
    fob_usd = models.DecimalField('FOB (USD)', max_digits=14, decimal_places=2)
    acogido_tlc = models.BooleanField('acogido a TLC', default=False)
    tipo_cambio = models.DecimalField('tipo de cambio', max_digits=10, decimal_places=2)

    # Resultados
    porcentaje_contingencia = models.DecimalField(max_digits=5, decimal_places=4)
    flete_base_usd = models.DecimalField(max_digits=16, decimal_places=2)
    recargo_usd = models.DecimalField(max_digits=16, decimal_places=2)
    flete_total_usd = models.DecimalField(max_digits=16, decimal_places=2)
    cif_usd = models.DecimalField(max_digits=16, decimal_places=2)
    arancel_usd = models.DecimalField(max_digits=16, decimal_places=2)
    iva_usd = models.DecimalField(max_digits=16, decimal_places=2)
    total_usd = models.DecimalField('total (USD)', max_digits=16, decimal_places=2)
    total_clp = models.BigIntegerField('total (CLP)')

    creada_en = models.DateTimeField('fecha', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'cotización'
        verbose_name_plural = 'cotizaciones'
        ordering = ['-creada_en']
        indexes = [models.Index(fields=['usuario', '-creada_en'], name='ix_cotiz_usuario_fecha')]

    def __str__(self):
        return self.numero

    @property
    def base_iva_usd(self) -> Decimal:
        return self.cif_usd + self.arancel_usd

    @property
    def porcentaje_contingencia_visible(self) -> Decimal:
        return (self.porcentaje_contingencia * 100).normalize()

    @classmethod
    def _generar_numero(cls) -> str:
        hoy = timezone.localdate().strftime('%Y%m%d')
        while True:
            candidato = f'COT-{hoy}-{secrets.token_hex(3).upper()}'
            if not cls.objects.filter(numero=candidato).exists():
                return candidato

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generar_numero()
        super().save(*args, **kwargs)
