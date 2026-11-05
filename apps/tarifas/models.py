from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Puerto(models.Model):
    """Cada puerto se guarda una sola vez (3FN) y las tarifas lo referencian."""
    nombre = models.CharField('nombre', max_length=80, unique=True)
    pais = models.CharField('país', max_length=60, blank=True)

    class Meta:
        verbose_name = 'puerto'
        verbose_name_plural = 'puertos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Embarcador(models.Model):
    nombre = models.CharField('nombre', max_length=80, unique=True)

    class Meta:
        verbose_name = 'embarcador'
        verbose_name_plural = 'embarcadores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Tarifa(models.Model):
    """Flete de un embarcador entre dos puertos, por contenedor o por tonelada."""

    class TipoCobro(models.TextChoices):
        CONTENEDOR = 'CONTENEDOR', 'Por contenedor'
        TONELADA = 'TONELADA', 'Por tonelada'

    embarcador = models.ForeignKey(Embarcador, on_delete=models.PROTECT, related_name='tarifas')
    puerto_origen = models.ForeignKey(Puerto, on_delete=models.PROTECT, related_name='tarifas_origen')
    puerto_destino = models.ForeignKey(Puerto, on_delete=models.PROTECT, related_name='tarifas_destino')
    tipo_cobro = models.CharField('tipo de cobro', max_length=10, choices=TipoCobro.choices)
    monto_usd = models.DecimalField('tarifa (USD)', max_digits=10, decimal_places=2,
                                    validators=[MinValueValidator(Decimal('0.01'))])
    dias_transito = models.PositiveSmallIntegerField('días de tránsito',
                                                     validators=[MinValueValidator(1), MaxValueValidator(365)])
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'tarifa'
        verbose_name_plural = 'tarifas'
        ordering = ['puerto_origen__nombre', 'puerto_destino__nombre', 'monto_usd']
        constraints = [
            models.UniqueConstraint(fields=['embarcador', 'puerto_origen', 'puerto_destino', 'tipo_cobro'],
                                    name='uq_tarifa_embarcador_ruta_cobro'),
            models.CheckConstraint(condition=~models.Q(puerto_origen=models.F('puerto_destino')),
                                   name='ck_tarifa_origen_distinto_destino'),
            models.CheckConstraint(condition=models.Q(monto_usd__gt=0), name='ck_tarifa_monto_positivo'),
        ]
        indexes = [models.Index(fields=['puerto_origen', 'puerto_destino'], name='ix_tarifa_ruta')]

    @property
    def ruta(self) -> str:
        return f'{self.puerto_origen.nombre} → {self.puerto_destino.nombre}'

    def __str__(self):
        unidad = 'cont.' if self.tipo_cobro == self.TipoCobro.CONTENEDOR else 't'
        return f'{self.ruta} · {self.embarcador.nombre} · US$ {self.monto_usd}/{unidad} · {self.dias_transito} días'
