"""
Reglas de negocio COMEX del cotizador de CINTAC.

Módulo de Python puro (sin Django): se prueba de forma aislada y no depende de la base de datos.
Todos los montos usan Decimal y se redondean a centavos línea por línea, como en una cotización formal.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

MAX_TON_POR_CONTENEDOR = Decimal('25')     # Decreto 75
ARANCEL_SIN_TLC = Decimal('0.06')          # 6 % sobre CIF; con TLC es 0 %
IVA_IMPORTACION = Decimal('0.19')          # 19 % sobre (CIF + arancel)
COBRO_CONTENEDOR = 'CONTENEDOR'
COBRO_TONELADA = 'TONELADA'
_CENTAVOS = Decimal('0.01')


def _a_centavos(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def porcentaje_contingencia(dias_transito: int) -> Decimal:
    """Recargo logístico progresivo según los días de tránsito."""
    if dias_transito <= 30:
        return Decimal('0.03')
    if dias_transito <= 40:
        return Decimal('0.05')
    return Decimal('0.08')


def contenedores_sugeridos(toneladas: Decimal) -> int:
    """Mínimo de contenedores para no superar 25 t por contenedor."""
    if toneladas <= 0:
        return 0
    return int((toneladas / MAX_TON_POR_CONTENEDOR).to_integral_value(rounding=ROUND_CEILING))


def excede_decreto_75(toneladas: Decimal, contenedores: int) -> bool:
    """True si la carga repartida supera las 25 t por contenedor."""
    if contenedores <= 0:
        return toneladas > 0
    return toneladas / Decimal(contenedores) > MAX_TON_POR_CONTENEDOR


@dataclass(frozen=True)
class ResultadoCotizacion:
    contenedores: int
    toneladas_por_contenedor: Decimal
    flete_base: Decimal
    porcentaje_contingencia: Decimal
    recargo: Decimal
    flete_total: Decimal
    seguro: Decimal
    cif: Decimal
    porcentaje_arancel: Decimal
    arancel: Decimal
    base_iva: Decimal
    iva: Decimal
    total_usd: Decimal
    total_clp: int
    excede_peso: bool

    @property
    def porcentaje_contingencia_visible(self) -> Decimal:
        """Porcentaje listo para mostrar (5 en lugar de 0.0500)."""
        return (self.porcentaje_contingencia * 100).normalize()


def calcular_cotizacion(*, monto_tarifa, tipo_cobro, toneladas, fob, dias_transito, acogido_tlc,
                        tipo_cambio, contenedores=None) -> ResultadoCotizacion:
    """Calcula el costo de importación. Lanza ValueError si algún dato es inválido (validación en servidor)."""
    monto_tarifa, toneladas, fob, tipo_cambio = (Decimal(monto_tarifa), Decimal(toneladas),
                                                 Decimal(fob), Decimal(tipo_cambio))
    if tipo_cobro not in (COBRO_CONTENEDOR, COBRO_TONELADA):
        raise ValueError('Tipo de cobro inválido.')
    if monto_tarifa <= 0:
        raise ValueError('La tarifa debe ser mayor a cero.')
    if toneladas <= 0:
        raise ValueError('Las toneladas deben ser mayores a cero.')
    if fob < 0:
        raise ValueError('El valor FOB no puede ser negativo.')
    if int(dias_transito) < 1:
        raise ValueError('Los días de tránsito deben ser al menos 1.')
    if tipo_cambio <= 0:
        raise ValueError('El tipo de cambio debe ser mayor a cero.')

    n_contenedores = int(contenedores) if contenedores else contenedores_sugeridos(toneladas)
    cantidad = Decimal(n_contenedores) if tipo_cobro == COBRO_CONTENEDOR else toneladas

    flete_base = _a_centavos(monto_tarifa * cantidad)
    pct_contingencia = porcentaje_contingencia(int(dias_transito))
    recargo = _a_centavos(flete_base * pct_contingencia)
    flete_total = flete_base + recargo
    seguro = Decimal('0.00')                                   # exento por póliza global CINTAC
    cif = _a_centavos(fob) + flete_total + seguro
    pct_arancel = Decimal('0') if acogido_tlc else ARANCEL_SIN_TLC
    arancel = _a_centavos(cif * pct_arancel)
    base_iva = cif + arancel
    iva = _a_centavos(base_iva * IVA_IMPORTACION)
    total_usd = cif + arancel + iva
    total_clp = int((total_usd * tipo_cambio).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    return ResultadoCotizacion(
        contenedores=n_contenedores,
        toneladas_por_contenedor=(toneladas / Decimal(n_contenedores)) if n_contenedores else Decimal('0'),
        flete_base=flete_base, porcentaje_contingencia=pct_contingencia, recargo=recargo,
        flete_total=flete_total, seguro=seguro, cif=cif, porcentaje_arancel=pct_arancel, arancel=arancel,
        base_iva=base_iva, iva=iva, total_usd=total_usd, total_clp=total_clp,
        excede_peso=excede_decreto_75(toneladas, n_contenedores))


# ------------------------------------------------------------------ Comparador de embarcadores
@dataclass(frozen=True)
class OpcionTarifa:
    id: int
    embarcador: str
    tipo_cobro: str
    monto: Decimal
    dias_transito: int


@dataclass(frozen=True)
class OpcionComparada:
    opcion: OpcionTarifa
    resultado: ResultadoCotizacion
    es_mas_conveniente: bool
    es_mas_rapida: bool


def comparar(opciones, *, toneladas, fob, acogido_tlc, tipo_cambio):
    """Cotiza la misma carga con cada opción y las ordena de la más barata a la más cara."""
    opciones = list(opciones)
    calculadas = [
        (op, calcular_cotizacion(monto_tarifa=op.monto, tipo_cobro=op.tipo_cobro, toneladas=toneladas, fob=fob,
                                 dias_transito=op.dias_transito, acogido_tlc=acogido_tlc, tipo_cambio=tipo_cambio))
        for op in opciones
    ]
    calculadas.sort(key=lambda par: (par[1].total_usd, par[0].dias_transito))
    if not calculadas:
        return []
    min_dias = min(op.dias_transito for op, _ in calculadas)
    return [OpcionComparada(opcion=op, resultado=res, es_mas_conveniente=(i == 0),
                            es_mas_rapida=(op.dias_transito == min_dias))
            for i, (op, res) in enumerate(calculadas)]


def ahorro_maximo(comparadas) -> Decimal:
    """Diferencia en USD entre la opción más cara y la más barata."""
    if len(comparadas) < 2:
        return Decimal('0.00')
    return comparadas[-1].resultado.total_usd - comparadas[0].resultado.total_usd
