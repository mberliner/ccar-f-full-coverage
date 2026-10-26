"""Reparto de tools entre roles: acceso acotado, tools restringidas y una tool cross-role.

CONCEPTO [TS 2.3-K2, K3, S1, S2, S3]: por qué un agente con tools de otro rol las
malusa, el acceso acotado con alguna tool cross-role muy limitada, y las tres
correcciones: restringir por rol, sustituir una tool genérica por una restringida y
dar una tool acotada para las necesidades frecuentes.

QUÉ DICE LA GUÍA:
- Los agentes con tools fuera de su especialización tienden a malusarlas; por ejemplo,
  un agente de síntesis que intenta hacer búsquedas (2.3-K2).
- El acceso acotado da a cada agente solo las tools de su rol, más unas pocas tools
  *cross-role* muy limitadas para las necesidades de alta frecuencia (2.3-K3).
- Cada subagente recibe solo las tools relevantes para su rol (2.3-S1).
- Una tool genérica se sustituye por una restringida: `fetch_url` por `load_document`,
  que valida que la URL sea de un documento (2.3-S2).
- Una tool cross-role acotada, como `verify_fact` en el agente de síntesis, cubre las
  verificaciones simples (en la guía, el 85 %); los casos complejos se enrutan por el
  coordinador (2.3-S3).

POR QUÉ IMPORTA (inferencia propia): lo que un subagente puede hacer lo decide su lista de
tools, no su prompt. Con todas las tools, el prompt «solo sintetiza» es una petición, no
una barrera; con las suyas, la barrera es la configuración. Y la tool cross-role evita que
cada comprobación trivial dé una vuelta completa por el coordinador.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: el sintetizador con todas las tools, que se pone a buscar
  (`--anti todas`); la tool genérica `fetch_url` en lugar de la que valida
  (`--anti fetch_url`); y ninguna tool cross-role, de modo que cada verificación simple
  pasa por el coordinador (`--anti sin_verify`).
- Inferencias propias: la respuesta tentadora a «el sintetizador busca de más» es reforzar
  el prompt («no busques»), no quitar la tool. Y dar `verify_fact` también al coordinador
  o fusionar investigador y sintetizador son vías que la guía no propone.
- Guía frente a producto: la guía llama `Task` a la tool de subagentes; en el producto es
  `Agent`. Un subagente no hereda el contexto: solo sabe lo que el coordinador le pase.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 03.

INTRODUCE: TS 2.3-K2, TS 2.3-K3, TS 2.3-S1, TS 2.3-S2, TS 2.3-S3

Uso: `uv run python app3_sistema_multiagente/03_tools_entre_roles.py [--anti todas|fetch_url|sin_verify] [--repeat N]`
"""

import asyncio
import json
import sys
from pathlib import Path

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query  # noqa: E402

from app3_sistema_multiagente.servers.investigacion import SERVER_NAME, build_server, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import SUBAGENT_TOOLS, RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["todas", "fetch_url", "sin_verify"]
SEARCH_TICKETS = tool_name("search_tickets")
SEARCH_KB = tool_name("search_kb")
FETCH_URL = tool_name("fetch_url")
LOAD_DOCUMENT = tool_name("load_document")
VERIFY_FACT = tool_name("verify_fact")
ALL_TOOLS = [SEARCH_TICKETS, SEARCH_KB, FETCH_URL, LOAD_DOCUMENT, VERIFY_FACT]
MAIN = "principal"
ENROUTE = "enrutar al coordinador"

CATALOG = load("documentos.json")
NON_DOCUMENT_URLS = {u["url"] for u in CATALOG["urls"] if not u["is_document"]}

# Petición del usuario: unas URLs que son documentos y otras que no, y cinco afirmaciones, tres simples
# (un artículo) y dos complejas (varios artículos).
REQUEST = (
    "Prepara un informe breve sobre reembolsos y licencias de la mesa de ayuda con el contenido de los documentos "
    "de estas URLs:\n"
    + "\n".join(f"- {u['url']}" for u in CATALOG["urls"])
    + "\nDespués verifica estas afirmaciones e indica si cada una es cierta:\n"
    + "\n".join(f"- {c['claim_id']}: {c['text']}" for c in CATALOG["afirmaciones"])
)

