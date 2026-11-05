"""Caso de Prueba CP01 (autenticación y seguridad) y control de acceso por rol."""
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import AuditLog
from apps.usuarios.models import Usuario

CLAVE = 'Cintac#2026'
Rol = Usuario.Rol


def crear(username, rol=Rol.ANALISTA, primer_ingreso=False, clave=CLAVE):
    return Usuario.objects.create_user(username=username, password=clave, rol=rol, first_name='Nombre',
                                       last_name='Apellido', primer_ingreso=primer_ingreso)


class LoginTests(TestCase):
    def setUp(self):
        self.analista = crear('analista1')
        self.url = reverse('usuarios:login')

    def ingresar(self, clave, usuario='analista1'):
        return self.client.post(self.url, {'username': usuario, 'password': clave})

    def test_login_correcto_entra_al_simulador(self):
        respuesta = self.ingresar(CLAVE)
        self.assertRedirects(respuesta, reverse('cotizaciones:simulador'))

    def test_usuario_sin_distinguir_mayusculas(self):
        self.assertEqual(self.ingresar(CLAVE, usuario='ANALISTA1').status_code, 302)

    def test_usuario_inexistente_mensaje_generico(self):
        respuesta = self.ingresar('x', usuario='noexiste')
        self.assertContains(respuesta, 'Usuario o contraseña incorrectos.')

    def test_avisa_los_intentos_restantes(self):
        self.assertContains(self.ingresar('mala'), 'Te quedan 2 intentos')
        self.assertContains(self.ingresar('mala'), 'Te queda 1 intento')

    def test_tres_fallos_bloquean_la_cuenta(self):
        for _ in range(3):
            respuesta = self.ingresar('mala')
        self.assertContains(respuesta, 'bloqueada')
        self.analista.refresh_from_db()
        self.assertTrue(self.analista.bloqueado)
        self.assertEqual(self.analista.intentos_fallidos, 3)

    def test_cuenta_bloqueada_niega_acceso_aunque_la_clave_sea_correcta(self):
        for _ in range(3):
            self.ingresar('mala')
        respuesta = self.ingresar(CLAVE)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_acierto_reinicia_el_contador(self):
        self.ingresar('mala')
        self.ingresar('mala')
        self.ingresar(CLAVE)
        self.client.post(reverse('usuarios:logout'))
        self.assertContains(self.ingresar('mala'), 'Te quedan 2 intentos')

    def test_usuario_inactivo_no_entra(self):
        self.analista.is_active = False
        self.analista.save()
        self.assertContains(self.ingresar(CLAVE), 'inactiva')

    def test_bloqueo_queda_en_la_auditoria(self):
        for _ in range(3):
            self.ingresar('mala')
        acciones = set(AuditLog.objects.values_list('accion', flat=True))
        self.assertIn(AuditLog.Accion.LOGIN_FALLIDO, acciones)
        self.assertIn(AuditLog.Accion.BLOQUEAR_USUARIO, acciones)


class PrimerIngresoTests(TestCase):
    def setUp(self):
        self.usuario = crear('nuevo', primer_ingreso=True, clave='Temporal#1')
        self.client.post(reverse('usuarios:login'), {'username': 'nuevo', 'password': 'Temporal#1'})
        self.url = reverse('usuarios:cambiar_clave')

    def test_login_redirige_al_cambio_obligatorio(self):
        self.client.logout()
        respuesta = self.client.post(reverse('usuarios:login'), {'username': 'nuevo', 'password': 'Temporal#1'})
        self.assertRedirects(respuesta, self.url)

    def test_no_puede_usar_otras_pantallas(self):
        for nombre in ('cotizaciones:simulador', 'cotizaciones:comparador', 'cotizaciones:historial'):
            with self.subTest(pantalla=nombre):
                self.assertRedirects(self.client.get(reverse(nombre)), self.url)

    def test_claves_que_no_cumplen_las_reglas_son_rechazadas(self):
        invalidas = {'Ab1!': 'al menos 8', 'abcdef1!': 'mayúscula', 'ABCDEF1!': 'minúscula',
                     'Abcdefg!': 'número', 'Abcdefg1': 'especial'}
        for clave, texto in invalidas.items():
            with self.subTest(clave=clave):
                respuesta = self.client.post(self.url, {'nueva_clave': clave, 'confirmar_clave': clave})
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, texto)
                self.usuario.refresh_from_db()
                self.assertTrue(self.usuario.primer_ingreso)

    def test_confirmacion_distinta_es_rechazada(self):
        respuesta = self.client.post(self.url, {'nueva_clave': 'Abcdef1!', 'confirmar_clave': 'Abcdef1?'})
        self.assertContains(respuesta, 'no coinciden')
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.primer_ingreso)

    def test_no_puede_repetir_la_clave_temporal(self):
        respuesta = self.client.post(self.url, {'nueva_clave': 'Temporal#1', 'confirmar_clave': 'Temporal#1'})
        self.assertContains(respuesta, 'distinta')

    def test_cambio_exitoso(self):
        respuesta = self.client.post(self.url, {'nueva_clave': 'Nueva#Clave1', 'confirmar_clave': 'Nueva#Clave1'})
        self.assertRedirects(respuesta, reverse('cotizaciones:simulador'))
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.primer_ingreso)
        self.assertTrue(self.usuario.check_password('Nueva#Clave1'))
        self.assertEqual(self.client.get(reverse('cotizaciones:simulador')).status_code, 200)
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.CAMBIAR_CLAVE).exists())


