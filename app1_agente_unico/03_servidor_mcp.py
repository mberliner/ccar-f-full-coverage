"""Descripciones de tools: lo que decide qué tool elige el modelo.

CONCEPTO [TS 2.1-K1, K2, K3, K4, S1, S2, S3, S4]: la descripción como mecanismo
de selección, qué debe contener, el *misrouting* por descripciones solapadas, el
efecto del *system prompt* sobre la elección y las tres correcciones (describir,
renombrar, dividir).

QUÉ DICE LA GUÍA:
- Las descripciones son el mecanismo principal con el que el modelo elige entre
  tools; si son mínimas, la selección entre tools parecidas deja de ser fiable
  (2.1-K1).
- Una buena descripción lleva el formato de la entrada, consultas de ejemplo,
  casos borde y los límites de la tool (2.1-K2).
- Descripciones ambiguas o que se solapan provocan *misrouting*, como en
  `analyze_content` frente a `analyze_document` (2.1-K3).
- El texto del *system prompt* también influye: una instrucción atada a una
  palabra clave crea asociaciones con una tool que pueden anular las
  descripciones (2.1-K4).
- La corrección tiene tres vías: escribir descripciones que diferencien
  propósito, entradas, salidas y cuándo usar cada tool frente a las parecidas
  (2.1-S1); renombrar las tools y actualizar su descripción para quitar el
  solapamiento (2.1-S2); y dividir una tool genérica en varias con propósito y
  contrato definidos (2.1-S3). Los *system prompts* se revisan para eliminar las
  instrucciones por palabra clave (2.1-S4).

POR QUÉ IMPORTA (inferencia propia): el código de la tool puede ser perfecto y el
agente fallar igual, porque lo que ve el modelo no es el código sino el nombre,
la descripción y el esquema. Es la palanca más barata y la primera que se
revisa ante un enrutamiento erróneo.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: descripciones de una línea y solapadas (`--anti minimas`) y
  un *system prompt* con una regla por palabra clave que gana a las
  descripciones (`--anti palabra_clave`). La corrección de ambos es la
  configuración correcta: tools renombradas, divididas y bien descritas, y un
  prompt sin la regla.
- Inferencia propia: ante un enrutamiento erróneo, las respuestas tentadoras son
  añadir más ejemplos al prompt, un clasificador previo o fusionar tools. La
  guía da primero la descripción, el nombre y la división.

Pregunta tipo examen: ver `app1_agente_unico/README.md`, módulo 03.

INTRODUCE: TS 2.1-K1, TS 2.1-K2, TS 2.1-K3, TS 2.1-K4, TS 2.1-S1, TS 2.1-S2, TS 2.1-S3, TS 2.1-S4

Uso: `uv run python app1_agente_unico/03_servidor_mcp.py [--anti minimas|palabra_clave] [--repeat N]`
"""

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeAgentOptions, query  # noqa: E402

from app1_agente_unico.servers.mesa import SERVER_NAME, build_server, make_tools, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["minimas", "palabra_clave"]
# Palabra que la regla del *system prompt* de `palabra_clave` asocia a una tool.
TRAP_WORD = "documento"
MCP_PREFIX = f"mcp__{SERVER_NAME}__"

TICKET_IDS = [t["ticket_id"] for t in load("tickets.json")][:2]


@dataclass
class Request:
    label: str
    prompt: str
    expected: str  # tool de la configuración correcta
    expected_minimal: str  # tool que cabría esperar con solo `analyze_content` y `analyze_document`


# Seis peticiones, una tool esperada cada una. Dos llevan la palabra «documento» y no esperan
# `summarize_article`: son las que la regla por palabra clave de `palabra_clave` desvía.
BATTERY = [
    Request("ticket-datos", f"Dame los datos del ticket {TICKET_IDS[0]}: usuario, estado y fecha.",
            "extract_ticket_facts", "analyze_content"),
    Request("ticket-importe", f"¿De qué categoría y por cuánto importe es el ticket {TICKET_IDS[1]}?",
            "extract_ticket_facts", "analyze_content"),
    Request("articulo-pasos", "Dime los pasos que hay que seguir según el documento KB-109.",
            "extract_article_steps", "analyze_document"),
    Request("articulo-resumen", "Resúmeme en una frase el artículo KB-114.",
            "summarize_article", "analyze_document"),
    Request("afirmacion-1", "Comprueba si esta afirmación es cierta según el documento KB-114: «Hasta 500 EUR lo aprueba soporte».",
            "verify_claim_against_article", "analyze_document"),
    Request("afirmacion-2", "Verifica con KB-112 esta afirmación: «Las renovaciones se piden 15 días antes de caducar».",
            "verify_claim_against_article", "analyze_document"),
]


