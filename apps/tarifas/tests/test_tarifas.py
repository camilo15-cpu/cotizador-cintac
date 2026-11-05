from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.tarifas.models import Embarcador, Puerto, Tarifa
from apps.usuarios.models import Usuario


def crear_tarifa(embarcador='Maersk', origen='Shanghai', destino='San Antonio', cobro='CONTENEDOR',
                 monto='2850.00', dias=32):
    e, _ = Embarcador.objects.get_or_create(nombre=embarcador)
    o, _ = Puerto.objects.get_or_create(nombre=origen)
    d, _ = Puerto.objects.get_or_create(nombre=destino)
    return Tarifa.objects.create(embarcador=e, puerto_origen=o, puerto_destino=d, tipo_cobro=cobro,
                                 monto_usd=Decimal(monto), dias_transito=dias)


class RestriccionesBaseDeDatosTests(TestCase):
    def test_no_permite_tarifa_duplicada(self):
        crear_tarifa()
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_tarifa()

    def test_origen_y_destino_deben_ser_distintos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_tarifa(origen='San Antonio', destino='San Antonio')

    def test_monto_debe_ser_positivo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_tarifa(monto='0.00')


class MantenedorTarifasTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user('admin1', password='Cintac#2026', rol=Usuario.Rol.ADMINISTRADOR,
                                                 primer_ingreso=False)
        self.analista = Usuario.objects.create_user('analista1', password='Cintac#2026', primer_ingreso=False)
        self.datos = {'embarcador': 'ONE', 'puerto_origen': 'Qingdao', 'puerto_destino': 'San Antonio',
                      'tipo_cobro': 'CONTENEDOR', 'monto_usd': '2500.00', 'dias_transito': 29}

    def test_admin_crea_tarifa_y_se_normalizan_embarcador_y_puertos(self):
        self.client.force_login(self.admin)
        crear_tarifa(embarcador='Maersk', origen='Shanghai')
        self.datos.update(embarcador='  maersk ', puerto_origen='shanghai')
        self.client.post(reverse('tarifas:crear'), self.datos)
        self.assertEqual(Embarcador.objects.filter(nombre__iexact='maersk').count(), 1)   # no se duplica
        self.assertEqual(Puerto.objects.filter(nombre__iexact='shanghai').count(), 1)
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.CREAR_TARIFA).exists())

    def test_rechaza_duplicado_y_mismo_origen_destino(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('tarifas:crear'), self.datos)
        self.assertContains(self.client.post(reverse('tarifas:crear'), self.datos), 'Ya existe')
        self.datos.update(embarcador='Otro', puerto_destino='Qingdao')
        self.assertContains(self.client.post(reverse('tarifas:crear'), self.datos), 'distinto al de origen')

    def test_valida_rangos(self):
        self.client.force_login(self.admin)
        for campo, valor in (('monto_usd', '-5'), ('monto_usd', '0'), ('dias_transito', 0), ('dias_transito', 400)):
            with self.subTest(campo=campo, valor=valor):
                self.client.post(reverse('tarifas:crear'), {**self.datos, campo: valor})
                self.assertEqual(Tarifa.objects.count(), 0)

    def test_editar_registra_antes_y_despues(self):
        tarifa = crear_tarifa()
        self.client.force_login(self.admin)
        self.client.post(reverse('tarifas:editar', args=[tarifa.pk]), {
            'embarcador': 'Maersk', 'puerto_origen': 'Shanghai', 'puerto_destino': 'San Antonio',
            'tipo_cobro': 'CONTENEDOR', 'monto_usd': '2900.00', 'dias_transito': 30})
        tarifa.refresh_from_db()
        self.assertEqual(tarifa.monto_usd, Decimal('2900.00'))
        registro = AuditLog.objects.get(accion=AuditLog.Accion.EDITAR_TARIFA)
        self.assertEqual(registro.detalle['antes']['monto_usd'], '2850.00')
        self.assertEqual(registro.detalle['despues']['monto_usd'], '2900.00')

    def test_eliminar_tarifa(self):
        tarifa = crear_tarifa()
        self.client.force_login(self.admin)
        self.client.post(reverse('tarifas:eliminar', args=[tarifa.pk]))
        self.assertFalse(Tarifa.objects.filter(pk=tarifa.pk).exists())
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.ELIMINAR_TARIFA).exists())

    def test_analista_no_puede_modificar_tarifas(self):
        tarifa = crear_tarifa()
        self.client.force_login(self.analista)
        self.assertEqual(self.client.post(reverse('tarifas:crear'), self.datos).status_code, 403)
        self.assertEqual(self.client.post(reverse('tarifas:eliminar', args=[tarifa.pk])).status_code, 403)
        self.assertTrue(Tarifa.objects.filter(pk=tarifa.pk).exists())
