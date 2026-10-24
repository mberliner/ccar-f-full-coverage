"""Bucle agéntico escrito a mano con la Messages API.

CONCEPTO [TS 1.1-K1, K2, K3, S1, S2, S3 · TS 5.1-K4]: ciclo de vida del bucle
agéntico, resultados de tools en el historial e historial completo en cada
petición.

QUÉ DICE LA GUÍA:
- El bucle envía la petición, mira `stop_reason` y, si vale `"tool_use"`,
  ejecuta las tools pedidas y devuelve sus resultados para la siguiente
  iteración. Con `"end_turn"` termina (1.1-K1, 1.1-S1).
- Los resultados se añaden al historial de la conversación, emparejados con
  el `tool_use_id` de la llamada, para que el modelo razone sobre el paso
  siguiente con la información nueva (1.1-K2, 1.1-S2).
- Decide el modelo qué tool llamar a partir del contexto; eso no es un árbol de
  decisión ni una secuencia de tools fijada de antemano (1.1-K3).
- La API no guarda estado: cada petición lleva el historial completo, o la
  conversación pierde la coherencia (5.1-K4).
- Anti-patrones de parada: interpretar el texto en lenguaje natural («he
  terminado»), un tope arbitrario de iteraciones como mecanismo principal, o
  tomar la presencia de texto del asistente como señal de fin (1.1-S3).

POR QUÉ IMPORTA: el Agent SDK (app1/02 en adelante) esconde este bucle. Sin
verlo una vez a mano, no se distingue lo que decide el modelo de lo que decide
el código, que es justo lo que preguntan los escenarios de D1.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: «el modelo escribió "Listo, he terminado"»
o «llevamos 10 iteraciones» como razón para parar. Solo `stop_reason` dice si
el modelo pidió otra tool. `max_turns` (o un tope) es una red de seguridad,
nunca la parada. Y un texto que acompaña a un `tool_use` es comentario, no
respuesta final.

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 01.

INTRODUCE: TS 1.1-K1, TS 1.1-K2, TS 1.1-K3, TS 1.1-S1, TS 1.1-S2, TS 1.1-S3, TS 5.1-K4

Uso: `uv run python app1_agente_unico/01_bucle_manual.py [--anti texto|tope|texto_asistente|sin_historial|arbol_fijo]`
"""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script (`python app1_agente_unico/01_….py`):
# la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials  # noqa: E402
from harness.budget import BudgetExceeded, CostGuard  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402

ANTI_VARIANTS = ["texto", "tope", "texto_asistente", "sin_historial", "arbol_fijo"]
# Red de seguridad: solo evita un bucle infinito si algo va mal. No es la
# parada del bucle correcto, que para por `stop_reason`.
SAFETY_CAP = 12
# Tope de la variante `tope`: arbitrario a propósito, como en el anti-patrón.
ANTI_CAP = 2
# Señales en lenguaje natural que la variante `texto` toma por fin de tarea.
FINISH_PHRASES = ("he terminado", "terminado", "listo", "hecho")

SYSTEM = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Atiende el ticket que te indiquen "
    "usando las tools. Comprueba en el directorio de empleados quién es la persona y consulta la base de "
    "conocimiento antes de responder. Si hay varias coincidencias, no elijas una: pide un identificador. "
    "Responde en español y de forma breve."
)

# --- Tools locales sobre los datos sintéticos ---------------------------------

TOOLS = [
    {
        "name": "get_ticket",
        "description": "Devuelve un ticket de la mesa de ayuda por su ID (formato TCK-NNNN): descripción, "
        "categoría, estado, fecha y user_id (null si quien escribe no está identificado).",
        "input_schema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "string", "description": "ID del ticket, p. ej. TCK-4012"}},
            "required": ["ticket_id"],
        },
    },
    {
        "name": "get_user",
        "description": "Busca empleados por user_id exacto (EMP-NNNN) o por nombre completo. Devuelve todas "
        "las coincidencias; con un nombre puede haber varias personas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "ID de empleado, p. ej. EMP-1004"},
                "name": {"type": "string", "description": "Nombre y apellido tal como aparecen en el ticket"},
            },
        },
    },
    {
        "name": "search_kb",
        "description": "Busca artículos de la base de conocimiento por palabras clave. Devuelve hasta 3 "
        "artículos con su ID, título, resumen y, si está obsoleto, el ID del artículo que lo sustituye.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Palabras clave en español"}},
            "required": ["query"],
        },
    },
]


