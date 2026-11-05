from django.urls import path

from . import views

app_name = 'cotizaciones'

urlpatterns = [
    path('', views.SimuladorView.as_view(), name='simulador'),
    path('comparador/', views.ComparadorView.as_view(), name='comparador'),
    path('historial/', views.HistorialView.as_view(), name='historial'),
    path('<int:pk>/', views.CotizacionDetalleView.as_view(), name='detalle'),
]
