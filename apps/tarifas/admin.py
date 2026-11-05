from django.contrib import admin

from .models import Embarcador, Puerto, Tarifa

admin.site.register(Embarcador)
admin.site.register(Puerto)


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ('embarcador', 'puerto_origen', 'puerto_destino', 'tipo_cobro', 'monto_usd', 'dias_transito')
    list_filter = ('tipo_cobro', 'embarcador')
