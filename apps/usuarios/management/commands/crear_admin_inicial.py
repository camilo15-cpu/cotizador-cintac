import os

from django.core.management.base import BaseCommand

from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = ('Crea el administrador inicial usando ADMIN_USERNAME y ADMIN_PASSWORD (variables de entorno). '
            'Es idempotente: si el usuario ya existe no hace nada. Debe cambiar la clave en su primer ingreso.')

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME', '').strip().lower()
        password = os.environ.get('ADMIN_PASSWORD', '')
        nombre = os.environ.get('ADMIN_NOMBRE', 'Administrador CINTAC').strip()
        if not username or not password:
            self.stdout.write('ADMIN_USERNAME / ADMIN_PASSWORD no definidos: no se crea administrador inicial.')
            return
        if Usuario.objects.filter(username=username).exists():
            self.stdout.write(f'El usuario «{username}» ya existe: no se modifica.')
            return
        partes = nombre.split(' ', 1)
        usuario = Usuario.objects.create_superuser(
            username=username, password=password, rol=Usuario.Rol.ADMINISTRADOR,
            first_name=partes[0], last_name=partes[1] if len(partes) > 1 else '',
            primer_ingreso=True)
        self.stdout.write(self.style.SUCCESS(
            f'Administrador «{usuario.username}» creado. Deberá cambiar la contraseña al ingresar.'))
