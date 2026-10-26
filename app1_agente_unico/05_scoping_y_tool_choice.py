"""Cuántas tools ve un agente y cómo se fuerza una llamada: scoping y `tool_choice`.

CONCEPTO [TS 2.3-K1, K4, S4, S5]: la fiabilidad de selección frente al número de
tools, las tres opciones de `tool_choice` y su uso para forzar una primera tool o
para garantizar que el modelo llame a una en vez de contestar con texto.

QUÉ DICE LA GUÍA:
- Cuantas más tools ve un agente, más difícil es la decisión y peor elige: la
  guía contrapone 18 tools a 4–5 (2.3-K1).
- `tool_choice` tiene tres modos: `"auto"` (el modelo decide si llama o no),
  `"any"` (tiene que llamar a alguna) y el forzado
  `{"type": "tool", "name": "..."}` (tiene que llamar a esa) (2.3-K4).
- El modo forzado sirve para que una tool determinada vaya la primera, como una
  extracción de metadatos antes de enriquecer; lo que viene después se hace en
  los turnos siguientes (2.3-S4).
- `"any"` asegura que la respuesta sea una llamada a tool y no texto de
  conversación (2.3-S5).
- El reparto de tools entre roles (2.3-K2, K3, S1–S3) está en `app3/03`.

POR QUÉ IMPORTA (inferencia propia): con `auto` el modelo puede contestar con
texto cuando el flujo necesitaba una llamada, y con demasiadas tools carga más
definiciones y puede elegir distinto cada vez. Las dos cosas se arreglan en la
configuración, no en el prompt.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: ofrecer 18 tools donde bastan 4–5 (`--anti amplio`) y dejar
  en `auto` un paso que tiene que empezar por una tool concreta.
- Inferencias propias: `any` o el forzado no pueden ir en todos los turnos,
  porque el modelo nunca podría dar su respuesta final. Y `any` garantiza una
  llamada, no cuál: si importa cuál, es el forzado.
- Lo observado aquí (ver README y `docs/hallazgos.md`): con seis peticiones
  claras, 18 tools no bajaron el acierto ni con Haiku 5.5 ni con Haiku 4.5; lo
  que subió fue el coste por petición y, con Haiku 4.5, la dispersión entre
  alias. El fallo de selección que describe la guía no se reprodujo.
- EN PRODUCCIÓN (no evaluable): `any` y el forzado devuelven 400 en Sonnet 5.5
  (comprobado) y, según el repositorio de estudio, en Opus 5.5 y Fable 5.1;
  Haiku 5.5 y Haiku 4.5 los aceptan. La carga diferida de definiciones (*tool
  search*) no se activó en las sondas con ningún valor de `ENABLE_TOOL_SEARCH`,
  así que su efecto no se demuestra: se fija por precaución. En el examen manda
  la guía.

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 05.

INTRODUCE: TS 2.3-K1, TS 2.3-K4, TS 2.3-S4, TS 2.3-S5

Uso: `uv run python app1_agente_unico/05_scoping_y_tool_choice.py --parte scoping|tool_choice [--anti amplio] [--repeat N]`
"""

import asyncio
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeAgentOptions, query  # noqa: E402

from app1_agente_unico.servers.mesa import CANONICAL, SERVER_NAME, build_server, make_tools, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.budget import BudgetExceeded, CostGuard  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

PARTS = ["scoping", "tool_choice"]
ANTI_VARIANTS = ["amplio"]  # solo de la parte `scoping`
MCP_PREFIX = f"mcp__{SERVER_NAME}__"

TICKET_ID = load("tickets.json")[0]["ticket_id"]
USER_IDS = [u["user_id"] for u in load("usuarios.json")][:2]

# --- Parte scoping (2.3-K1) --------------------------------------------------------


@dataclass
class Request:
    label: str
    prompt: str
    expected: str  # una de las 5 tools de `acotado`


