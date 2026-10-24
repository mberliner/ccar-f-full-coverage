"""Hook `PreToolUse` de las sesiones que construyen el proyecto (roadmap §4.1).

PROPÓSITO: rechazar cualquier escritura en `datos/sinteticos/` o en un `.env`
(`.env`, `.env.local`…; no las plantillas `.env.example` y `.env.sample`), tanto
por `Edit`/`Write` como por un comando de shell (`Bash` o `PowerShell`).

POR QUÉ EXISTE: los datos de prueba solo se crean con `datos/generar_sinteticos.py`
y `.env` guarda la credencial. Una instrucción en `CLAUDE.md` se puede saltar; un
hook es una puerta programática que se cumple siempre (ver TS 1.4-K1 y TS 1.5-K1,
que introducen las apps). El *matcher* incluye la shell porque una redirección
(`echo > datos/sinteticos/x.json`) esquiva un hook que solo mire `Edit`, y en
Windows la tool `PowerShell` es otra vía distinta de `Bash`.

Falla en cerrado: una entrada que no se entiende bloquea (exit 2). Cualquier otro
código de error es no bloqueante para Claude Code y dejaría pasar la llamada.

QUÉ NO HACE: el filtro de shell es heurístico y estricto. Bloquea todo comando que
mencione una ruta protegida, también los de solo lectura, porque para leer está
`Read`. Solo deja pasar un `git` de lectura o `git add`, sin nada encadenado. No
detecta un script que escriba por dentro, ni variables o comodines que compongan
la ruta (`$d/sinteticos`, `datos/sint*`). Esa vía la cubre `--check` del
generador y su test.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROTECTED_DIR = "datos/sinteticos"
ENV_TEMPLATES = (".example", ".sample")  # plantillas versionables, sin secretos

# Nombre de archivo `.env` o `.env.<sufijo>`, precedido de inicio, separador o
# comilla (así no casa con `.venv`). IGNORECASE: en Windows `.ENV` es el mismo archivo.
ENV_IN_COMMAND = re.compile(r"(?:^|[\s/\\'\"=])\.env(\.[\w.-]+)?(?![\w.-])", re.IGNORECASE)
# Excepción: subcomandos de git que no tocan el árbol de trabajo. `add` solo
# prepara el índice y hace falta para commitear los datos regenerados.
SAFE_GIT = re.compile(r"\s*git\s+(status|diff|log|show|add)\b")
# Cualquier separador o redirección invalida la excepción, incluido el salto de
# línea, que en bash y en PowerShell separa comandos igual que «;».
SHELL_OPERATORS = re.compile(r"[;&|<>`\n\r]|\$\(")


def is_protected_env(name: str) -> bool:
    """¿Es un `.env` con secretos? (`.env`, `.env.local`…, pero no sus plantillas)."""
    name = name.lower()
    if name == ".env":
        return True
    return name.startswith(".env.") and not name.endswith(ENV_TEMPLATES)


def protected_path(file_path: str) -> bool:
    """¿Cae la ruta (absoluta o relativa al proyecto) en una zona protegida?"""
    path = Path(file_path)
    if not path.is_absolute():
        path = ROOT / path
    try:
        # normcase: en Windows ignora mayúsculas y unifica separadores.
        rel = Path(os.path.normcase(path.resolve())).relative_to(os.path.normcase(ROOT))
    except ValueError:
        return False  # fuera del proyecto: no es asunto de este hook
    rel_posix = rel.as_posix().lower()
    return rel_posix == PROTECTED_DIR or rel_posix.startswith(PROTECTED_DIR + "/") or is_protected_env(rel.name)


def protected_command(command: str) -> bool:
    """¿Nombra el comando una ruta protegida sin ser un `git` seguro y aislado?"""
    normalized = command.replace("\\", "/")
    mentions = PROTECTED_DIR in normalized.lower() or any(
        is_protected_env(".env" + (m.group(1) or "")) for m in ENV_IN_COMMAND.finditer(normalized)
    )
    if not mentions:
        return False
    is_safe_git = SAFE_GIT.match(normalized) is not None and not SHELL_OPERATORS.search(normalized)
    return not is_safe_git


def decide(hook_input: object) -> str | None:
    """Devuelve el motivo del bloqueo, o None si la llamada puede seguir.

    Lanza ValueError si la entrada no tiene la forma esperada.
    """
    if not isinstance(hook_input, dict) or not isinstance(hook_input.get("tool_input"), dict):
        raise ValueError("falta tool_input")
    tool_name = hook_input.get("tool_name")
    tool_input = hook_input["tool_input"]

    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path")
        if not isinstance(file_path, str):
            raise ValueError(f"{tool_name} sin file_path")
        if protected_path(file_path):
            return f"{file_path} está protegido: los datos se cambian con datos/generar_sinteticos.py y .env no se edita."
    elif tool_name in ("Bash", "PowerShell"):
        command = tool_input.get("command")
        if not isinstance(command, str):
            raise ValueError(f"{tool_name} sin command")
        if protected_command(command):
            return "El comando nombra datos/sinteticos/ o un .env: usa Read para leer y datos/generar_sinteticos.py para regenerar."
    elif not isinstance(tool_name, str):
        raise ValueError("falta tool_name")
    return None


def main() -> int:
    # Claude Code envía y lee UTF-8; en Windows Python usaría cp1252 por defecto
    # y las rutas o los motivos con tildes llegarían corruptos.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        reason = decide(json.load(sys.stdin))
    except Exception as exc:  # noqa: BLE001
        # Falla en cerrado: con exit 1 la llamada seguiría adelante.
        reason = f"proteger_rutas.py no pudo evaluar la llamada ({type(exc).__name__}: {exc}); se bloquea por seguridad."
    if reason is None:
        return 0
    # Exit 2 bloquea la llamada y entrega stderr a Claude como motivo.
    print(reason, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