# --- Tools por rol (2.3-S1) ---------------------------------------------------------------


def role_tools(anti: str | None) -> dict[str, list[str]]:
    """Tools de cada subagente según la variante. La configuración correcta es la de `anti=None`."""
    researcher = [SEARCH_KB, LOAD_DOCUMENT]  # busca y carga documentos: nada más
    synthesizer = [VERIFY_FACT]  # solo la tool cross-role acotada (2.3-S3)
    if anti == "todas":
        synthesizer = list(ALL_TOOLS)  # anti-patrón (2.3-K2): el sintetizador ve todas las tools
    if anti == "fetch_url":
        researcher = [SEARCH_KB, FETCH_URL]  # anti-patrón (2.3-S2): la genérica en vez de la que valida
    if anti == "sin_verify":
        synthesizer = []  # anti-patrón (2.3-S3): sin tool acotada, cada verificación vuelve al coordinador
    return {"researcher": researcher, "synthesizer": synthesizer}


# Lo que cada rol debería llamar con la configuración correcta: la vara para contar llamadas fuera de rol.
EXPECTED = {**role_tools(None), MAIN: ["Agent"]}

SUBAGENT_PROMPTS = {
    "researcher": (
        "Eres el investigador. Reúne con tus tools lo que te pida el coordinador: artículos de la base de conocimiento "
        "y el contenido de las URLs que te indique. Devuelve cada hallazgo con su fuente (article_id o URL). "
        "No redactes el informe ni verifiques afirmaciones."
    ),
    "synthesizer": (
        "Eres el sintetizador. Redactas el informe con los hallazgos que vengan en tu prompt y verificas las "
        "afirmaciones que te pida el coordinador con las tools que tengas. Solo cuentas con lo que viene en tu "
        "prompt. Si una afirmación no se puede verificar con tus tools, dilo y devuélvesela al coordinador."
    ),
}
SUBAGENT_DESCRIPTIONS = {
    "researcher": "Reúne artículos de la base de conocimiento y el contenido de documentos. Úsalo para obtener hallazgos.",
    "synthesizer": "Redacta el informe a partir de los hallazgos que le pases y verifica afirmaciones.",
}


def build_agents(anti: str | None, subagent_model: str) -> dict[str, AgentDefinition]:
    """`AgentDefinition` de cada subagente con solo las tools de su rol (2.3-S1)."""
    tools = role_tools(anti)
    return {
        name: AgentDefinition(
            description=SUBAGENT_DESCRIPTIONS[name],
            prompt=SUBAGENT_PROMPTS[name],
            tools=tools[name],
            model=subagent_model,
            background=False,  # en primer plano: el coordinador necesita el resultado (regla 4)
        )
        for name in SUBAGENT_PROMPTS
    }


def coordinator_prompt() -> str:
    # No nombra las tools ni dice cuál va a quién: el reparto es lo que se mide.
    return (
        "Objetivo: entregar el informe pedido y la verificación de cada afirmación. Dispones de dos subagentes, "
        "researcher y synthesizer. Los subagentes no ven esta conversación ni se hablan entre sí: todo pasa por ti, y cada "
        "uno solo sabe lo que pongas en su prompt. No busques ni verifiques tú con tools: delega. Si un subagente te "
        "devuelve que una afirmación debe resolverla el coordinador, resuélvela tú con los hallazgos que ya tengas o "
        "pidiéndoselos al investigador."
    )


