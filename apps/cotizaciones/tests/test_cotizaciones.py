from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.cotizaciones.models import Cotizacion
from apps.tarifas.tests.test_tarifas import crear_tarifa
from apps.usuarios.models import Usuario


class SimuladorTests(TestCase):
    def setUp(self):
        self.analista = Usuario.objects.create_user('analista1', password='Cintac#2026', primer_ingreso=False,
                                                    first_name='Ana', last_name='Lista')
        self.tarifa = crear_tarifa()
        self.client.force_login(self.analista)
        self.url = reverse('cotizaciones:simulador')
        self.datos = {'tarifa': self.tarifa.pk, 'solicitante': 'Ana Lista', 'referencia': 'IMP-1',
                      'toneladas': '60', 'fob_usd': '85000', 'tipo_cambio': '950'}

    def test_calcula_guarda_historial_y_audita(self):
        respuesta = self.client.post(self.url, self.datos)
        cotizacion = Cotizacion.objects.get()
        self.assertRedirects(respuesta, reverse('cotizaciones:detalle', args=[cotizacion.pk]))
        self.assertEqual(cotizacion.contenedores, 3)
        self.assertEqual(cotizacion.total_usd, Decimal('118543.22'))
        self.assertEqual(cotizacion.total_clp, 112616059)
        self.assertEqual(cotizacion.usuario, self.analista)
        self.assertTrue(cotizacion.numero.startswith('COT-'))
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.CREAR_COTIZACION).exists())

    def test_tlc_elimina_el_arancel(self):
        self.client.post(self.url, {**self.datos, 'acogido_tlc': 'on'})
        self.assertEqual(Cotizacion.objects.get().arancel_usd, Decimal('0.00'))

    def test_exceso_de_25_toneladas_por_contenedor_bloquea(self):
        respuesta = self.client.post(self.url, {**self.datos, 'contenedores': '2'})
        self.assertContains(respuesta, 'Decreto 75')
        self.assertEqual(Cotizacion.objects.count(), 0)

    @override_settings(COTIZADOR_BLOQUEAR_EXCESO_PESO=False)
    def test_exceso_solo_advierte_si_el_bloqueo_esta_desactivado(self):
        respuesta = self.client.post(self.url, {**self.datos, 'contenedores': '2'}, follow=True)
        self.assertEqual(Cotizacion.objects.count(), 1)
        self.assertContains(respuesta, 'Decreto 75')

    def test_entradas_invalidas_son_rechazadas(self):
        for campo, valor in (('tipo_cambio', '0'), ('tipo_cambio', '-950'), ('fob_usd', '-1'),
                             ('toneladas', '0'), ('toneladas', '-5'), ('dias_transito', '0')):
            with self.subTest(campo=campo, valor=valor):
                self.client.post(self.url, {**self.datos, campo: valor})
                self.assertEqual(Cotizacion.objects.count(), 0)

    def test_analista_solo_ve_sus_cotizaciones(self):
        self.client.post(self.url, self.datos)
        propia = Cotizacion.objects.get()
        otro = Usuario.objects.create_user('otro', password='Cintac#2026', primer_ingreso=False)
        self.client.force_login(otro)
        self.assertEqual(self.client.get(reverse('cotizaciones:detalle', args=[propia.pk])).status_code, 404)

    def test_administrador_ve_todas(self):
        self.client.post(self.url, self.datos)
        propia = Cotizacion.objects.get()
        admin = Usuario.objects.create_user('admin1', password='Cintac#2026', rol=Usuario.Rol.ADMINISTRADOR,
                                            primer_ingreso=False)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse('cotizaciones:detalle', args=[propia.pk])).status_code, 200)


class ComparadorTests(TestCase):
    def setUp(self):
        self.analista = Usuario.objects.create_user('analista1', password='Cintac#2026', primer_ingreso=False)
        crear_tarifa('Maersk', monto='2850', dias=32)
        crear_tarifa('MSC', monto='2700', dias=38)
        crear_tarifa('Hapag-Lloyd', monto='3050', dias=28)
        self.client.force_login(self.analista)

    def test_marca_la_mas_conveniente_y_la_mas_rapida(self):
        from apps.tarifas.models import Puerto
        ruta = f"{Puerto.objects.get(nombre='Shanghai').pk}-{Puerto.objects.get(nombre='San Antonio').pk}"
        respuesta = self.client.get(reverse('cotizaciones:comparador'), {
            'ruta': ruta, 'toneladas': '60', 'fob_usd': '85000', 'tipo_cambio': '950'})
        comparadas = respuesta.context['comparadas']
        self.assertEqual([c.opcion.embarcador for c in comparadas], ['MSC', 'Maersk', 'Hapag-Lloyd'])
        self.assertEqual(respuesta.context['ahorro'], Decimal('1159.85'))
