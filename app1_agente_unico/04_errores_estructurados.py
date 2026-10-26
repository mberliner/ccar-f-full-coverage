"""Errores estructurados en tools MCP: que el agente pueda decidir qué hacer ante un fallo.

CONCEPTO [TS 2.2-K1, K2, K3, K4, S1, S2, S4]: el flag de error de MCP, las cuatro
categorías de error, el coste de un error genérico, errores reintentables y no
reintentables, y la diferencia entre un fallo de acceso y un resultado vacío válido.

QUÉ DICE LA GUÍA:
- En MCP, la tool avisa al agente de que algo salió mal marcando su resultado
  con el flag `isError` (2.2-K1).
- La guía separa cuatro clases de fallo: transitorios (se agotó el tiempo, el
  servicio no responde), de validación (la entrada no es válida), de negocio
  (se viola una política) y de permisos (2.2-K2).
- Si todas las tools contestan lo mismo, del estilo «Operation failed», el
  agente no tiene con qué decidir cómo recuperarse (2.2-K3).
- Unos fallos admiten reintento y otros no; devolver metadatos estructurados
  es lo que evita reintentar en vano (2.2-K4).
- El error estructurado lleva `errorCategory`, un booleano `isRetryable` y una
  descripción que se pueda leer (2.2-S1). Como valores de `errorCategory`, la
  guía solo enumera `transient`, `validation` y `permission`: no da nombre a la
  categoría de negocio, aunque la cuente entre las cuatro clases de K2.
- Ante una regla de negocio, la respuesta indica que no es reintentable (la guía
  lo escribe `retriable: false`, no `isRetryable`) y explica la regla, para que
  el agente se lo cuente bien a la persona usuaria (2.2-S2).
- No es lo mismo no haber podido consultar (y tener que decidir si se
  reintenta) que haber consultado bien sin encontrar nada (2.2-S4).
- 2.2-S3 (recuperación local en el subagente y propagación al coordinador) no
  es de este módulo: va a `app3/04`.

POR QUÉ IMPORTA (inferencia propia): lo que el agente hace ante un error depende
de lo que el error le cuenta. Con una categoría y un `isRetryable` puede
reintentar lo transitorio, corregir lo inválido y explicar lo prohibido. Sin
ellos, reintenta lo que no tiene arreglo o se rinde ante lo que sí lo tenía.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: el mismo error genérico para todo (`--anti generico`, 2.2-K3)
  y confundir un fallo de acceso con un resultado vacío válido
  (`--anti fallo_como_vacio`, 2.2-S4).
- Decisiones de este proyecto: la categoría de negocio se llama `business`, y el
  booleano es siempre `isRetryable`, también en la regla de negocio; el
  comentario del servidor señala la grafía `retriable` de la guía. En el examen
  manda la guía.
- Inferencias propias: devolver la excepción tal cual o un texto suelto sin
  `isError` sería otra forma del error genérico. Y la rama de validación no se
  ve en ejecución, porque el modelo corrige el ID gracias a la descripción de
  la tool (ver README y `docs/hallazgos.md`).

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 04.

INTRODUCE: TS 2.2-K1, TS 2.2-K2, TS 2.2-K3, TS 2.2-K4, TS 2.2-S1, TS 2.2-S2, TS 2.2-S4

Uso: `uv run python app1_agente_unico/04_errores_estructurados.py [--anti generico|fallo_como_vacio] [--repeat N]`
"""

import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeAgentOptions, query  # noqa: E402

from app1_agente_unico.servers.mesa import SERVER_NAME, ErroresState, build_server, make_tools, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["generico", "fallo_como_vacio"]
MCP_PREFIX = f"mcp__{SERVER_NAME}__"
TRANSIENT_TOOL = "fetch_ticket_history"
NO_CATEGORY = "sin categoría"

# Un solo mensaje que obliga a llamar a las cinco tools. El ID del usuario va mal formado a propósito.
PROMPT = (
    "Necesito cinco cosas del caso del ticket TCK-4001:\n"
    "1. El histórico del ticket TCK-4001.\n"
    "2. El perfil de la persona con ID 1001.\n"
    "3. Reasignar 12 puestos de la licencia «editor» a EMP-1001.\n"
    "4. Exportar el registro de auditoría completo.\n"
    "5. La lista de tickets de EMP-9999.\n"
    "Al final dime cómo ha ido cada una."
)

# El prompt no explica qué hacer con cada error: eso lo decide el agente con los metadatos del error.
SYSTEM = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Haz las tareas que te pidan con tus tools. "
    "Si una tool falla, decide qué hacer y explica a la persona el resultado de cada tarea. Responde en español."
)

# --- Lectura del RunRecord ---------------------------------------------------------


def short_name(name: str) -> str:
    return name.removeprefix(MCP_PREFIX)