def get_ticket(ticket_id: str) -> dict:
    ticket = next((t for t in load("tickets.json") if t["ticket_id"] == ticket_id), None)
    return ticket if ticket else {"error": f"no existe el ticket {ticket_id}"}


def get_user(user_id: str | None = None, name: str | None = None) -> dict:
    if not user_id and not name:
        return {"error": "hace falta user_id o name"}
    users = load("usuarios.json")
    matches = [u for u in users if (user_id and u["user_id"] == user_id) or (name and u["name"] == name)]
    return {"matches": matches} if matches else {"error": "sin coincidencias", "user_id": user_id, "name": name}


def search_kb(query: str) -> dict:
    words = {w for w in query.lower().split() if len(w) > 3}

    def score(article: dict) -> int:
        haystack = f"{article['title']} {article['body']}".lower()
        return sum(word in haystack for word in words)

    ranked = sorted((a for a in load("articulos_kb.json") if score(a)), key=score, reverse=True)
    fields = ("article_id", "title", "body", "superseded_by")
    return {"articles": [{k: a[k] for k in fields} for a in ranked[:3]]}


HANDLERS: dict[str, Callable[..., dict]] = {"get_ticket": get_ticket, "get_user": get_user, "search_kb": search_kb}


def execute_tool(name: str, tool_input: dict) -> str:
    """Ejecuta una tool local y devuelve su resultado serializado (lo que verá el modelo)."""
    handler = HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"tool desconocida: {name}"})
    try:
        result = handler(**tool_input)
    except TypeError as exc:
        # Un argumento que la tool no espera vuelve al modelo como error, no
        # tira el bucle.
        result = {"error": f"argumentos no válidos para {name}: {exc}"}
    return json.dumps(result, ensure_ascii=False)


def ambiguous_ticket() -> dict:
    """El ticket de «Soy Laura Gómez…»: sin user_id y con dos homónimos en los datos."""
    return next(t for t in load("tickets.json") if t["user_id"] is None and "Laura Gómez" in t["description"])


# --- El bucle -----------------------------------------------------------------


@dataclass
class LoopCall:
    id: str
    name: str
    input: dict
    is_error: bool


@dataclass
class LoopResult:
    stop: str  # end_turn | texto | tope | texto_asistente | red_de_seguridad | arbol_fijo
    iterations: int
    history: list[dict[str, Any]]
    tool_calls: list[LoopCall] = field(default_factory=list)
    final_text: str | None = None


def blocks_of(response: Any, kind: str) -> list[Any]:
    return [block for block in response.content if block.type == kind]


def run_loop(
    create: Callable[[list[dict]], Any],
    messages: list[dict],
    executor: Callable[[str, dict], str],
    *,
    anti: str | None = None,
    safety_cap: int = SAFETY_CAP,
    echo: bool = True,
) -> LoopResult:
    """Bucle agéntico. `create` recibe los mensajes y devuelve la respuesta del modelo.

    Es puro respecto a la API: `create` se inyecta, así que el test usa
    respuestas falsas y el módulo, `client.messages.create`.
    """
    history = list(messages)
    calls: list[LoopCall] = []

    def finish(stop: str, iteration: int, response: Any = None) -> LoopResult:
        final = " ".join(b.text for b in blocks_of(response, "text")) if response is not None else None
        if echo:
            print(f"[parada] {stop} tras {iteration} iteraciones y {len(calls)} llamadas")
        return LoopResult(stop, iteration, history, calls, final or None)

    for iteration in range(1, safety_cap + 1):
        # 5.1-K4: la API no recuerda nada; el correcto envía todo el historial.
        # `sin_historial` reenvía solo la pregunta inicial y el modelo nunca ve
        # lo que devolvieron sus tools.
        sent = list(messages) if anti == "sin_historial" else history
        response = create(sent)
        # Se guarda el contenido completo (incluidos los bloques de thinking),
        # no solo el texto: el modelo necesita ver sus propias llamadas.
        history.append({"role": "assistant", "content": response.content})
        texts = [b.text for b in blocks_of(response, "text")]
        uses = blocks_of(response, "tool_use")
        if echo:
            names = [u.name for u in uses]
            print(f"[iteración {iteration}] stop_reason={response.stop_reason} tools={names}")
            for value in texts:
                print(f"  [texto] {value.strip()[:160]}")

        # Anti-patrones de parada (1.1-S3): deciden por el texto, no por stop_reason.
        if anti == "texto" and any(p in t.lower() for t in texts for p in FINISH_PHRASES):
            return finish("texto", iteration, response)
        if anti == "texto_asistente" and any(t.strip() for t in texts):
            return finish("texto_asistente", iteration, response)

        # 1.1-S1: la única señal de continuar es stop_reason == "tool_use".
        if response.stop_reason != "tool_use":
            if response.stop_reason != "end_turn" and echo:
                # max_tokens, pause_turn, refusal…: termina, pero no es un final normal.
                print(f"[aviso] parada anómala: stop_reason={response.stop_reason}")
            return finish(response.stop_reason, iteration, response)

        # 1.1-S2: un tool_result por tool_use, con su tool_use_id, todos en un
        # único mensaje de usuario.
        results = []
        for use in uses:
            content = executor(use.name, use.input)
            is_error = "error" in json.loads(content)
            calls.append(LoopCall(use.id, use.name, use.input, is_error))
            results.append({"type": "tool_result", "tool_use_id": use.id, "content": content, "is_error": is_error})
            if echo:
                print(f"  [resultado] {use.name} {'error' if is_error else 'ok'}: {content[:160]}")
        history.append({"role": "user", "content": results})

        if anti == "tope" and iteration >= ANTI_CAP:
            return finish("tope", iteration)
    return finish("red_de_seguridad", safety_cap)


