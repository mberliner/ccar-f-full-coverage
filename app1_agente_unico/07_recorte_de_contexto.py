"""Recorte de los resultados de una tool antes de que se acumulen en el contexto.

CONCEPTO [TS 5.1-K3, S3]: los resultados de las tools se acumulan en el
contexto y consumen tokens de forma desproporcionada a lo que importan; se
recortan a los campos relevantes antes de que entren en el historial.

QUÉ DICE LA GUÍA:
- Los resultados de las tools se van acumulando en el contexto y consumen
  tokens de forma desproporcionada a lo que aportan. El ejemplo de la guía es
  una consulta de pedido que devuelve más de 40 campos cuando la tarea solo
  necesita 5 (5.1-K3).
- La destreza es recortar las salidas verbosas de las tools a los campos
  relevantes antes de que se acumulen en el contexto; en el ejemplo de la
  guía, quedarse solo con los campos de la consulta que sirven para una
  devolución (5.1-S3).
- Cada petición siguiente lleva el historial completo de la conversación
  (5.1-K4, introducido en `01`; aquí solo se usa).

POR QUÉ IMPORTA (inferencia propia, a partir de 5.1-K3 y K4): lo que entra en
el historial viaja en todas las peticiones siguientes, así que un campo que
nadie usa se vuelve a leer y a facturar cada vez. Ocho consultas de 40 campos
son 320 campos que acompañan a cada petición posterior.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Dejar los resultados enteros en el contexto (`--anti sin_recorte`): es el
    consumo desproporcionado de 5.1-K3.
  - Recortar tarde. La guía pide recortar antes de que el resultado se acumule
    (5.1-S3); resumir el historial después, además, arriesga condensar cifras,
    fechas y estados en frases vagas (5.1-K1, de `app2/05`).
- Inferencias propias:
  - «Pedir al modelo que ignore lo que sobra» no libera contexto: los campos
    siguen en el historial y se leen en cada petición.
  - Recortar tanto que falte un campo que la tarea necesita rompe la respuesta:
    el recorte se decide por lo que la tarea usa. En esta demostración la lista
    de campos es fija y está en el código; en un sistema real la fija quien
    conoce las preguntas que se van a hacer.
- Lo que la medida no respalda: que los campos sobrantes empeoren la respuesta.
  Sin recorte el modelo también acierta; la señal de este módulo es de tokens,
  no de calidad.
- Límite de la comprobación: la respuesta se da por correcta si el primer
  equipo que nombra es el esperado, buscando primero por ID y, si no hay ninguno,
  por nombre con su mayúscula (cuatro equipos se llaman con palabras comunes:
  «por seguridad» no es el equipo Seguridad). No distingue «es X, no Y» de «es Y,
  no X», y una frase que empiece por «Datos…» sin ningún ID se tomaría por el
  equipo Datos. Las correcciones que tuvo están en `docs/hallazgos.md`.

Qué se mide: los tokens de entrada de cada petición, que salen del `usage` de
la respuesta de la API, y si la respuesta sigue siendo correcta con 5 campos. El
recorte es determinista; cuántas peticiones hace el modelo no lo es.

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 07.

INTRODUCE: TS 5.1-K3, TS 5.1-S3
USA: TS 1.1-K1, TS 1.1-S1, TS 1.1-S2, TS 5.1-K4

Uso: `uv run python app1_agente_unico/07_recorte_de_contexto.py [--anti sin_recorte] [--repeat N] [--budget USD]`
"""

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials  # noqa: E402
from harness.budget import BudgetExceeded, CostGuard  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402

ANTI_VARIANTS = ["sin_recorte"]
# Los 5 campos de los 40 que responden a las preguntas del módulo. Es lo que
# conserva el recorte; las etiquetas del generador dicen lo mismo y un test lo comprueba.
KEEP_FIELDS = ["team_id", "team_name", "laptops_total", "laptops_assigned", "open_requests"]
# Red de seguridad: solo evita un bucle infinito. La parada es `stop_reason`.
SAFETY_CAP = 16

