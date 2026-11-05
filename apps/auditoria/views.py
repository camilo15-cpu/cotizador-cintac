from django.utils.dateparse import parse_date
from django.views.generic import ListView

from apps.usuarios.permisos import SoloAdminMixin

from .models import AuditLog


class AuditLogListView(SoloAdminMixin, ListView):
    """Bitácora de auditoría (solo lectura, solo Administrador) con filtros y paginación."""
    model = AuditLog
    template_name = 'auditoria/lista.html'
    context_object_name = 'registros'
    paginate_by = 25

    def get_queryset(self):
        consulta = AuditLog.objects.select_related('usuario')
        accion = self.request.GET.get('accion', '')
        usuario = self.request.GET.get('usuario', '').strip()
        desde = parse_date(self.request.GET.get('desde', '') or '')
        hasta = parse_date(self.request.GET.get('hasta', '') or '')
        if accion in AuditLog.Accion.values:
            consulta = consulta.filter(accion=accion)
        if usuario:
            consulta = consulta.filter(usuario_nombre__icontains=usuario)
        if desde:
            consulta = consulta.filter(creado_en__date__gte=desde)
        if hasta:
            consulta = consulta.filter(creado_en__date__lte=hasta)
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        parametros = self.request.GET.copy()
        parametros.pop('page', None)
        contexto['acciones'] = AuditLog.Accion.choices
        contexto['filtros'] = self.request.GET
        contexto['querystring'] = parametros.urlencode()
        return contexto
