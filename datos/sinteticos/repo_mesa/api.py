"""Interfaz pública del paquete: reexporta funciones con el nombre que usa el resto."""

from .core.sla import calcular_sla as sla_ticket

__all__ = ["sla_ticket"]
