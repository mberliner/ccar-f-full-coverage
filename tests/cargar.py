"""Carga de módulos de app desde los tests. Sin modelo.

PROPÓSITO: importar `appN_*/NN_concepto.py`, cuyo nombre empieza por un dígito
y no admite `import` normal.

POR QUÉ EXISTE: los módulos se numeran por orden de lectura (roadmap §5); el
número no es un identificador de Python válido.

QUÉ NO HACE: no ejecuta `main()`: el bloque `if __name__ == "__main__"` no
corre al cargar, así que importar un módulo nunca llama al modelo.
"""

from pathlib import Path
from types import ModuleType

from harness.cargar import load_path

ROOT = Path(__file__).resolve().parent.parent


def load(relative_path: str) -> ModuleType:
    """Carga un módulo por su ruta relativa al repositorio (p. ej. `app1_agente_unico/01_bucle_manual.py`)."""
    # Delega en el helper del arnés: un único nombre y una única caché por archivo.
    return load_path(ROOT / relative_path)