# Seis peticiones sobre las cinco tools estrechas. `amplio` ofrece además 13 alias casi iguales.
BATTERY = [
    Request("ticket", f"Dame los datos del ticket {TICKET_ID}.", "get_ticket"),
    Request("usuario", f"¿Quién es {USER_IDS[0]}? Dime nombre y departamento.", "get_user"),
    Request("articulo", "Lee el artículo KB-109 completo.", "get_article"),
    Request("kb", "Busca en la base de conocimiento artículos sobre la VPN.", "search_kb"),
    Request("tickets-wifi", "Busca tickets sobre la wifi de las salas de reuniones.", "search_tickets"),
    Request("tickets-usuario", f"Lista los tickets de {USER_IDS[1]}.", "search_tickets"),
]


def is_correct(chosen: str | None, expected: str) -> bool:
    """Acierta si la tool elegida es la esperada o un alias suyo: elegir un alias no es un error de enrutamiento."""
    return chosen is not None and CANONICAL.get(chosen) == expected


def first_mesa_call(rec: RunRecord) -> str | None:
    for call in rec.tool_calls:
        if call.name.startswith(MCP_PREFIX):
            return call.name.removeprefix(MCP_PREFIX)
    return None


def accuracy(results: list[tuple[str | None, str]]) -> tuple[int, int]:
    return sum(is_correct(chosen, expected) for chosen, expected in results), len(results)


def rate_text(rate: tuple[int, int]) -> str:
    hits, total = rate
    return f"{hits}/{total} ({round(100 * hits / total)} %)" if total else "sin datos"


def distinct_choices(results: list[tuple[str, str | None]]) -> dict[str, set[str | None]]:
    """Por petición, las tools distintas que eligió a lo largo de las repeticiones."""
    choices: dict[str, set[str | None]] = {}
    for label, chosen in results:
        choices.setdefault(label, set()).add(chosen)
    return choices


def inconsistent(choices: dict[str, set[str | None]]) -> list[str]:
    """Peticiones para las que la tool elegida cambió entre repeticiones."""
    return [label for label, names in choices.items() if len(names) > 1]


SCOPE_SYSTEM = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Atiende la petición con la tool más "
    "adecuada y responde en español y de forma breve."
)


def build_scope_options(anti: str | None, *, budget: float, model: str) -> ClaudeAgentOptions:
    family = "amplio" if anti == "amplio" else "acotado"
    names = [tool_name(t.name) for t in make_tools(family)]
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=SCOPE_SYSTEM,
        mcp_servers={SERVER_NAME: build_server(family)},
        tools=[],  # sin tools integradas: el agente solo ve las del servidor (18 o 5)
        allowed_tools=names,
        permission_mode="dontAsk",
        # Regla 4 del proyecto: lo que se mide es el número de tools, no la carga diferida de
        # definiciones. Con este servidor y estos modelos la carga diferida no se activó en las
        # sondas con ningún valor (docs/hallazgos.md); se fija igualmente y el recorder confirma
        # `tool_search_loads == 0`.
        env={"ENABLE_TOOL_SEARCH": "false"},
        max_turns=4,  # red de seguridad: basta una llamada y la respuesta
    )


# --- Parte tool_choice (2.3-K4, 2.3-S4, 2.3-S5) --------------------------------------

MODES = ["auto", "any", "forzado"]
FORCED_TOOL = "extract_ticket_metadata"

TOOLS = [
    {
        "name": FORCED_TOOL,
        "description": "Extrae la categoría (acceso, hardware, software, red, licencias, gastos) y la urgencia "
        "(alta o normal) de un ticket a partir de su texto. Es el primer paso para preparar un ticket nuevo.",
        "input_schema": {
            "type": "object",
            "properties": {"ticket_text": {"type": "string", "description": "Texto del ticket tal como llegó"}},
            "required": ["ticket_text"],
        },
    },
    {
        "name": "search_kb",
        "description": "Busca artículos de la base de conocimiento por palabras clave. Devuelve hasta 3 con su ID y título.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Palabras clave en español"}},
            "required": ["query"],
        },
    },
]

