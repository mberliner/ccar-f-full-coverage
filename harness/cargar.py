"""Carga de módulos de app por ruta, con un único objeto por archivo.

PROPÓSITO: importar `appN_*/NN_concepto.py` (su nombre empieza por un dígito y no admite `import`) y
cargar el módulo hermano de otro (`load_sibling`), con el nombre `_app_<carpeta>_<stem>` y caché en
`sys.modules`.

POR QUÉ EXISTE: la misma lógica estaba copiada en `tests/cargar.py` y en cuatro módulos de app. Con un
solo nombre por archivo, las dataclass de un módulo son las mismas para sus hermanos y para los tests.

QUÉ NO HACE: no ejecuta `main()` (el bloque `__main__` no corre al cargar) ni busca fuera de la ruta
dada. Un archivo inexistente da `FileNotFoundError` y no deja nada registrado.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_path(path: str | Path) -> ModuleType:
    """Carga el módulo en `path`; si ya se cargó, devuelve el mismo objeto."""
    path = Path(path).resolve()
    name = "_app_" + path.parent.name + "_" + path.stem
    if name in sys.modules:
        return sys.modules[name]
    # Se comprueba antes de registrar nada: un fallo no debe dejar un módulo a medias.
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Se registra antes de ejecutar: los dataclass lo necesitan para resolver tipos.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]  # un módulo que falla al cargar no queda en caché
        raise
    return module


def load_sibling(anchor: str | Path, filename: str) -> ModuleType:
    """Carga `filename` de la carpeta del archivo `anchor` (normalmente `__file__`)."""
    return load_path(Path(anchor).resolve().parent / filename)
