"""Pruebas unitarias de la política de contraseñas y de la clave temporal (sin Django)."""
import unittest

from apps.usuarios.reglas_clave import es_valida, mensajes_incumplidos
from apps.usuarios.seguridad import generar_clave_temporal


class ReglasClaveTests(unittest.TestCase):
    def test_clave_valida(self):
        for clave in ['Abcdef1!', 'Cintac#2026', 'Nueva#Clave1', 'aB3$aB3$aB3$']:
            with self.subTest(clave=clave):
                self.assertEqual(mensajes_incumplidos(clave), [])
                self.assertTrue(es_valida(clave))

    def test_cada_regla_por_separado(self):
        casos = {'Ab1!': 'al menos 8', 'abcdef1!': 'mayúscula', 'ABCDEF1!': 'minúscula',
                 'Abcdefg!': 'número', 'Abcdefg1': 'especial'}
        for clave, palabra in casos.items():
            with self.subTest(clave=clave):
                mensajes = mensajes_incumplidos(clave)
                self.assertEqual(len(mensajes), 1)
                self.assertIn(palabra, mensajes[0])
                self.assertFalse(es_valida(clave))

    def test_clave_vacia_incumple_las_5_reglas(self):
        self.assertEqual(len(mensajes_incumplidos('')), 5)

    def test_simbolo_fuera_de_la_lista_no_cuenta(self):
        self.assertFalse(es_valida('Abcdef1.'))              # el punto no está entre !@#$%^&*

    def test_regex_completa_equivale_a_las_reglas_separadas(self):
        for clave in ['', 'abc', 'Abcdef1!', 'ABCDEFG1!', 'abcdefg1!', 'Abcdefgh!', 'Abcdefg1', 'Aa1!', 'Aa1!Aa1!']:
            with self.subTest(clave=clave):
                self.assertEqual(es_valida(clave), mensajes_incumplidos(clave) == [])


class ClaveTemporalTests(unittest.TestCase):
    def test_cumple_siempre_las_reglas_y_es_aleatoria(self):
        claves = [generar_clave_temporal() for _ in range(500)]
        self.assertTrue(all(es_valida(c) for c in claves))
        self.assertTrue(all(len(c) == 12 for c in claves))
        self.assertGreater(len(set(claves)), 495)


if __name__ == '__main__':
    unittest.main()
