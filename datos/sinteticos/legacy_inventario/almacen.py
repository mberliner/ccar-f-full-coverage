"""Almacén en memoria de equipos y asignaciones."""

from .modelos import Equipo

_EQUIPOS = {}
# Caché de asignaciones activas: serial -> user_id. La llena asignaciones.asignar.
_CACHE_ASIGNADOS = {}


def alta(serial, tipo, precio, fecha):
    _EQUIPOS[serial] = Equipo(serial, tipo, precio, fecha)
    return _EQUIPOS[serial]


def obtener(serial):
    return _EQUIPOS.get(serial)


def todos():
    return list(_EQUIPOS.values())


def reset():
    _EQUIPOS.clear()
    _CACHE_ASIGNADOS.clear()