class RolesTests(TestCase):
    def setUp(self):
        self.admin = crear('admin1', rol=Rol.ADMINISTRADOR)
        self.analista = crear('analista1')

    def test_analista_recibe_403_en_modulos_de_administrador(self):
        self.client.force_login(self.analista)
        for nombre in ('usuarios:lista', 'usuarios:crear', 'tarifas:lista', 'tarifas:crear', 'auditoria:lista'):
            with self.subTest(modulo=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.ACCESO_DENEGADO).exists())

    def test_analista_accede_a_simulador_y_comparador(self):
        self.client.force_login(self.analista)
        for nombre in ('cotizaciones:simulador', 'cotizaciones:comparador', 'cotizaciones:historial'):
            with self.subTest(modulo=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_analista_no_puede_ejecutar_acciones_sobre_usuarios(self):
        self.client.force_login(self.analista)
        respuesta = self.client.post(reverse('usuarios:accion', args=[self.admin.pk, 'eliminar']))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_anonimo_es_enviado_al_login(self):
        respuesta = self.client.get(reverse('tarifas:lista'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta['Location'])

    def test_administrador_accede_a_todo(self):
        self.client.force_login(self.admin)
        for nombre in ('usuarios:lista', 'tarifas:lista', 'auditoria:lista', 'cotizaciones:simulador'):
            with self.subTest(modulo=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)


class GestionUsuariosTests(TestCase):
    def setUp(self):
        self.admin = crear('admin1', rol=Rol.ADMINISTRADOR)
        self.client.force_login(self.admin)

    def test_crear_usuario_genera_clave_temporal_y_primer_ingreso(self):
        respuesta = self.client.post(reverse('usuarios:crear'), {
            'first_name': 'María', 'last_name': 'Pérez', 'username': 'MPerez@cintac.cl', 'rol': Rol.ANALISTA},
            follow=True)
        usuario = Usuario.objects.get(username='mperez@cintac.cl')
        self.assertTrue(usuario.primer_ingreso)
        self.assertTrue(usuario.has_usable_password())
        self.assertContains(respuesta, 'Contraseña temporal')
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.CREAR_USUARIO).exists())

    def test_usuario_duplicado_y_correo_invalido(self):
        crear('repetido')
        for username, texto in (('REPETIDO', 'Ya existe'), ('correo@malo', 'formato')):
            with self.subTest(username=username):
                respuesta = self.client.post(reverse('usuarios:crear'), {
                    'first_name': 'A', 'last_name': 'B', 'username': username, 'rol': Rol.ANALISTA})
                self.assertContains(respuesta, texto)

    def test_desbloquear(self):
        bloqueado = crear('bloqueado')
        bloqueado.bloqueado, bloqueado.intentos_fallidos = True, 3
        bloqueado.save()
        self.client.post(reverse('usuarios:accion', args=[bloqueado.pk, 'desbloquear']))
        bloqueado.refresh_from_db()
        self.assertFalse(bloqueado.bloqueado)
        self.assertEqual(bloqueado.intentos_fallidos, 0)
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.DESBLOQUEAR_USUARIO).exists())

    def test_desactivar_y_activar(self):
        otro = crear('otro')
        self.client.post(reverse('usuarios:accion', args=[otro.pk, 'desactivar']))
        otro.refresh_from_db()
        self.assertFalse(otro.is_active)
        self.client.post(reverse('usuarios:accion', args=[otro.pk, 'activar']))
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)

    def test_restablecer_clave_vuelve_a_exigir_cambio(self):
        otro = crear('otro')
        self.client.post(reverse('usuarios:accion', args=[otro.pk, 'restablecer']))
        otro.refresh_from_db()
        self.assertTrue(otro.primer_ingreso)
        self.assertFalse(otro.check_password(CLAVE))

    def test_eliminar_usuario(self):
        otro = crear('otro')
        self.client.post(reverse('usuarios:accion', args=[otro.pk, 'eliminar']))
        self.assertFalse(Usuario.objects.filter(pk=otro.pk).exists())
        self.assertTrue(AuditLog.objects.filter(accion=AuditLog.Accion.ELIMINAR_USUARIO).exists())

    def test_no_puede_eliminarse_ni_desactivarse_a_si_mismo(self):
        for accion in ('eliminar', 'desactivar'):
            self.client.post(reverse('usuarios:accion', args=[self.admin.pk, accion]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertTrue(Usuario.objects.filter(pk=self.admin.pk).exists())

    def test_accion_inexistente_responde_404(self):
        otro = crear('otro')
        self.assertEqual(self.client.post(reverse('usuarios:accion', args=[otro.pk, 'volar'])).status_code, 404)

    def test_acciones_solo_por_post(self):
        otro = crear('otro')
        self.assertEqual(self.client.get(reverse('usuarios:accion', args=[otro.pk, 'eliminar'])).status_code, 405)