def error_category(text: str | None) -> str:
    """`errorCategory` del texto del resultado, o «sin categoría» si el error es genérico o no es JSON."""
    try:
        data = json.loads(text or "")
    except json.JSONDecodeError:
        return NO_CATEGORY
    return data.get("errorCategory", NO_CATEGORY) if isinstance(data, dict) else NO_CATEGORY


@dataclass
class Analysis:
    calls: dict[str, int] = field(default_factory=dict)
    # Reintentos: llamadas idénticas (mismo input) después de una que ya había fallado.
    retries: dict[str, int] = field(default_factory=dict)
    # Por tool, en orden de llamada: la categoría del error, o None si la llamada tuvo éxito.
    categories: dict[str, list[str | None]] = field(default_factory=dict)


def analyze(rec: RunRecord) -> Analysis:
    analysis = Analysis()
    failed_inputs: dict[str, set[str]] = {}
    for call in rec.tool_calls:
        tool = short_name(call.name)
        key = json.dumps(call.input, sort_keys=True)
        analysis.calls[tool] = analysis.calls.get(tool, 0) + 1
        # Corregir la entrada tras un error de validación cambia el input: no es un reintento ciego.
        if key in failed_inputs.get(tool, set()):
            analysis.retries[tool] = analysis.retries.get(tool, 0) + 1
        if call.is_error:
            failed_inputs.setdefault(tool, set()).add(key)
        analysis.categories.setdefault(tool, []).append(error_category(call.result_text) if call.is_error else None)
    return analysis


def useless_retries(analysis: Analysis) -> int:
    """Reintentos idénticos de tools cuyo fallo no se arregla reintentando (todas salvo la transitoria)."""
    return sum(n for tool, n in analysis.retries.items() if tool != TRANSIENT_TOOL)


def transient_recovered(rec: RunRecord) -> bool:
    """¿Falló la tool transitoria y una llamada posterior tuvo éxito?"""
    calls = [c for c in rec.tool_calls if short_name(c.name) == TRANSIENT_TOOL]
    failed = next((i for i, c in enumerate(calls) if c.is_error), None)
    return failed is not None and any(not c.is_error for c in calls[failed + 1:])


NO_HISTORY_RE = re.compile(
    r"(no tiene|no hay|sin|no se registr\w+|no consta)\b.{0,40}\b(hist[oó]rico|eventos)\b|hist[oó]rico\s+(est[aá]\s+)?vac[ií]o",
    re.IGNORECASE,
)


def says_no_history(text: str | None) -> bool:
    """¿Afirma la respuesta que el ticket no tiene histórico? (señal de `fallo_como_vacio`)."""
    return bool(text and NO_HISTORY_RE.search(text))


# --- Configuración ------------------------------------------------------------------


def build_options(anti: str | None, state: ErroresState, *, budget: float, model: str) -> ClaudeAgentOptions:
    kwargs = {"state": state, "estructurado": anti != "generico", "fallo_como_vacio": anti == "fallo_como_vacio"}
    names = [tool_name(t.name) for t in make_tools("errores", **kwargs)]
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=SYSTEM,
        mcp_servers={SERVER_NAME: build_server("errores", **kwargs)},
        tools=[],  # sin tools integradas: el agente solo ve las cinco del servidor
        allowed_tools=names,
        permission_mode="dontAsk",
        max_turns=20,  # red de seguridad, no la parada
    )


def expectation(anti: str | None) -> str:
    return {
        None: "reintenta solo el transitorio, corrige el ID, explica el cupo y el permiso sin reintentarlos, y dice que EMP-9999 no tiene tickets",
        "generico": "todos los errores son «Operation failed»: reintentos inútiles o una explicación equivocada",
        "fallo_como_vacio": "el timeout llega como histórico vacío: afirma que el ticket no tiene histórico",
    }[anti]


def report(rec: RunRecord, anti: str | None) -> None:
    analysis = analyze(rec)
    print(f"[medida] llamadas={analysis.calls} · reintentos idénticos={analysis.retries} · reintentos inútiles={useless_retries(analysis)}")
    print(f"[medida] categorías por tool={analysis.categories}")
    print(f"[medida] transitorio recuperado={transient_recovered(rec)} · dice que no hay histórico={says_no_history(rec.final_text)}")


# --- Ejecución ---------------------------------------------------------------------


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")

    for run in range(1, args.repeat + 1):
        # Estado nuevo por ejecución: el transitorio vuelve a fallar solo la primera vez.
        state = ErroresState()
        options = build_options(args.anti, state, budget=budget / args.repeat, model=model)
        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'correcta'} ===")
        print(f"[esperado] {expectation(args.anti)}")
        rec = await record(query(prompt=PROMPT, options=options))
        report(rec, args.anti)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
