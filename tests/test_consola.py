"""
PROPÓSITO: comprobar que los módulos pueden imprimir ✓, ✗ y similares por una
tubería en Windows sin que la persona haya activado UTF-8 a mano.
POR QUÉ EXISTE: con la salida redirigida (Claude Code con `!`, `| tee`, un
archivo) Python usa cp1252 y `print("✓")` lanza UnicodeEncodeError a mitad de
un módulo; se descubrió en la prueba del narrador con `app1/05`. Arreglarlo
exige que nadie conozca `PYTHONUTF8` ni `PYTHONIOENCODING`.
QUÉ NO HACE: no ejecuta módulos ni usa el modelo; solo importa el arnés en un
intérprete aparte y escribe un carácter fuera de cp1252.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(code: str) -> subprocess.CompletedProcess:
    # Se fuerza el caso malo: sin UTF-8 activado y con la salida en una tubería.
    # PYTHONUTF8=0 desactiva el modo UTF-8 también en Python que lo trae por defecto.
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["PYTHONUTF8"] = "0"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=False,
    )


def test_importar_el_arnes_deja_la_salida_en_utf8() -> None:
    result = _run("import harness, sys; print('\\u2713 \\u2717 \\u00b7')")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert result.stdout.decode("utf-8").strip() == "✓ ✗ ·"


def test_el_error_por_stderr_tambien_sale_en_utf8() -> None:
    result = _run("import harness, sys; print('\\u2713', file=sys.stderr)")
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert result.stderr.decode("utf-8").strip() == "✓"
