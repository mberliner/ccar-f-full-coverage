"""Hook `PreToolUse` de las sesiones que construyen el proyecto (roadmap §4.1).

PROPÓSITO: rechazar cualquier escritura en `datos/sinteticos/` o en `.env`, tanto
por `Edit`/`Write` como por un comando de shell (`Bash` o `PowerShell`).

POR QUÉ EXISTE: los datos de prueba solo se crean con `datos/generar_sinteticos.py`
y `.env` guarda la credencial. Una instrucción en `CLAUDE.md` se puede saltar; un
hook es una puerta programática que se cumple siempre (ver TS 1.4-K1 y TS 1.5-K1,
que introducen las apps). El *matcher* incluye la shell porque una redirección
(`echo > datos/sinteticos/x.json`) esquiva un hook que solo mire `Edit`, y en
Windows la tool `PowerShell` es otra vía distinta de `Bash`.

QUÉ NO HACE: el filtro de shell es heurístico y estricto. Bloquea todo comando que
mencione una ruta protegida, también los de solo lectura, porque para leer está
`Read`. Solo deja pasar `git` sin encadenar otros comandos. No detecta un script
que escriba por dentro sin nombrar la ruta en el comando. Para eso está
`--check` del generador y su test.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROTECTED_DIR = "datos/sinteticos"
PROTECTED_FILE = ".env"

# `.env` como nombre de archivo: precedido de inicio, separador o comilla
# (así no casa con `.venv`).
ENV_IN_COMMAND = re.compile(r"(^|[\s/\\'\"=])\.env\b")
# Cualquier operador que encadene o redirija invalida la excepción de `git`.
SHELL_OPERATORS = re.compile(r"[;&|<>`]|\$\(")


def protected_path(file_path: str) -> bool:
    """¿Cae la ruta (absoluta o relativa al proyecto) en una zona protegida?"""
    path = Path(file_path)
    if not path.is_absolute():
        path = ROOT / path
    try:
        # normcase: en Windows `C:\` y `c:\` son la misma ruta.
        rel = Path(os.path.normcase(path.resolve())).relative_to(os.path.normcase(ROOT))
    except ValueError:
        return False  # fuera del proyecto: no es asunto de este hook
    rel_posix = rel.as_posix()
    return rel_posix == PROTECTED_DIR or rel_posix.startswith(PROTECTED_DIR + "/") or rel.name == PROTECTED_FILE


def protected_command(command: str) -> bool:
    """¿Nombra el comando una ruta protegida sin ser un `git` aislado?"""
    normalized = command.replace("\\", "/")
    mentions = PROTECTED_DIR in normalized.lower() or ENV_IN_COMMAND.search(normalized) is not None
    if not mentions:
        return False
    is_plain_git = normalized.lstrip().startswith("git ") and not SHELL_OPERATORS.search(normalized)
    return not is_plain_git


def main() -> int:
    # Claude Code envía y lee UTF-8; en Windows Python usaría cp1252 por defecto
    # y las rutas o los motivos con tildes llegarían corruptos.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    hook_input = json.load(sys.stdin)
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name in ("Edit", "Write") and protected_path(tool_input.get("file_path", "")):
        reason = f"{tool_input['file_path']} está protegido: los datos se cambian con datos/generar_sinteticos.py y .env no se edita."
    elif tool_name in ("Bash", "PowerShell") and protected_command(tool_input.get("command", "")):
        reason = "El comando nombra datos/sinteticos/ o .env: usa Read para leer y datos/generar_sinteticos.py para regenerar."
    else:
        return 0

    # Exit 2 bloquea la llamada y entrega stderr a Claude como motivo.
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
