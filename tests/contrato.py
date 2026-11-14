"""Contratos de la fase 3 del plan de mejoras: qué módulo y qué nombres debe aportar cada paquete.

PROPÓSITO: dejar escritos los tests de un paquete antes que su código sin romper la suite. Un archivo
de tests de contrato empieza con `require("3.x")`: mientras falte lo que ese paquete aporta, el archivo
entero se salta; en cuanto existe, sus tests corren y tienen que pasar.

POR QUÉ EXISTE: un `import` de un módulo que aún no existe es un error de recolección, y pytest
interrumpe entonces toda la suite. Quien implementa el paquete 3.1 vería en cada edición los errores
de 3.2 a 3.4, que no le tocan. El salto no puede quedarse para siempre sin que nadie lo vea:
`tests/test_contratos_fase3.py` lleva un `xfail(strict=True)` por paquete pendiente, que falla en
cuanto el paquete está hecho y obliga a quitarlo de `PENDING`.

QUÉ NO HACE: no comprueba el comportamiento, solo que el módulo y los nombres existen. El
comportamiento lo fijan los tests de cada archivo de contrato.
"""

import importlib

import pytest

# Paquete → [(módulo, nombres que debe tener)]. El detalle de cada firma está en `NOTAS.md`.
CONTRACTS: dict[str, list[tuple[str, list[str]]]] = {
    "3.1": [
        ("harness.items", ["Item", "UnknownItem", "all_items", "find_item", "item_for"]),
        ("harness.repaso", ["INTERVALS", "Failure", "parse_failures", "next_due", "is_due", "review_queue"]),
    ],
    "3.2": [("harness.items", ["mixed_selection"])],
    "3.3": [("harness.narrador", ["D3_PHASES", "d3_phase"])],
    "3.4": [("harness.hojas_repaso", ["build_sheets", "main"])],
}
# Paquetes sin implementar. Al cerrar un paquete se quita de aquí, en el mismo cambio.
PENDING: set[str] = set()


def missing(package: str) -> list[str]:
    """Lo que falta de un paquete, como «módulo» o «módulo.nombre»."""
    absent = []
    for module_name, names in CONTRACTS[package]:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            absent.append(module_name)
            continue
        absent += [f"{module_name}.{name}" for name in names if not hasattr(module, name)]
    return absent


def require(package: str) -> None:
    """Salta el archivo de tests que lo llama mientras falte algo del paquete."""
    absent = missing(package)
    if absent:
        pytest.skip(f"contrato pendiente (paquete {package}): falta {', '.join(absent)}", allow_module_level=True)
