"""Decide si un ticket hay que escalarlo."""

from ..core.sla import calcular_sla


def debe_escalar(prioridad, horas_abiertas):
    try:
        calcular_sla(prioridad, horas_abiertas)
    except ValueError:
        return True
    return False
