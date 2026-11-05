from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'rol', 'estado', 'primer_ingreso')
    list_filter = ('rol', 'bloqueado', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Seguridad CINTAC', {'fields': ('rol', 'primer_ingreso', 'intentos_fallidos', 'bloqueado')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos CINTAC', {'fields': ('first_name', 'last_name', 'rol')}),
    )
