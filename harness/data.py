"""Lectura de los datos sintéticos (roadmap §5).

PROPÓSITO: cargar un archivo de `datos/sinteticos/` por su nombre.

POR QUÉ EXISTE: lo leen el bucle de app1, los servidores MCP de app2 y app3 y
sus tests; una sola función evita rutas escritas a mano en cada uno.

QUÉ NO HACE: no escribe nunca: los datos solo cambian con
`datos/generar_sinteticos.py`. Tampoco lee `tickets_etiquetas.json` para el
agente: las etiquetas son para puntuar, no para el contexto del modelo.
"""

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "datos" / "sinteticos"


def load(name: str) -> Any:
    """Contenido JSON de `datos/sinteticos/<name>`."""
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
