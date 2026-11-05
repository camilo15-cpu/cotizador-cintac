from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.tarifas.models import Embarcador, Puerto, Tarifa
from apps.usuarios.models import Usuario

TARIFAS = [
    ('Maersk', 'Shanghai', 'San Antonio', 'CONTENEDOR', '2850.00', 32),
    ('MSC', 'Shanghai', 'San Antonio', 'CONTENEDOR', '2700.00', 38),
    ('Hapag-Lloyd', 'Shanghai', 'San Antonio', 'CONTENEDOR', '3050.00', 28),
    ('Maersk', 'Ningbo', 'San Antonio', 'CONTENEDOR', '2600.00', 35),
    ('MSC', 'Ningbo', 'San Antonio', 'TONELADA', '118.00', 42),
    ('Hapag-Lloyd', 'Ningbo', 'San Antonio', 'CONTENEDOR', '2750.00', 30),
]
PAISES = {'Shanghai': 'China', 'Ningbo': 'China', 'San Antonio': 'Chile'}
CLAVE_DEMO = 'Cintac#2026'


class Command(BaseCommand):
    help = 'Carga las tarifas de ejemplo. Con --usuarios-demo crea además 3 usuarios de prueba (NO usar en producción).'

    def add_arguments(self, parser):
        parser.add_argument('--usuarios-demo', action='store_true',
                            help=f'Crea admin_cintac, analista1 y analista2 con la clave {CLAVE_DEMO}')

    def handle(self, *args, **options):
        for emb, origen, destino, cobro, monto, dias in TARIFAS:
            e, _ = Embarcador.objects.get_or_create(nombre=emb)
            o, _ = Puerto.objects.get_or_create(nombre=origen, defaults={'pais': PAISES[origen]})
            d, _ = Puerto.objects.get_or_create(nombre=destino, defaults={'pais': PAISES[destino]})
            Tarifa.objects.get_or_create(embarcador=e, puerto_origen=o, puerto_destino=d, tipo_cobro=cobro,
                                         defaults={'monto_usd': Decimal(monto), 'dias_transito': dias})
        self.stdout.write(self.style.SUCCESS(f'Tarifas de ejemplo cargadas ({Tarifa.objects.count()} en total).'))

        if options['usuarios_demo']:
            demos = [('admin_cintac', 'Administrador', 'CINTAC', Usuario.Rol.ADMINISTRADOR, False),
                     ('analista1', 'Analista', 'Uno', Usuario.Rol.ANALISTA, False),
                     ('analista2', 'Analista', 'Dos', Usuario.Rol.ANALISTA, True)]
            for username, nombre, apellido, rol, primer in demos:
                if not Usuario.objects.filter(username=username).exists():
                    Usuario.objects.create_user(username=username, password=CLAVE_DEMO, first_name=nombre,
                                                last_name=apellido, rol=rol, primer_ingreso=primer)
            self.stdout.write(self.style.WARNING(f'Usuarios demo listos (clave {CLAVE_DEMO}). No los uses en producción.'))
