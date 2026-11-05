from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auditoria'
    verbose_name = 'Auditoría'

    def ready(self):
        from . import signals  # noqa: F401  (conecta login / logout / login fallido)
