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


def run(script: str, tool_name: str, tool_input: dict, event: str = "PreToolUse") -> subprocess.CompletedProcess:
    payload = {"hook_event_name": event, "tool_name": tool_name, "tool_input": tool_input, "cwd": str(ROOT)}
    return subprocess.run(
        [sys.executable, str(HOOKS / script)], input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("tool_name", "tool_input", "code"),
    [
        ("Edit", {"file_path": str(ROOT / "datos" / "sinteticos" / "tickets.json")}, 2),
        ("Write", {"file_path": "datos/sinteticos/nuevo.json"}, 2),
        ("Write", {"file_path": str(ROOT / ".env")}, 2),
        ("Edit", {"file_path": str(ROOT / "harness" / "options.py")}, 0),
        ("Edit", {"file_path": str(ROOT / "datos" / "generar_sinteticos.py")}, 0),
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
        ("Bash", "uv run python datos/generar_sinteticos.py --check", 0),
        ("Bash", "ls .venv", 0),
    ],
)
def test_shell_tools(tool_name, command, code):
    assert run("proteger_rutas.py", tool_name, {"command": command}).returncode == code


def test_post_tool_use_skips_non_python_files():
    # Si ejecutara pytest aquí habría recursión; con un .md debe salir sin hacer nada.
    result = run("ejecutar_tests.py", "Edit", {"file_path": "NOTAS.md"}, event="PostToolUse")
    assert result.returncode == 0 and result.stderr == ""
