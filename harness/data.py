"""Lectura de los datos sintéticos (roadmap §5).

PROPÓSITO: cargar un archivo de `datos/sinteticos/` por su nombre.

POR QUÉ EXISTE: lo leen el bucle de app1, los servidores MCP de app2 y app3 y
sus tests; una sola función evita rutas escritas a mano en cada uno.

QUÉ NO HACE: no escribe nunca en `datos/sinteticos/`: los datos solo cambian
con `datos/generar_sinteticos.py` (`copy_to_temp` escribe en una copia). Tampoco lee `tickets_etiquetas.json` para el
agente: las etiquetas son para puntuar, no para el contexto del modelo.
"""

import atexit
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "datos" / "sinteticos"


def load(name: str) -> Any:
    """Contenido JSON de `datos/sinteticos/<name>`."""
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def copy_to_temp(name: str) -> Path:
    """Copia un conjunto de `datos/sinteticos/` a un directorio temporal nuevo.

    Sirve de `cwd` para los módulos cuyas tools escriben (`Edit`/`Write` en
    app1/02) o que generan archivos propios (el `.mcp.json` de app1/06): así
    `datos/sinteticos/` no se toca nunca. Un directorio se copia por dentro
    (su contenido queda en la raíz del temporal); un archivo suelto, dentro
    del temporal. Cada llamada devuelve un directorio distinto, que se borra al
    salir del proceso.
    """
    source = DATA_DIR / name
    # `resolve()`: en Windows `mkdtemp` devuelve una ruta corta (`FMARTI~1`); la CLI no la
    # reconoce como el directorio de trabajo y deniega `Edit`/`Write` en `dontAsk`.
    target = Path(tempfile.mkdtemp(prefix="ccarf-")).resolve()
    # ignore_errors: en Windows el directorio puede seguir en uso al salir.
    atexit.register(shutil.rmtree, target, ignore_errors=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    else:
        shutil.copy2(source, target / source.name)
    return target
