from django.urls import path

from . import views

app_name = 'tarifas'

urlpatterns = [
    path('', views.TarifaListView.as_view(), name='lista'),
    path('nueva/', views.TarifaCrearView.as_view(), name='crear'),
    path('<int:pk>/editar/', views.TarifaEditarView.as_view(), name='editar'),
    path('<int:pk>/eliminar/', views.TarifaEliminarView.as_view(), name='eliminar'),
]
