"""Utilidades de fechas del ERP antiguo."""

from datetime import date


def parse_fecha(texto):
    # El ERP exporta dd/mm/aaaa; algunos registros vienen con guiones.
    dia, mes, anio = texto.replace("-", "/").split("/")
    return date(int(anio), int(mes), int(dia))


def anios_entre(desde, hasta):
    return (hasta - desde).days / 365.25
