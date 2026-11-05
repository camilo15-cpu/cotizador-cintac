from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.auditoria.services import obtener_ip, registrar
from apps.usuarios.models import Usuario


class AuditLogTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user('admin1', password='Cintac#2026', rol=Usuario.Rol.ADMINISTRADOR,
                                                 primer_ingreso=False)

    def test_los_registros_son_inmutables(self):
        registro = registrar(AuditLog.Accion.LOGIN, usuario=self.admin)
        with self.assertRaises(PermissionError):
            registro.accion = AuditLog.Accion.LOGOUT
            registro.save()
        with self.assertRaises(PermissionError):
            registro.delete()

    def test_login_y_logout_se_registran_con_ip(self):
        self.client.post(reverse('usuarios:login'), {'username': 'admin1', 'password': 'Cintac#2026'},
                         REMOTE_ADDR='203.0.113.9')
        self.client.post(reverse('usuarios:logout'))
        acciones = list(AuditLog.objects.values_list('accion', flat=True))
        self.assertIn(AuditLog.Accion.LOGIN, acciones)
        self.assertIn(AuditLog.Accion.LOGOUT, acciones)
        self.assertEqual(AuditLog.objects.get(accion=AuditLog.Accion.LOGIN).ip, '203.0.113.9')

    def test_el_nombre_se_conserva_si_se_elimina_el_usuario(self):
        otro = Usuario.objects.create_user('temporal', password='Cintac#2026', primer_ingreso=False)
        registrar(AuditLog.Accion.LOGIN, usuario=otro)
        otro.delete()
        registro = AuditLog.objects.get()
        self.assertIsNone(registro.usuario)
        self.assertEqual(registro.usuario_nombre, 'temporal')

    def test_ip_detras_del_proxy(self):
        class FalsaPeticion:
            META = {'HTTP_X_FORWARDED_FOR': '198.51.100.7, 10.0.0.1', 'REMOTE_ADDR': '10.0.0.1'}
        self.assertEqual(obtener_ip(FalsaPeticion()), '198.51.100.7')
        FalsaPeticion.META = {'HTTP_X_FORWARDED_FOR': 'no-es-una-ip', 'REMOTE_ADDR': ''}
        self.assertIsNone(obtener_ip(FalsaPeticion()))

    def test_vista_con_filtros_solo_para_administrador(self):
        registrar(AuditLog.Accion.CREAR_TARIFA, usuario=self.admin, detalle={'monto_usd': '100.00'})
        registrar(AuditLog.Accion.LOGIN, usuario=self.admin)
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('auditoria:lista'), {'accion': 'CREAR_TARIFA'})
        self.assertEqual(respuesta.status_code, 200)
        registros = respuesta.context['registros']
        self.assertTrue(all(r.accion == 'CREAR_TARIFA' for r in registros))
        self.assertEqual(len(registros), 1)