TC_SYSTEM = "Eres un asistente de la mesa de ayuda TI de una empresa ficticia. Responde en español y de forma breve."
# Una petición de opinión: con `auto` el modelo contesta con texto sin llamar a ninguna tool (con
# «¿qué te parece?» o «¿es urgente?» Haiku 5.5 sí llamaba a la tool y el contraste no se veía).
# El flujo, en cambio, necesita los metadatos del ticket: ahí `any` o forzado garantizan la llamada.
TC_PROMPT = (
    "Entre nosotros: ¿crees que este tipo de tickets suelen ser un problema grave? "
    f"«{load('tickets.json')[0]['description']}»"
)

CATEGORY_WORDS = {
    "red": ("vpn", "wifi", "wi-fi", "impresora", "conexión"),
    "acceso": ("contraseña", "cuenta", "acceso", "portal"),
    "licencias": ("licencia",),
    "gastos": ("reembolso", "gasto"),
    "hardware": ("portátil", "pantalla", "teclado", "batería"),
    "software": ("aplicación", "correo", "navegador"),
}
URGENT_WORDS = ("no puedo", "bloquead", "se cae", "caíd", "desconecta")


def execute_tool(name: str, args: dict[str, Any]) -> str:
    """Ejecuta una de las dos tools locales y devuelve su resultado como JSON."""
    if name == FORCED_TOOL:
        text = args.get("ticket_text", "").lower()
        category = next((c for c, words in CATEGORY_WORDS.items() if any(w in text for w in words)), "software")
        urgency = "alta" if any(w in text for w in URGENT_WORDS) else "normal"
        return json.dumps({"category": category, "urgency": urgency}, ensure_ascii=False)
    if name == "search_kb":
        words = {w for w in args.get("query", "").lower().split() if len(w) >= 3}
        hits = [
            {"article_id": a["article_id"], "title": a["title"]}
            for a in load("articulos_kb.json")
            if a["category"] in words or any(w in f"{a['title']} {a['body']}".lower() for w in words)
        ]
        return json.dumps({"results": hits[:3]}, ensure_ascii=False)
    return json.dumps({"error": f"tool desconocida: {name}"})


def choice_for_turn(mode: str, turn: int) -> dict[str, str]:
    """`tool_choice` de cada turno: el modo elegido en el primero y `auto` en los siguientes."""
    if mode not in MODES:
        raise ValueError(f"modo desconocido: {mode}")
    if turn > 0 or mode == "auto":
        # Con `any` o forzado en todos los turnos el modelo nunca podría dar una respuesta final.
        return {"type": "auto"}
    if mode == "any":
        return {"type": "any"}  # llama a alguna tool, no devuelve texto (2.3-S5)
    return {"type": "tool", "name": FORCED_TOOL}  # llama a esta tool primero (2.3-S4)


def first_block_kind(content: list[Any]) -> str:
    """«tool_use» o «texto» según el primer bloque visible de la respuesta (el razonamiento no cuenta)."""
    visible = [b for b in content if b.type not in ("thinking", "redacted_thinking")]
    if not visible:
        return "vacío"
    return "tool_use" if visible[0].type == "tool_use" else "texto"


@dataclass
class Turn:
    choice: str  # tipo de `tool_choice` enviado
    first_kind: str  # con qué empezó la respuesta
    names: list[str]  # tools que pidió


@dataclass
class ModeRun:
    mode: str
    turns: list[Turn] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    final_text: str | None = None


def run_mode(create: Callable[[list[dict], dict], Any], mode: str, prompt: str, *, max_turns: int = 4) -> ModeRun:
    """Bucle de la Messages API con el `tool_choice` del modo en el primer turno y `auto` después."""
    run = ModeRun(mode, messages=[{"role": "user", "content": prompt}])
    for turn in range(max_turns):
        choice = choice_for_turn(mode, turn)
        response = create(run.messages, choice)
        uses = [b for b in response.content if b.type == "tool_use"]
        run.turns.append(Turn(choice["type"], first_block_kind(response.content), [u.name for u in uses]))
        run.messages.append({"role": "assistant", "content": response.content})
        # La parada la decide `stop_reason`, como en app1/01.
        if response.stop_reason != "tool_use":
            run.final_text = " ".join(b.text for b in response.content if b.type == "text") or None
            return run
        results = [{"type": "tool_result", "tool_use_id": u.id, "content": execute_tool(u.name, u.input)} for u in uses]
        run.messages.append({"role": "user", "content": results})
    return run