def tool_variant(anti: str | None) -> str | None:
    """`minimas` cambia las tools; `palabra_clave` deja las buenas y cambia solo el prompt."""
    return "minimas" if anti == "minimas" else None


def expected_for(request: Request, anti: str | None) -> str:
    return request.expected_minimal if anti == "minimas" else request.expected


# --- Medida ------------------------------------------------------------------------


def first_mcp_call(rec: RunRecord) -> str | None:
    """Nombre corto de la primera llamada a una tool del servidor `mesa`, o None si no llamó a ninguna."""
    for call in rec.tool_calls:
        if call.name.startswith(MCP_PREFIX):
            return call.name.removeprefix(MCP_PREFIX)
    return None


def accuracy(results: list[tuple[str | None, str]]) -> tuple[int, int]:
    """(aciertos, total) de pares (primera llamada, esperada). Sin llamada cuenta como fallo."""
    return sum(chosen == expected for chosen, expected in results), len(results)


def rate_text(rate: tuple[int, int]) -> str:
    hits, total = rate
    return f"{hits}/{total} ({round(100 * hits / total)} %)" if total else "sin datos"


# --- Configuración ------------------------------------------------------------------

BASE_SYSTEM = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Atiende la petición con la tool más "
    "adecuada y responde en español y de forma breve."
)


def system_prompt(anti: str | None) -> str:
    if anti == "palabra_clave":
        # Anti-patrón: una regla atada a una palabra clave anula las descripciones (2.1-K4).
        return BASE_SYSTEM + f" Si la petición menciona un {TRAP_WORD}, usa siempre summarize_article."
    return BASE_SYSTEM


def build_options(anti: str | None, *, budget: float, model: str) -> ClaudeAgentOptions:
    variant = tool_variant(anti)
    names = [tool_name(t.name) for t in make_tools("routing", variante=variant)]
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=system_prompt(anti),
        mcp_servers={SERVER_NAME: build_server("routing", variante=variant)},
        tools=[],  # sin tools integradas: solo ve las del servidor, y la elección depende de sus descripciones
        allowed_tools=names,  # se aprueban todas; con `dontAsk`, lo no aprobado se deniega
        permission_mode="dontAsk",
        max_turns=4,  # red de seguridad: basta una llamada y la respuesta
    )


def expectation(anti: str | None) -> str:
    return {
        None: "acierta casi todas: cada tool tiene un propósito y una descripción que la distingue",
        "minimas": "falla más: `analyze_content` y `analyze_document` no dicen en qué se diferencian",
        "palabra_clave": "las dos peticiones con «documento» van a `summarize_article` aunque piden pasos o verificar",
    }[anti]


# --- Ejecución ---------------------------------------------------------------------


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")

    print(f"\n=== variante {args.anti or 'correcta'} · {len(BATTERY)} peticiones × {args.repeat} ===")
    print(f"[esperado] {expectation(args.anti)}")
    results: list[tuple[str | None, str]] = []
    misses: dict[str, list[str | None]] = {}
    for run in range(1, args.repeat + 1):
        for request in BATTERY:
            # Opciones nuevas por petición: cada una es una conversación nueva, sin historial previo.
            options = build_options(args.anti, budget=budget / (args.repeat * len(BATTERY)), model=model)
            rec = await record(query(prompt=request.prompt, options=options), echo=False)
            chosen, expected = first_mcp_call(rec), expected_for(request, args.anti)
            results.append((chosen, expected))
            mark = "✓" if chosen == expected else "✗"
            print(f"[{run}/{args.repeat}] {mark} {request.label}: esperada={expected} · primera={chosen} · coste=${rec.cost_usd or 0:.4f}")
            if chosen != expected:
                misses.setdefault(request.label, []).append(chosen)
    print(f"\n[acierto] {rate_text(accuracy(results))}")
    for label, chosen in misses.items():
        print(f"[fallos] {label}: {chosen}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
