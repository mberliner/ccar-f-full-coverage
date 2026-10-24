"""Informes para Finanzas."""

from . import almacen
from .depreciacion import valor_actual


def valor_total(hoy=None):
    return round(sum(valor_actual(e.serial, hoy) for e in almacen.todos()), 2)


def por_tipo():
    conteo = {}
    for equipo in almacen.todos():
        conteo[equipo.tipo] = conteo.get(equipo.tipo, 0) + 1
    return conteo
