"""Orden aislada de `claude -p` para `app3/11` y `app3/12` (roadmap §3 regla 3, y §5).

PROPÓSITO: construir la orden de `claude -p` con el aislamiento del proyecto y un tope de
coste obligatorio, imprimirla entera antes de ejecutarla, y leer su resultado JSON (salida
estructurada, sesión y coste) sin dar por buena una respuesta que no cumple el schema.

POR QUÉ EXISTE: la sonda C1 (docs/hallazgos.md, tanda C) midió tres cosas que un módulo no
debe redescubrir cada vez:
  1. `--setting-sources project` quita la memoria y la configuración de usuario, pero deja
     pasar el `CLAUDE.md` de los directorios padre; `--setting-sources ""` y `--bare`
     quitan también el del `cwd`, que en `11` es el contexto de CI (TS 3.6-K3). Con
     `--settings` y un `claudeMdExcludes` negado sobre el propio `cwd` solo llega ese.
  2. Con un schema que el modelo no cumple, la CLI devuelve `subtype: success`, sin
     `structured_output` y con texto libre en `result`: hay que comprobarlo aparte.
  3. `--max-budget-usd` cuenta lo gastado en esa invocación, no el histórico de la sesión,
     mientras que `total_cost_usd` de una sesión reanudada sí es acumulado. El tope de
     una rama con `--resume` lo lleva, por tanto, el arnés (`Ledger`).

QUÉ NO HACE: no elige el prompt, el schema ni las tools (las pasa cada módulo, visibles en
su llamada), no reintenta y no esconde la orden: imprimirla es parte de la lección.
"""

import json
import math
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import claude_agent_sdk
import jsonschema

from harness import credentials
from harness.options import ISOLATION_ENV

# Solo lectura: la revisión no necesita editar, y `dontAsk` deniega lo demás en vez de
# esperar una respuesta que en un proceso no interactivo nunca llegaría (TS 3.6-S1).
READ_ONLY_TOOLS = ("Read", "Grep", "Glob")


def bundled_cli() -> str:
    """CLI incluida en el SDK fijado (la misma versión que muestra `credentials.describe`).

    La sonda C1 dio el mismo comportamiento con la instalada (2.1.319) y con esta (2.1.309);
    se usa la del SDK para que el resultado no dependa de qué haya instalado cada persona.
    """
    folder = Path(claude_agent_sdk.__file__).parent / "_bundled"
    found = sorted(folder.glob("claude*"))
    return str(found[0]) if found else "claude"


def build_command(
    *,
    cwd: Path,
    model: str,
    max_budget_usd: float | None,
    schema: dict[str, Any] | None = None,
    tools: tuple[str, ...] = READ_ONLY_TOOLS,
    resume: str | None = None,
    persist: bool = False,
    cli: str | None = None,
) -> list[str]:
    """Orden completa de `claude -p`. El prompt no va aquí: se pasa por stdin."""
    # Mismo criterio que harness/options.py: el tope se impone en código, no en prosa.
    if max_budget_usd is None or not math.isfinite(max_budget_usd) or max_budget_usd <= 0:
        raise ValueError("max_budget_usd debe ser un importe positivo (roadmap §3, regla 7)")
    cwd = Path(cwd).resolve()
    if not cwd.is_dir():
        raise FileNotFoundError(f"el cwd de CI no existe: {cwd}")

    # `claudeMdExcludes` con negación: se excluye todo lo que queda fuera del cwd (los
    # CLAUDE.md de los padres) y se conserva el del propio cwd. Es el mismo truco que usa
    # `.claude/settings.local.json` del proyecto.
    only_cwd = json.dumps({"claudeMdExcludes": ["!" + cwd.as_posix() + "/**"]})
    cmd = [
        cli or bundled_cli(),
        "-p",  # no interactivo: no se queda esperando entrada (TS 3.6-K1, S1)
        "--output-format", "json",  # un único objeto con resultado, sesión y coste (TS 3.6-K2)
        "--model", model,
        "--max-budget-usd", str(max_budget_usd),
        "--setting-sources", "project",  # sin memoria ni configuración de usuario
        "--settings", only_cwd,  # y del proyecto, solo el CLAUDE.md del cwd
        "--strict-mcp-config",  # ningún servidor MCP que no se pase con --mcp-config
        "--disable-slash-commands",  # sin skills ni comandos
        "--tools", ",".join(tools),
        "--allowedTools", ",".join(tools),
        "--permission-mode", "dontAsk",
    ]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
    if resume:
        cmd += ["--resume", resume]
    elif not persist:
        # Sin sesión que reanudar no hay razón para dejar nada en disco.
        cmd.append("--no-session-persistence")
    return cmd


