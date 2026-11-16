"""Configuración común de los tests: el marcador `needs_git`. Sin modelo.

PROPÓSITO: registrar el marcador `needs_git` y saltar los tests que lo llevan cuando `git` no está instalado.

POR QUÉ EXISTE: varios archivos construían un repositorio temporal con `git` y cada uno repetía su propio `skipif(shutil.which("git") is None)`; aquí vive una sola vez.

QUÉ NO HACE: no define fixtures ni llama al modelo; no cambia ningún test que no lleve el marcador.
"""

import shutil

import pytest


def pytest_configure(config):
    # Registra el marcador para que `--strict-markers` no lo rechace.
    config.addinivalue_line("markers", "needs_git: el test necesita `git` en el PATH (si no está, se salta)")


def pytest_collection_modifyitems(config, items):
    if shutil.which("git") is not None:
        return
    skip = pytest.mark.skip(reason="necesita git")
    # Mismo motivo que tenía cada `skipif` repetido: sin `git` no se puede crear el repositorio temporal.
    for item in items:
        if "needs_git" in item.keywords:
            item.add_marker(skip)
