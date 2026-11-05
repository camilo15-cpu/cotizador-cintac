from django.contrib import admin

from .models import Cotizacion


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero', 'usuario', 'ruta', 'embarcador', 'total_usd', 'total_clp', 'creada_en')
    list_filter = ('embarcador', 'acogido_tlc')
    search_fields = ('numero', 'referencia', 'solicitante')
    readonly_fields = [f.name for f in Cotizacion._meta.fields]
