"""Tests del registro de contratos de la fase 3 (`tests/contrato.py`): cada paquete pendiente falla de forma esperada hasta que se implementa. Sin modelo.

PROPÓSITO: que un paquete con los tests escritos y el código por hacer se vea en la salida de pytest
(`xfailed`) y que, al implementarlo, la marca sobrante falle (`xfail(strict=True)`) hasta que se
quite el paquete de `PENDING`.

POR QUÉ EXISTE: los archivos de contrato se saltan mientras falta su módulo. Sin este test, un
paquete olvidado quedaría como un salto más entre los de la suite.

QUÉ NO HACE: no prueba el comportamiento de los paquetes; eso está en `tests/test_items.py`,
`tests/test_repaso.py`, `tests/test_mixto.py`, `tests/test_narrador_d3.py`, `tests/test_hojas_repaso.py`,
`tests/test_repaso_celdas.py`, `tests/test_item_ciego.py`, `tests/test_simulaciones_narrador.py`, `tests/test_narrador_contexto.py` y, de la fase 5,
`tests/test_fase5_helpers.py`, `tests/test_fase5_salida.py` y `tests/test_fase5_d3_lector.py`.
"""

import pytest

from tests.contrato import CONTRACTS, PENDING, missing


def packages() -> list:
    params = []
    for package in sorted(CONTRACTS):
        marks = [pytest.mark.xfail(strict=True, reason=f"paquete {package} sin implementar")] if package in PENDING else []
        params.append(pytest.param(package, marks=marks, id=package))
    return params


@pytest.mark.parametrize("package", packages())
def test_package_brings_its_modules_and_names(package):
    assert missing(package) == []


def test_pending_only_names_known_packages():
    assert PENDING <= set(CONTRACTS)
