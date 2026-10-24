"""Tests de los hooks de comando de `.claude/hooks/`, ejecutados como los lanza Claude Code. Sin modelo.

`harness/offline.run_hook` sirve para los callbacks del SDK; estos hooks son
scripts que leen el JSON por stdin y deciden con el código de salida.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def run_raw(script: str, stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / script)], input=stdin, capture_output=True, text=True, encoding="utf-8"
    )


def run(script: str, tool_name: str, tool_input: dict, event: str = "PreToolUse") -> subprocess.CompletedProcess:
    payload = {"hook_event_name": event, "tool_name": tool_name, "tool_input": tool_input, "cwd": str(ROOT)}
    return run_raw(script, json.dumps(payload))


@pytest.mark.parametrize(
    ("tool_name", "tool_input", "code"),
    [
        ("Edit", {"file_path": str(ROOT / "datos" / "sinteticos" / "tickets.json")}, 2),
        ("Write", {"file_path": "datos/sinteticos/nuevo.json"}, 2),
        ("Write", {"file_path": str(ROOT / ".env")}, 2),
        ("Edit", {"file_path": str(ROOT / "harness" / "options.py")}, 0),
        ("Edit", {"file_path": str(ROOT / "datos" / "generar_sinteticos.py")}, 0),
        # Variantes de .env: las locales se protegen; las plantillas sin secretos, no.
        ("Write", {"file_path": ".env.local"}, 2),
        ("Write", {"file_path": "app1_agente_unico/.env"}, 2),
        ("Write", {"file_path": ".env.example"}, 0),
        ("Write", {"file_path": ".env.sample"}, 0),
        # En Windows la ruta no distingue mayúsculas.
        ("Write", {"file_path": "DATOS/Sinteticos/x.json"}, 2),
        ("Write", {"file_path": ".ENV"}, 2),
    ],
)
def test_file_tools(tool_name, tool_input, code):
    result = run("proteger_rutas.py", tool_name, tool_input)
    assert result.returncode == code, result.stderr
    assert bool(result.stderr) == (code == 2)


@pytest.mark.parametrize(
    ("tool_name", "command", "code"),
    [
        ("Bash", "echo '[]' > datos/sinteticos/tickets.json", 2),
        ("Bash", "cat .env", 2),
        ("PowerShell", "Set-Content datos\\sinteticos\\x.json '{}'", 2),
        ("Bash", "git add datos/sinteticos && echo x > datos/sinteticos/a.json", 2),
        ("Bash", "git add datos/sinteticos", 0),
        ("Bash", "git status datos/sinteticos", 0),
        ("Bash", "git diff -- datos/sinteticos/tickets.json", 0),
        ("Bash", "uv run python datos/generar_sinteticos.py --check", 0),
        ("Bash", "ls .venv", 0),
        # Un salto de línea separa comandos igual que «;».
        ("Bash", "git status datos/sinteticos\necho x > datos/sinteticos/a.json", 2),
        ("PowerShell", "git status datos/sinteticos\r\nRemove-Item datos\\sinteticos\\a.json", 2),
        # Subcomandos de git que reescriben archivos.
        ("Bash", "git checkout -- datos/sinteticos", 2),
        ("Bash", "git restore datos/sinteticos/tickets.json", 2),
        ("Bash", "git clean -fd datos/sinteticos", 2),
        ("Bash", "git stash push datos/sinteticos", 2),
        ("Bash", "git -C . checkout -- datos/sinteticos", 2),
        # Variantes de .env y mayúsculas, con el mismo criterio que las rutas.
        ("Bash", "cat .env.local", 2),
        ("Bash", "cp .env.example .env.sample", 0),
        ("PowerShell", "Get-Content .ENV", 2),
        ("Bash", "echo x > DATOS/SINTETICOS/a.json", 2),
    ],
)
def test_shell_tools(tool_name, command, code):
    assert run("proteger_rutas.py", tool_name, {"command": command}).returncode == code


@pytest.mark.parametrize(
    "stdin",
    ["", "no es json", "[]", json.dumps({"tool_name": "Edit"}), json.dumps({"tool_name": "Bash", "tool_input": "x"})],
)
def test_fails_closed_on_bad_input(stdin):
    # Exit 1 es un error no bloqueante para Claude Code: la barrera tiene que cerrarse con 2.
    result = run_raw("proteger_rutas.py", stdin)
    assert result.returncode == 2 and result.stderr


def test_post_tool_use_skips_non_python_files():
    # Si ejecutara pytest aquí habría recursión; con un .md debe salir sin hacer nada.
    result = run("ejecutar_tests.py", "Edit", {"file_path": "NOTAS.md"}, event="PostToolUse")
    assert result.returncode == 0 and result.stderr == ""
