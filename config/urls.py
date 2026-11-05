"""Rutas principales del proyecto."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='cotizaciones:simulador', permanent=False), name='inicio'),
    path('usuarios/', include('apps.usuarios.urls')),
    path('tarifas/', include('apps.tarifas.urls')),
    path('cotizaciones/', include('apps.cotizaciones.urls')),
    path('auditoria/', include('apps.auditoria.urls')),
]