def build_env() -> dict[str, str]:
    """Entorno del proceso: el actual más el aislamiento de `harness/options.py`."""
    credentials.detect()  # deja la API key del proyecto en os.environ si hace falta
    return {**os.environ, **ISOLATION_ENV}


def format_command(cmd: list[str]) -> str:
    return shlex.join(cmd)


def print_command(cmd: list[str], *, stdin_chars: int) -> None:
    """Imprime la orden entera: es lo que enseña el módulo."""
    print(f"[orden] {format_command(cmd)}")
    print(f"[orden] prompt por stdin: {stdin_chars} caracteres")


@dataclass
class HeadlessResult:
    # ok | schema_invalid | no_structured_output | budget_exhausted | not_json | error
    status: str
    structured: Any = None
    text: str = ""
    session_id: str = ""
    cost_usd: float = 0.0  # `total_cost_usd` tal cual: acumulado si la sesión se reanudó
    num_turns: int = 0
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def parse_result(stdout: str, schema: dict[str, Any] | None) -> HeadlessResult:
    """Lee el JSON de `--output-format json` sin fiarse del `subtype`."""
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return HeadlessResult("not_json", detail=(stdout or "")[:300])
    base = {
        "text": data.get("result") or "",
        "session_id": data.get("session_id") or "",
        "cost_usd": float(data.get("total_cost_usd") or 0.0),
        "num_turns": int(data.get("num_turns") or 0),
    }
    subtype = data.get("subtype")
    if subtype == "error_max_budget_usd":
        return HeadlessResult("budget_exhausted", detail=f"terminal_reason={data.get('terminal_reason')}", **base)
    if data.get("is_error") or subtype != "success":
        return HeadlessResult("error", detail=f"subtype={subtype}", **base)
    if schema is None:
        return HeadlessResult("ok", **base)
    # Sonda C1: ante un schema imposible llega `success` y texto libre, sin objeto.
    if "structured_output" not in data:
        return HeadlessResult("no_structured_output", **base)
    structured = data["structured_output"]
    try:
        jsonschema.validate(structured, schema)
    except jsonschema.ValidationError as error:
        path = "/".join(str(p) for p in error.absolute_path) or "(raíz)"
        return HeadlessResult("schema_invalid", structured=structured, detail=f"{path}: {error.message}", **base)
    return HeadlessResult("ok", structured=structured, **base)


class BudgetExhausted(RuntimeError):
    """El tope de la rama se agotó antes de lanzar otra invocación."""


class Ledger:
    """Tope de una rama de ejecuciones (un generador y su revisión con `--resume`).

    `--max-budget-usd` no cuenta el histórico de la sesión reanudada y `total_cost_usd` sí
    lo incluye: el coste de cada invocación es la diferencia, y lo que queda se pasa como
    flag a la siguiente.
    """

    def __init__(self, limit_usd: float):
        if not limit_usd or not math.isfinite(limit_usd) or limit_usd <= 0:
            raise ValueError("el tope de la rama debe ser un importe positivo")
        self.limit = limit_usd
        self.spent = 0.0

    def add(self, result: HeadlessResult, *, resumed_from: HeadlessResult | None = None) -> float:
        """Suma una invocación y devuelve lo que costó ella sola."""
        own = result.cost_usd - (resumed_from.cost_usd if resumed_from else 0.0)
        self.spent += max(own, 0.0)
        return own

    def remaining(self) -> float:
        left = self.limit - self.spent
        if left <= 0:
            raise BudgetExhausted(f"gastado {self.spent:.4f} $ de {self.limit:.4f} $")
        return left


def run(
    cmd: list[str],
    prompt: str,
    *,
    cwd: Path,
    schema: dict[str, Any] | None,
    runner: Callable[..., Any] = subprocess.run,
    timeout: int = 600,
) -> HeadlessResult:
    """Imprime la orden, la ejecuta con el prompt por stdin y devuelve el resultado leído."""
    print_command(cmd, stdin_chars=len(prompt))
    proc = runner(
        cmd,
        input=prompt,
        cwd=str(cwd),
        env=build_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    result = parse_result(proc.stdout, schema)
    print(
        f"[resultado] estado={result.status} sesion={result.session_id[:8]} "
        f"turnos={result.num_turns} coste_acumulado={result.cost_usd:.4f} $"
        + (f" detalle={result.detail}" if result.detail else "")
    )
    return result
