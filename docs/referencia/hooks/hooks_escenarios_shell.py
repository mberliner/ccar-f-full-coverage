"""Hook de comando (shell) de prueba para el escenario S1 de `hooks-escenarios-codigo.md`.

PROPÓSITO: mostrar cómo el código de salida y el JSON de un hook de comando deciden
la llamada. Lee el evento por stdin y se comporta según el modo (argumento):
  exit2      PreToolUse: bloquea un comando peligroso con `exit 2` y el motivo en stderr.
  json       PreToolUse: lo bloquea con `exit 0` y un JSON `permissionDecision: "deny"`.
  exit1      PreToolUse: la TRAMPA. Con `exit 1` el error es no bloqueante y la llamada pasa.
  post-exit2 PostToolUse: `exit 2` solo muestra el stderr a Claude; la herramienta ya corrió.

POR QUÉ EXISTE: para probar el comportamiento de los códigos de salida sin cargar nada en
el proyecto. `docs/referencia/hooks/hooks_escenarios.py` lo invoca como subproceso en su autocomprobación.

QUÉ NO HACE: no se registra en `.claude/settings.json` (el ejemplo está en
`hooks_escenarios_settings.json` y no se carga solo), no es una lista completa de comandos
peligrosos y solo mira la primera coincidencia de una expresión regular simple.
"""

import json
import re
import sys

# Heurística mínima y deliberadamente corta: `rm` recursivo y forzado, y `git push` forzado.
DANGEROUS = re.compile(r"\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r|\bgit\s+push\s+(--force|-f)\b")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "exit2"
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or "hook_event_name" not in event:
            raise ValueError("evento sin hook_event_name")
    except ValueError as exc:
        # Falla en cerrado: con `exit 1` la llamada pasaría, así que una entrada ilegible usa `exit 2`.
        print(f"Entrada del hook ilegible: {exc}", file=sys.stderr)
        return 2

    if mode == "post-exit2":
        if "FAILED" in json.dumps(event.get("tool_response", "")):
            print("Los tests fallaron: revisa antes de continuar.", file=sys.stderr)
            return 2  # PostToolUse: no bloquea nada (ya corrió), solo llega a Claude como stderr
        return 0

    command = str(event.get("tool_input", {}).get("command", ""))
    match = DANGEROUS.search(command)
    if not match:
        return 0
    message = f"Comando bloqueado por política: «{match.group(0)}» es destructivo."
    if mode == "json":
        # Con exit 0 el JSON decide: aquí sí rige permissionDecision, dentro de hookSpecificOutput.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": message}}))
        return 0
    print(message, file=sys.stderr)
    return 1 if mode == "exit1" else 2  # exit1: error no bloqueante, la llamada se ejecuta


if __name__ == "__main__":
    sys.exit(main())