def build_options(anti: str | None, *, budget: float, model: str, subagent_model: str) -> ClaudeAgentOptions:
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=coordinator_prompt(),
        mcp_servers={SERVER_NAME: build_server(extended=True)},
        tools=["Agent"],  # solo la tool integrada que lanza subagentes (la guía la llama "Task")
        # Se pre-aprueban todas las tools MCP: cada subagente solo ve las de su `AgentDefinition`.
        allowed_tools=["Agent", *ALL_TOOLS],
        permission_mode="dontAsk",
        agents=build_agents(anti, subagent_model),
        env={
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",  # coste acotado: un subagente no lanza otros
            "CLAUDE_CODE_FORK_SUBAGENT": "0",  # sin fork: la lección es que el subagente no hereda contexto
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",  # primer plano (CLI 2.1.309, ver app3/01)
        },
        max_turns=25,  # red de seguridad
    )


# --- Medidas sobre el RunRecord ---------------------------------------------------------------


def out_of_role(rec: RunRecord) -> dict[str, int]:
    """Llamadas a tools que el rol no tiene en la configuración correcta, por agente."""
    counts: dict[str, int] = {}
    for call in rec.tool_calls:
        expected = EXPECTED.get(call.agent)
        if expected is not None and call.name not in expected:
            counts[call.agent] = counts.get(call.agent, 0) + 1
    return counts


def junk_urls_fetched(rec: RunRecord) -> int:
    """`fetch_url` sobre URLs que no son documentos y que respondió: páginas de login o seguimiento en los hallazgos."""
    return sum(
        1 for c in rec.tool_calls
        if c.name == FETCH_URL and not c.is_error and c.input.get("url") in NON_DOCUMENT_URLS
    )


def rejected_loads(rec: RunRecord) -> int:
    """`load_document` que rechazó una URL no documento con un error de validación: la tool restringida funcionando."""
    return sum(1 for c in rec.tool_calls if c.name == LOAD_DOCUMENT and c.is_error)


def delegations(rec: RunRecord) -> dict[str, int]:
    counts: dict[str, int] = {}
    for call in rec.tool_calls:
        if call.name in SUBAGENT_TOOLS:
            kind = call.input.get("subagent_type", "?")
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def total_delegations(rec: RunRecord) -> int:
    return sum(delegations(rec).values())


def verify_calls(rec: RunRecord) -> int:
    return sum(1 for c in rec.tool_calls if c.name == VERIFY_FACT)


def routed_to_coordinator(rec: RunRecord) -> int:
    """Verificaciones que `verify_fact` devolvió al coordinador por ser complejas."""
    return sum(1 for c in rec.tool_calls if c.name == VERIFY_FACT and ENROUTE in (c.result_text or ""))


# --- Ejecución -----------------------------------------------------------------------------------


def expectation(anti: str | None) -> str:
    return {
        None: "sin llamadas fuera de rol, 0 URLs basura, verify_fact en el sintetizador y las 2 complejas devueltas al coordinador",
        "todas": "el sintetizador, con todas las tools, se pone a buscar: llamadas fuera de rol",
        "fetch_url": "el investigador abre páginas que no son documentos y las mete en los hallazgos",
        "sin_verify": "más delegaciones: cada verificación simple da una vuelta por el coordinador",
    }[anti]


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("coordinator")
    subagent_model = report_model("subagent")
    budget = report_budget(args.budget, "multiagent")

    for run in range(1, args.repeat + 1):
        # El tope es de toda la ejecución del script, repartido entre repeticiones.
        options = build_options(args.anti, budget=budget / args.repeat, model=model, subagent_model=subagent_model)
        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'correcta'} ===")
        print(f"[esperado] {expectation(args.anti)}")
        rec = await record(query(prompt=REQUEST, options=options))
        print(f"[medida] llamadas por agente: { {a: len(c) for a, c in rec.by_agent().items()} }")
        print(f"[medida] fuera de rol: {out_of_role(rec) or 'ninguna'}")
        print(f"[medida] URLs no documento abiertas con fetch_url: {junk_urls_fetched(rec)} · rechazadas por load_document: {rejected_loads(rec)}")
        print(f"[medida] delegaciones: {delegations(rec)} (total {total_delegations(rec)})")
        print(f"[medida] verify_fact: {verify_calls(rec)} llamadas · devueltas al coordinador por complejas: {routed_to_coordinator(rec)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
