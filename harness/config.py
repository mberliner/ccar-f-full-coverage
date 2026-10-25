"""Modelo por rol y presupuesto por tipo de ejecución (roadmap §3, regla 7).

PROPÓSITO: resolver qué modelo usa cada rol (agente único, coordinador,
subagente) y cuánto puede gastar cada tipo de ejecución (agente único o sistema
multiagente), e imprimir de dónde sale cada valor.

POR QUÉ EXISTE: el modelo y el presupuesto forman parte de la lección (Haiku
para medir la tasa de fallo de un prompt, Sonnet para coordinar) y tienen que
poder cambiarse sin tocar los 8 módulos. Se leen del `.env` del proyecto antes
que del entorno, al revés que la credencial: el repositorio fija qué modelo
enseña cada lección y cuánto puede costar, y una variable exportada en la shell
para otro proyecto no debe cambiarlo sin que se note.

QUÉ NO HACE: no valida que el modelo exista (lo dice la API en la primera
llamada) ni escribe en `os.environ`: cada módulo pasa el valor de forma
explícita (`model=` en `ClaudeAgentOptions`, `AgentDefinition` o
`messages.create`), así que el `ANTHROPIC_MODEL` de la CLI no interviene.
"""

import math
import os
from pathlib import Path

from harness.credentials import ROOT, read_dotenv

MODEL_VARS = {
    "agent": "CCARF_MODEL_AGENT",  # agente único y repeticiones (app1, app2)
    "coordinator": "CCARF_MODEL_COORDINATOR",  # coordinador de app3
    "subagent": "CCARF_MODEL_SUBAGENT",  # subagentes de app3
    # Solo app2/01, en sus dos variantes. Su lección es una tasa de fallo del
    # prompt, y Haiku 5.5 no falló en 40 ejecuciones; Haiku 4.5 sí (8 de 10).
    # Cuesta unas diez veces más, pero solo en este módulo.
    "enforcement": "CCARF_MODEL_ENFORCEMENT",
}
MODEL_DEFAULTS = {
    "agent": "claude-haiku-5-5",
    "coordinator": "claude-sonnet-5-5",
    "subagent": "claude-haiku-5-5",
    "enforcement": "claude-haiku-4-5",
}

BUDGET_VARS = {
    "agent": "CCARF_BUDGET_AGENT",
    "multiagent": "CCARF_BUDGET_MULTIAGENT",
    # app2/01 con Haiku 4.5: con 0,25 $ y --repeat 10, la variante con puerta
    # usaba el 95 % del tope de cada ejecución y a veces lo superaba.
    "enforcement": "CCARF_BUDGET_ENFORCEMENT",
}
BUDGET_DEFAULTS = {"agent": 0.25, "multiagent": 1.00, "enforcement": 0.50}


def lookup(name: str, root: Path) -> tuple[str, str] | None:
    """Devuelve (valor, origen) de la primera fuente no vacía: `.env` y después entorno."""
    dotenv_value = read_dotenv(root / ".env").get(name, "").strip()
    if dotenv_value:
        return dotenv_value, ".env"
    # Un valor vacío en el entorno no cuenta, igual que en credentials.py.
    env_value = os.environ.get(name, "").strip()
    if env_value:
        return env_value, "entorno"
    return None


def resolve_model(role: str, *, root: Path = ROOT) -> tuple[str, str]:
    """Modelo del rol y su origen (`.env`, `entorno` o `defecto`)."""
    found = lookup(MODEL_VARS[role], root)
    return found if found else (MODEL_DEFAULTS[role], "defecto")


def resolve_budget(kind: str, *, root: Path = ROOT) -> tuple[float, str]:
    """Presupuesto del tipo de ejecución y su origen. Corta si no es un importe positivo."""
    found = lookup(BUDGET_VARS[kind], root)
    if not found:
        return BUDGET_DEFAULTS[kind], "defecto"
    raw, origin = found
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    # Mismo criterio que harness/options.py: el tope se impone en código y un
    # valor inválido no se sustituye en silencio por el de defecto.
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{BUDGET_VARS[kind]}={raw!r} ({origin}) debe ser un importe positivo en USD")
    return value, origin


def describe(kind: str, **fields: object) -> str:
    """Línea `[modelo] …` o `[presupuesto] …` para la salida del módulo."""
    return f"[{kind}] " + " ".join(f"{key}={value}" for key, value in fields.items())


def report_model(role: str) -> str:
    """Imprime la línea `[modelo]` del rol y devuelve el modelo resuelto."""
    model, origin = resolve_model(role)
    print(describe("modelo", rol=role, valor=model, origen=origin))
    return model

