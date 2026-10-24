"""Asignación de equipos a empleados."""

from . import almacen
from .modelos import Asignacion

_HISTORICO = []


def asignar(serial, user_id, fecha):
    if almacen.obtener(serial) is None:
        raise KeyError(f"equipo desconocido: {serial}")
    if serial in almacen._CACHE_ASIGNADOS:
        raise ValueError(f"{serial} ya está asignado a {almacen._CACHE_ASIGNADOS[serial]}")
    almacen._CACHE_ASIGNADOS[serial] = user_id
    _HISTORICO.append(Asignacion(serial, user_id, fecha))


def devolver(serial):
    almacen._CACHE_ASIGNADOS.pop(serial, None)


def de_empleado(user_id):
    return [s for s, u in almacen._CACHE_ASIGNADOS.items() if u == user_id]
