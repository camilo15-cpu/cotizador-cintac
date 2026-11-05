from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.UsuarioListView.as_view(), name='lista'),
    path('nuevo/', views.UsuarioCrearView.as_view(), name='crear'),
    path('ingresar/', views.LoginView.as_view(), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('cambiar-clave/', views.CambiarClaveView.as_view(), name='cambiar_clave'),
    path('<int:pk>/<slug:accion>/', views.UsuarioAccionView.as_view(), name='accion'),
]