SYSTEM = (
    "Eres el agente de inventario de TI de una empresa ficticia. Responde con los datos de las tools, "
    "sin inventar. Consulta los equipos de uno en uno (una consulta por turno) y responde en español, "
    "de forma breve."
)
# Dos preguntas en la misma conversación: la segunda se responde con lo que ya
# está en el historial, así que paga todo lo acumulado en la primera.
QUESTIONS = [
    "¿Qué equipo tiene más portátiles sin asignar? Consulta los equipos uno por uno con las tools.",
    "Y de ese equipo, ¿cuántas solicitudes abiertas hay?",
]

TOOLS = [
    {
        "name": "list_teams",
        "description": "Lista los equipos con su ID (EQ-NN) y su nombre.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_team_inventory",
        "description": "Devuelve el registro de inventario de un equipo por su ID (EQ-NN).",
        "input_schema": {"type": "object", "properties": {"team_id": {"type": "string"}}, "required": ["team_id"]},
    },
]


# --- Recorte --------------------------------------------------------------------


def trim_fields(record: dict[str, Any], keep: list[str]) -> dict[str, Any]:
    """5.1-S3: deja solo los campos relevantes, en el orden de `keep`; nunca inventa uno que no exista."""
    return {name: record[name] for name in keep if name in record}


def field_count(record: dict[str, Any]) -> int:
    return len(record)


def execute_tool(name: str, tool_input: dict[str, Any], *, trim: bool) -> str:
    """Ejecuta una tool local. El recorte ocurre aquí, ANTES de que el resultado entre en el historial."""
    teams = load("inventario_equipos.json")["teams"]
    if name == "list_teams":
        return json.dumps({"teams": [{"team_id": t["team_id"], "team_name": t["team_name"]} for t in teams]}, ensure_ascii=False)
    if name == "get_team_inventory":
        team = next((t for t in teams if t["team_id"] == tool_input.get("team_id")), None)
        if team is None:
            return json.dumps({"error": f"no existe el equipo {tool_input.get('team_id')}"}, ensure_ascii=False)
        # Variante correcta: 5 campos. Variante `sin_recorte`: los 40 tal cual los devuelve el sistema.
        return json.dumps(trim_fields(team, KEEP_FIELDS) if trim else team, ensure_ascii=False)
    return json.dumps({"error": f"tool desconocida: {name}"}, ensure_ascii=False)


# --- Bucle y medida ---------------------------------------------------------------


@dataclass
class Request:
    """Una petición a la API: su número, los tokens de entrada que llevó y cuántas tools pidió la respuesta."""

    number: int
    input_tokens: int
    tool_calls: int


@dataclass
class LoopResult:
    stop: str
    requests: list[Request]
    history: list[dict[str, Any]]
    final_text: str | None = None
    field_counts: list[int] = field(default_factory=list)


def input_tokens_of(usage: Any) -> int:
    """Tokens de entrada de la petición, con los de caché: es lo que el modelo tuvo que leer."""
    return (
        (usage.input_tokens or 0)
        + (getattr(usage, "cache_creation_input_tokens", None) or 0)
        + (getattr(usage, "cache_read_input_tokens", None) or 0)
    )


def total_input(requests: list[Request]) -> int:
    return sum(r.input_tokens for r in requests)


def peak_input(requests: list[Request]) -> int:
    return max((r.input_tokens for r in requests), default=0)


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 2) if b else None


def run_loop(
    create: Callable[[list[dict]], Any],
    messages: list[dict],
    executor: Callable[[str, dict], str],
    *,
    safety_cap: int = SAFETY_CAP,
    first_number: int = 1,
    echo: bool = True,
) -> LoopResult:
    """Bucle agéntico que anota el `usage` de cada petición. Para por `stop_reason` (1.1-S1)."""
    history = list(messages)
    requests: list[Request] = []
    counts: list[int] = []
    for number in range(first_number, first_number + safety_cap):
        # 5.1-K4 (USA): cada petición lleva el historial completo, con todo lo acumulado.
        response = create(history)
        history.append({"role": "assistant", "content": response.content})
        uses = [b for b in response.content if b.type == "tool_use"]
        requests.append(Request(number, input_tokens_of(response.usage), len(uses)))
        if echo:
            print(f"[petición {number}] entrada={requests[-1].input_tokens} tokens · tools={[u.name for u in uses]}")
        if response.stop_reason != "tool_use":
            final = " ".join(b.text for b in response.content if b.type == "text") or None
            return LoopResult(response.stop_reason, requests, history, final, counts)
        results = []
        for use in uses:
            content = executor(use.name, use.input)
            # Solo cuentan los resultados del inventario: la lista de equipos no es un registro de 40 campos.
            if use.name == "get_team_inventory":
                counts.append(field_count(json.loads(content)))
            results.append({"type": "tool_result", "tool_use_id": use.id, "content": content})
        history.append({"role": "user", "content": results})
    return LoopResult("red_de_seguridad", requests, history, None, counts)


