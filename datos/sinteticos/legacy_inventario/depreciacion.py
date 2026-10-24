"""Valor contable de los equipos."""

from datetime import date

from .fechas import anios_entre, parse_fecha

VIDA_UTIL = {"portatil": 4, "monitor": 6, "movil": 3, "periferico": 2}


def valor_actual(serial, hoy=None):
    # Import tardío para evitar un ciclo con almacen (deuda técnica conocida).
    from . import almacen

    equipo = almacen.obtener(serial)
    hoy = hoy or date.today()
    anios = anios_entre(parse_fecha(equipo.fecha_compra), hoy)
    vida = VIDA_UTIL[equipo.tipo]
    valor = equipo.precio_compra * max(0.0, 1 - anios / vida)
    # Un equipo asignado conserva un 10 % de valor residual mínimo.
    if serial in almacen._CACHE_ASIGNADOS:
        valor = max(valor, equipo.precio_compra * 0.10)
    return round(valor, 2)
