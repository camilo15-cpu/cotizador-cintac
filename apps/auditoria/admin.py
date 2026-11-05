from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Solo lectura: nadie puede crear, editar ni borrar registros desde el admin."""
    list_display = ('creado_en', 'usuario_nombre', 'accion', 'objeto_tipo', 'objeto_id', 'ip')
    list_filter = ('accion',)
    search_fields = ('usuario_nombre', 'objeto_tipo', 'objeto_id')
    date_hierarchy = 'creado_en'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