def run_fixed_tree(
    create: Callable[[list[dict]], Any],
    ticket_id: str,
    executor: Callable[[str, dict], str],
    *,
    echo: bool = True,
) -> LoopResult:
    """Anti-patrón de 1.1-K3: la secuencia de tools la decide el código, no el modelo.

    Siempre get_ticket → get_user(user_id del ticket) → search_kb(categoría),
    pase lo que pase. Con el ticket ambiguo, get_user falla (no hay user_id) y
    el árbol no tiene una rama para buscar por nombre.
    """
    calls: list[LoopCall] = []
    ticket = json.loads(executor("get_ticket", {"ticket_id": ticket_id}))
    calls.append(LoopCall("fijo_1", "get_ticket", {"ticket_id": ticket_id}, "error" in ticket))
    user_input = {"user_id": ticket.get("user_id")}
    user = json.loads(executor("get_user", user_input))
    calls.append(LoopCall("fijo_2", "get_user", user_input, "error" in user))
    kb_input = {"query": ticket.get("category", "")}
    kb = executor("search_kb", kb_input)
    calls.append(LoopCall("fijo_3", "search_kb", kb_input, "error" in json.loads(kb)))
    if echo:
        for call in calls:
            print(f"[árbol fijo] {call.name} {call.input} {'error' if call.is_error else 'ok'}")
    # Una sola llamada al modelo, solo para redactar con lo que el árbol reunió.
    prompt = (
        f"Redacta la respuesta al ticket con estos datos.\nTicket: {json.dumps(ticket, ensure_ascii=False)}\n"
        f"Usuario: {json.dumps(user, ensure_ascii=False)}\nKB: {kb}"
    )
    history: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    response = create(history)
    history.append({"role": "assistant", "content": response.content})
    final = " ".join(b.text for b in blocks_of(response, "text")) or None
    return LoopResult("arbol_fijo", 1, history, calls, final)


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    args = parser.parse_args()

    # §11.1: credencial y versiones antes de interpretar nada. La Messages API
    # solo admite API key.
    print(credentials.describe())
    credentials.require_api_key()
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")

    import anthropic

    client = anthropic.Anthropic()
    ticket = ambiguous_ticket()
    question = [{"role": "user", "content": f"Atiende el ticket {ticket['ticket_id']}."}]

    for run in range(1, args.repeat + 1):
        # El tope es de toda la ejecución del script, repartido entre repeticiones.
        guard = CostGuard(model, budget / args.repeat)

        def create(messages: list[dict], tools: list[dict] | None = TOOLS) -> Any:
            response = client.messages.create(
                model=model, max_tokens=4096, system=SYSTEM, messages=messages, tools=tools or []
            )
            guard.add(response.usage)  # corta con BudgetExceeded si se supera el tope
            return response

        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'correcta'} · {ticket['ticket_id']} ===")
        try:
            if args.anti == "arbol_fijo":
                result = run_fixed_tree(lambda m: create(m, tools=None), ticket["ticket_id"], execute_tool)
            else:
                result = run_loop(create, question, execute_tool, anti=args.anti)
        except BudgetExceeded as exc:
            print(f"[corte] {exc}")
            return 1
        print(f"[final] {result.final_text or '(sin respuesta final)'}")
        print(f"[fin] parada={result.stop} · iteraciones={result.iterations} · llamadas={len(result.tool_calls)} "
              f"· coste=${guard.spent:.4f} (tope ${guard.max_usd:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
