"""Pruebas unitarias de las reglas de negocio (no requieren base de datos ni Django)."""
import unittest
from decimal import Decimal as D

from apps.cotizaciones.services import (
    OpcionTarifa, ahorro_maximo, calcular_cotizacion, comparar, contenedores_sugeridos,
    excede_decreto_75, porcentaje_contingencia)


def cotizar(**kw):
    datos = dict(monto_tarifa=D('2850'), tipo_cobro='CONTENEDOR', toneladas=D('60'), fob=D('85000'),
                 dias_transito=32, acogido_tlc=False, tipo_cambio=D('950'))
    datos.update(kw)
    return calcular_cotizacion(**datos)


class ContingenciaTests(unittest.TestCase):
    def test_limites_de_dias(self):
        esperado = {1: '0.03', 30: '0.03', 31: '0.05', 40: '0.05', 41: '0.08', 365: '0.08'}
        for dias, pct in esperado.items():
            with self.subTest(dias=dias):
                self.assertEqual(porcentaje_contingencia(dias), D(pct))


class Decreto75Tests(unittest.TestCase):
    def test_contenedores_sugeridos(self):
        casos = {'0.1': 1, '24.9': 1, '25': 1, '25.1': 2, '50': 2, '50.1': 3, '100000': 4000}
        for toneladas, esperado in casos.items():
            with self.subTest(toneladas=toneladas):
                self.assertEqual(contenedores_sugeridos(D(toneladas)), esperado)

    def test_exceso_de_peso(self):
        self.assertFalse(excede_decreto_75(D('25'), 1))
        self.assertTrue(excede_decreto_75(D('25.01'), 1))
        self.assertTrue(excede_decreto_75(D('60'), 2))       # 30 t por contenedor
        self.assertFalse(excede_decreto_75(D('60'), 3))


class CalculoTests(unittest.TestCase):
    def test_cotizacion_de_referencia_por_contenedor(self):
        r = cotizar()
        self.assertEqual(r.contenedores, 3)
        self.assertEqual(r.flete_base, D('8550.00'))
        self.assertEqual(r.recargo, D('427.50'))            # 32 días -> 5 %
        self.assertEqual(r.cif, D('93977.50'))
        self.assertEqual(r.arancel, D('5638.65'))           # 6 % sobre CIF
        self.assertEqual(r.base_iva, D('99616.15'))         # CIF + arancel
        self.assertEqual(r.iva, D('18927.07'))              # 19 % sobre CIF + arancel
        self.assertEqual(r.total_usd, D('118543.22'))
        self.assertEqual(r.total_clp, 112616059)
        self.assertFalse(r.excede_peso)

    def test_tlc_elimina_el_arancel(self):
        r = cotizar(acogido_tlc=True)
        self.assertEqual(r.arancel, D('0.00'))
        self.assertEqual(r.iva, D('17855.73'))
        self.assertEqual(r.total_usd, D('111833.23'))
        self.assertEqual(r.total_clp, 106241569)            # 106.241.568,5 redondea hacia arriba

    def test_tarifa_por_tonelada(self):
        r = cotizar(monto_tarifa=D('118'), tipo_cobro='TONELADA', dias_transito=42)
        self.assertEqual(r.flete_base, D('7080.00'))
        self.assertEqual(r.recargo, D('566.40'))            # 42 días -> 8 %
        self.assertEqual(r.total_usd, D('116864.16'))

    def test_mas_contenedores_que_los_sugeridos(self):
        r = cotizar(contenedores=4)
        self.assertEqual(r.flete_base, D('11400.00'))

    def test_exceso_se_informa(self):
        self.assertTrue(cotizar(contenedores=2).excede_peso)

    def test_seguro_exento(self):
        self.assertEqual(cotizar().seguro, D('0.00'))

    def test_validaciones_en_servidor(self):
        invalidos = [dict(tipo_cambio=D('0')), dict(tipo_cambio=D('-950')), dict(fob=D('-1')),
                     dict(dias_transito=0), dict(toneladas=D('0')), dict(monto_tarifa=D('0')),
                     dict(tipo_cobro='OTRO')]
        for cambio in invalidos:
            with self.subTest(cambio=cambio):
                with self.assertRaises(ValueError):
                    cotizar(**cambio)

    def test_fob_cero_es_valido(self):
        self.assertGreater(cotizar(fob=D('0')).total_usd, 0)


class ComparadorTests(unittest.TestCase):
    OPCIONES = [
        OpcionTarifa(1, 'Maersk', 'CONTENEDOR', D('2850'), 32),
        OpcionTarifa(2, 'MSC', 'CONTENEDOR', D('2700'), 38),
        OpcionTarifa(3, 'Hapag-Lloyd', 'CONTENEDOR', D('3050'), 28),
    ]

    def comparar(self, opciones=None):
        return comparar(self.OPCIONES if opciones is None else opciones, toneladas=D('60'), fob=D('85000'),
                        acogido_tlc=False, tipo_cambio=D('950'))

    def test_orden_y_etiquetas(self):
        comparadas = self.comparar()
        self.assertEqual([c.opcion.embarcador for c in comparadas], ['MSC', 'Maersk', 'Hapag-Lloyd'])
        self.assertTrue(comparadas[0].es_mas_conveniente)
        self.assertEqual([c.opcion.embarcador for c in comparadas if c.es_mas_rapida], ['Hapag-Lloyd'])

    def test_ahorro(self):
        # Diferencia de flete con margen (9.424,50 - 8.505,00 = 919,50) × 1,06 (arancel) × 1,19 (IVA)
        self.assertEqual(ahorro_maximo(self.comparar()), D('1159.85'))

    def test_mezcla_de_cobro_por_tonelada_y_contenedor(self):
        opciones = [OpcionTarifa(4, 'Maersk', 'CONTENEDOR', D('2600'), 35),
                    OpcionTarifa(5, 'MSC', 'TONELADA', D('118'), 42),
                    OpcionTarifa(6, 'Hapag-Lloyd', 'CONTENEDOR', D('2750'), 30)]
        self.assertEqual(self.comparar(opciones)[0].opcion.embarcador, 'MSC')

    def test_sin_opciones(self):
        self.assertEqual(self.comparar([]), [])
        self.assertEqual(ahorro_maximo([]), D('0.00'))


if __name__ == '__main__':
    unittest.main()
