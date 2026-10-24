"""Modelos del inventario."""

from dataclasses import dataclass


@dataclass
class Equipo:
    serial: str
    tipo: str  # portatil | monitor | movil | periferico
    precio_compra: float
    fecha_compra: str  # dd/mm/aaaa, como lo exporta el ERP antiguo


@dataclass
class Asignacion:
    serial: str
    user_id: str
    fecha: str