# --- Comprobación de la respuesta ------------------------------------------------


def mentions(text: str | None, value: str) -> bool:
    return bool(text) and re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text, re.IGNORECASE) is not None


def answer_is_correct(text: str | None, expected_team_id: str) -> bool:
    """El primer equipo que nombra la respuesta es el esperado: se busca por ID y, si no hay ninguno, por nombre.

    Los equipos siguientes son contexto («le siguen…»). Cuatro equipos se llaman con palabras comunes (Redes, Datos,
    Seguridad, Plataforma), así que el ID manda y el nombre solo cuenta escrito con su mayúscula: «por seguridad» no es
    el equipo Seguridad. Límites: no distingue «es X, no Y» de «es Y, no X», y una frase que empiece por «Datos…»
    sin ningún ID se tomaría por el equipo Datos.
    """
    if not text:
        return False
    teams = load("inventario_equipos.json")["teams"]
    by_id = [(m.start(), t["team_id"]) for t in teams for m in [re.search(rf"(?<!\w){re.escape(t['team_id'])}(?!\w)", text, re.IGNORECASE)] if m]
    if by_id:
        return min(by_id)[1] == expected_team_id
    by_name = [(m.start(), t["team_id"]) for t in teams for m in [re.search(rf"(?<!\w){re.escape(t['team_name'])}(?!\w)", text)] if m]
    return bool(by_name) and min(by_name)[1] == expected_team_id


def follow_up_is_correct(text: str | None, expected_team_id: str) -> bool:
    team = next(t for t in load("inventario_equipos.json")["teams"] if t["team_id"] == expected_team_id)
    return mentions(text, str(team["open_requests"]))


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    args = parser.parse_args()
    trim = args.anti != "sin_recorte"

    print(credentials.describe())
    credentials.require_api_key()
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")
    expected = load("inventario_equipos_etiquetas.json")["expected"]["team_with_most_unassigned_laptops"]

    import anthropic

    client = anthropic.Anthropic()
    for run in range(1, args.repeat + 1):
        # El tope es de toda la ejecución del script, repartido entre repeticiones.
        guard = CostGuard(model, budget / args.repeat)

        def create(messages: list[dict]) -> Any:
            response = client.messages.create(model=model, max_tokens=2048, system=SYSTEM, messages=messages, tools=TOOLS)
            guard.add(response.usage)  # corta con BudgetExceeded si se supera el tope
            return response

        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'correcta (con recorte)'} ===")
        history: list[dict[str, Any]] = []
        requests: list[Request] = []
        answers: list[str | None] = []
        counts: list[int] = []
        try:
            for question in QUESTIONS:
                history.append({"role": "user", "content": question})
                print(f"[pregunta] {question}")
                result = run_loop(
                    create, history, lambda n, a: execute_tool(n, a, trim=trim), first_number=len(requests) + 1
                )
                history, requests, counts = result.history, requests + result.requests, counts + result.field_counts
                answers.append(result.final_text)
                print(f"[respuesta] {result.final_text or '(sin respuesta final)'}")
        except BudgetExceeded as exc:
            print(f"[corte] {exc}")
            return 1
        fields = sorted(set(counts))
        print(
            f"[medida] peticiones={len(requests)} · entrada total={total_input(requests)} tokens · "
            f"máxima={peak_input(requests)} · campos por resultado={fields} · "
            f"equipo correcto={answer_is_correct(answers[0], expected)} · "
            f"solicitudes correctas={follow_up_is_correct(answers[1], expected)}"
        )
        print(f"[fin] coste=${guard.spent:.4f} (tope ${guard.max_usd:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
