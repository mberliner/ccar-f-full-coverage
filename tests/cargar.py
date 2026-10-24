"""Carga de módulos de app desde los tests. Sin modelo.

PROPÓSITO: importar `appN_*/NN_concepto.py`, cuyo nombre empieza por un dígito
y no admite `import` normal.

POR QUÉ EXISTE: los módulos se numeran por orden de lectura (roadmap §5); el
número no es un identificador de Python válido.

QUÉ NO HACE: no ejecuta `main()`: el bloque `if __name__ == "__main__"` no
corre al cargar, así que importar un módulo nunca llama al modelo.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def load(relative_path: str) -> ModuleType:
    """Carga un módulo por su ruta relativa al repositorio (p. ej. `app1_agente_unico/01_bucle_manual.py`)."""
    path = ROOT / relative_path
    name = "_app_" + path.parent.name + "_" + path.stem
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Se registra antes de ejecutar: los dataclass lo necesitan para resolver tipos.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
