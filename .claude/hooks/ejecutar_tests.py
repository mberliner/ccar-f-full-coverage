"""Hook `PostToolUse` de las sesiones que construyen el proyecto (roadmap §4.1).

PROPÓSITO: ejecutar `uv run pytest -q` cada vez que se edita o se escribe un `.py`
y, si algo falla, devolver el final de la salida a Claude.

POR QUÉ EXISTE: con tests primero, el fallo tiene que verse en cuanto aparece y
no al final de la sesión. Como hook, se ejecuta siempre, sin depender de que
Claude se acuerde.

QUÉ NO HACE: no deshace la edición, porque en `PostToolUse` la tool ya se ejecutó.
El exit 2 solo hace llegar el fallo a Claude para que lo corrija. Tampoco se
ejecuta en ediciones que no sean `.py`.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TAIL_LINES = 40  # lo bastante para ver el test y su aserción sin inundar el contexto


def main() -> int:
    # Claude Code envía y lee UTF-8; en Windows Python usaría cp1252 por defecto
    # y las rutas o los motivos con tildes llegarían corruptos.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    hook_input = json.load(sys.stdin)
    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return 0

    result = subprocess.run(
        ["uv", "run", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode == 0:
        return 0
    tail = "\n".join((result.stdout + result.stderr).splitlines()[-TAIL_LINES:])
    print(f"pytest falla tras editar {file_path}:\n{tail}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