def starts_with_tool(runs: list[ModeRun]) -> tuple[int, int]:
    """(ejecuciones cuya primera respuesta empezó por una tool, total)."""
    return sum(1 for r in runs if r.turns and r.turns[0].first_kind == "tool_use"), len(runs)


# --- Ejecución ---------------------------------------------------------------------


async def run_scoping(args: Any, model: str, budget: float) -> None:
    print(f"\n=== scoping · variante {'amplio (18 tools)' if args.anti else 'acotado (5 tools)'} · {len(BATTERY)} peticiones × {args.repeat} ===")
    print("[esperado] acierto parecido con un modelo reciente; con 18 tools, más coste y a veces otro alias de la misma tool")
    results: list[tuple[str | None, str]] = []
    labelled: list[tuple[str, str | None]] = []
    loads = 0
    cost = 0.0
    for run in range(1, args.repeat + 1):
        for request in BATTERY:
            options = build_scope_options(args.anti, budget=budget / (args.repeat * len(BATTERY)), model=model)
            rec = await record(query(prompt=request.prompt, options=options), echo=False)
            chosen = first_mesa_call(rec)
            results.append((chosen, request.expected))
            labelled.append((request.label, chosen))
            loads += rec.tool_search_loads
            cost += rec.cost_usd or 0
            mark = "✓" if is_correct(chosen, request.expected) else "✗"
            print(f"[{run}/{args.repeat}] {mark} {request.label}: esperada={request.expected} · primera={chosen} · coste=${rec.cost_usd or 0:.4f}")
    print(f"\n[acierto] {rate_text(accuracy(results))}")
    changing = inconsistent(distinct_choices(labelled))
    print(f"[consistencia] peticiones con más de una tool elegida entre repeticiones: {changing or 'ninguna'}")
    print(f"[tool search] cargas diferidas={loads} (se espera 0)")
    # Cada petición reenvía las definiciones de todas las tools: con 18 pesan más que con 5.
    print(f"[coste] total=${cost:.4f} · por petición=${cost / len(results):.5f}")


def run_tool_choice(args: Any, model: str, budget: float) -> int:
    import anthropic

    client = anthropic.Anthropic()
    print(f"\n=== tool_choice · {len(MODES)} modos × {args.repeat} ===")
    print("[esperado] auto puede empezar por texto; any y forzado empiezan siempre por tool_use; el forzado llama a la tool fijada")
    runs: dict[str, list[ModeRun]] = {mode: [] for mode in MODES}
    for run in range(1, args.repeat + 1):
        for mode in MODES:
            # El tope es de toda la ejecución del script, repartido entre repeticiones y modos.
            guard = CostGuard(model, budget / (args.repeat * len(MODES)))

            def create(messages: list[dict], tool_choice: dict) -> Any:
                response = client.messages.create(
                    model=model, max_tokens=1024, system=TC_SYSTEM, tools=TOOLS, tool_choice=tool_choice, messages=messages
                )
                guard.add(response.usage)
                return response

            try:
                result = run_mode(create, mode, TC_PROMPT)
            except BudgetExceeded as exc:
                print(f"[corte] {exc}")
                return 1
            runs[mode].append(result)
            sequence = " → ".join(f"{t.choice}:{t.first_kind}{t.names or ''}" for t in result.turns)
            print(f"[{run}/{args.repeat}] {mode}: {sequence} · coste=${guard.spent:.4f}")
    print()
    for mode in MODES:
        print(f"[primera respuesta con tool] {mode}: {rate_text(starts_with_tool(runs[mode]))}")
    return 0


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTS, required=True)
    args = parser.parse_args()
    if args.anti and args.parte != "scoping":
        parser.error("--anti amplio es de la parte scoping")
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")
    if args.parte == "scoping":
        await run_scoping(args, model, budget)
        return 0
    # La Messages API solo admite API key.
    credentials.require_api_key()
    return run_tool_choice(args, model, budget)


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
