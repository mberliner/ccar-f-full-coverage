"""Coordinador con subagentes: hub-and-spoke, contexto explícito y selección dinámica.

CONCEPTO [TS 1.2-K1, K2, K3, K4, S1, S2, S4 · TS 1.3-K1, K2, K3, S1, S4]:
orquestación coordinador-subagente e invocación de subagentes.

QUÉ DICE LA GUÍA:
- Arquitectura hub-and-spoke: el coordinador gestiona toda la comunicación
  entre subagentes, el manejo de errores y el enrutado de la información
  (1.2-K1); toda la comunicación pasa por él, por observabilidad, manejo de
  errores coherente y flujo de información controlado (1.2-S4).
- Los subagentes trabajan con contexto aislado: no heredan automáticamente el
  historial del coordinador (1.2-K2). Su contexto hay que dárselo de forma
  explícita en el prompt, y no comparten memoria entre invocaciones (1.3-K2).
- El coordinador descompone, delega, agrega resultados y decide qué
  subagentes invocar según la complejidad de la consulta (1.2-K3); analiza la
  consulta y elige de forma dinámica en vez de pasar siempre por todo el
  pipeline (1.2-S1).
- Una descomposición demasiado estrecha deja sin cubrir partes de un tema
  amplio (1.2-K4). El alcance se reparte entre subagentes para no duplicar
  trabajo, por ejemplo con subtemas o tipos de fuente distintos (1.2-S2).
- La tool Task es el mecanismo para lanzar subagentes y `allowedTools` del
  coordinador tiene que incluir "Task" (1.3-K1). Cada tipo de subagente se
  configura con `AgentDefinition`: descripción, *system prompt* y
  restricciones de tools (1.3-K3).
- Los hallazgos completos de los agentes previos se incluyen en el prompt del
  subagente siguiente (1.3-S1), y el prompt del coordinador fija objetivos y
  criterios de calidad, no pasos (1.3-S4).

POR QUÉ IMPORTA: el sintetizador no «ve» lo que encontraron los analistas.
Si el coordinador no se lo pega en el prompt, sintetiza sobre nada; y si el
coordinador estrecha la pregunta, ningún subagente puede recuperar lo que
nunca se le pidió.

ANTI-PATRÓN / TRAMPA DEL EXAMEN: suponer que el subagente hereda el contexto;
pasar siempre por todos los subagentes; reducir «problemas de red» a «VPN»
(la causa de una cobertura incompleta está en la descomposición del
coordinador, no en los subagentes); y escribir el prompt del coordinador como
una receta de pasos.

Guía frente a producto: la guía llama `Task` a la tool; en el producto se llama
`Agent` y es la que se pone en `allowed_tools` (el recorder acepta las dos).

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 01.

INTRODUCE: TS 1.2-K1, TS 1.2-K2, TS 1.2-K3, TS 1.2-K4, TS 1.2-S1, TS 1.2-S2, TS 1.2-S4, TS 1.3-K1, TS 1.3-K2, TS 1.3-K3, TS 1.3-S1, TS 1.3-S4

Uso: `uv run python app3_sistema_multiagente/01_coordinador.py [--pregunta amplia|simple] [--anti pipeline_completo|estrecha|sin_hallazgos|procedimental]`
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query  # noqa: E402

from app3_sistema_multiagente.servers.investigacion import (  # noqa: E402
    NETWORK_SUBTOPICS,
    SERVER_NAME,
    build_server,
    tool_name,
)
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import SUBAGENT_TOOLS, RunRecord, record  # noqa: E402

SEARCH_TICKETS = tool_name("search_tickets")
SEARCH_KB = tool_name("search_kb")
ANTI_VARIANTS = ["pipeline_completo", "estrecha", "sin_hallazgos", "procedimental"]
QUESTIONS = {
    "amplia": "¿Qué problemas de red están teniendo los empleados y qué dice la base de conocimiento de cada uno?",
    "simple": "¿Qué dice el artículo KB-109?",
}
# Subtemas de «problemas de red» en los datos: la variante estrecha pierde la wifi.
SUBTOPICS = NETWORK_SUBTOPICS
ID_RE = re.compile(r"\b(?:TCK|KB)-\d+\b")

# Reparto del alcance por tipo de fuente (1.2-S2): un analista por tool.
SUBAGENT_PROMPTS = {
    "tickets_analyst": (
        "Eres el analista de tickets. Busca con search_tickets lo que te pida el coordinador (puedes hacer "
        "varias búsquedas) y devuelve cada hallazgo con su texto y sus metadatos (ticket_id, estado y fecha). "
        "No interpretes la base de conocimiento: no la ves."
    ),
    "kb_analyst": (
        "Eres el analista de la base de conocimiento. Busca con search_kb lo que te pida el coordinador y "
        "devuelve cada artículo con su resumen y sus metadatos (article_id, updated_at y superseded_by si lo hay)."
    ),
    "synthesizer": (
        "Eres el sintetizador. Solo trabajas con lo que viene en tu prompt: no tienes tools ni ves otras "
        "conversaciones. Responde a la pregunta con un apartado por subtema, citando cada afirmación con su "
        "ticket_id o article_id y su fecha. Si un artículo está sustituido, dilo. Si no recibes hallazgos, dilo."
    ),
}
SUBAGENT_DESCRIPTIONS = {
    "tickets_analyst": "Busca en los tickets de la mesa de ayuda. Úsalo para saber qué les pasa a los empleados.",
    "kb_analyst": "Busca en la base de conocimiento. Úsalo para saber qué solución documentada hay.",
    "synthesizer": "Redacta la respuesta final a partir de los hallazgos que le pases en el prompt.",
}
SUBAGENT_TOOLS_BY_NAME = {"tickets_analyst": [SEARCH_TICKETS], "kb_analyst": [SEARCH_KB], "synthesizer": []}


def build_agents(subagent_model: str) -> dict[str, AgentDefinition]:
    """`AgentDefinition` de cada subagente: descripción, prompt y solo sus tools (1.3-K3)."""
    return {
        name: AgentDefinition(
            description=SUBAGENT_DESCRIPTIONS[name],
            prompt=SUBAGENT_PROMPTS[name],
            tools=SUBAGENT_TOOLS_BY_NAME[name],
            model=subagent_model,
            # En primer plano (roadmap §3, regla 4): en segundo plano el
            # coordinador seguiría sin esperar el resultado. No basta por sí
            # solo: ver CLAUDE_CODE_DISABLE_BACKGROUND_TASKS en build_options.
            background=False,
        )
        for name in SUBAGENT_PROMPTS
    }


def synthesizer_prompt(question: str, findings: list[dict[str, Any]]) -> str:
    """Prompt del sintetizador: la pregunta y todos los hallazgos, con el contenido separado de los metadatos."""
    lines = [f"Pregunta: {question}", "", "HALLAZGOS (completos; cita por ID y fecha):"]
    for number, finding in enumerate(findings, start=1):
        meta = ", ".join(f"{k}={v}" for k, v in finding["metadata"].items())
        lines.append(f"{number}. [{finding['source']}] {finding['content']}  ({meta})")
    return "\n".join(lines)


TEMPLATE = synthesizer_prompt(
    "<pregunta>",
    [{"source": "tickets_analyst", "content": "<texto del hallazgo>", "metadata": {"ticket_id": "TCK-…", "created_at": "…"}}],
)

GOALS = (
    "Objetivo: responder a la pregunta del usuario con cobertura completa de todo su alcance, no solo del caso "
    "más obvio. Criterios de calidad: cada afirmación lleva su fuente (ticket_id o article_id) y su fecha; se "
    "señalan los artículos obsoletos; nada se afirma sin un hallazgo que lo respalde.\n"
    "Dispones de tres subagentes y decides cuáles necesitas según la pregunta: no invoques a los que no aporten. "
    "Los subagentes no ven esta conversación ni se hablan entre sí: todo pasa por ti, y cada uno solo sabe lo que "
    "pongas en su prompt. No busques tú: delega las búsquedas."
)
SYNTH_RULE = (
    "Si usas el sintetizador, pégale en el prompt la pregunta y todos los hallazgos completos con sus metadatos, "
    f"con este formato:\n{TEMPLATE}"
)


def coordinator_prompt(anti: str | None) -> str:
    """Prompt del coordinador según la variante."""
    if anti == "procedimental":
        # Receta de pasos en vez de objetivos (anti de 1.3-S4).
        return (
            "Sigue estos pasos sin desviarte. Paso 1: llama a tickets_analyst con la consulta «VPN». Paso 2: llama "
            "a kb_analyst con la consulta «VPN». Paso 3: llama a synthesizer con la pregunta y lo que te hayan "
            "devuelto. Paso 4: devuelve la respuesta del sintetizador."
        )
    prompt = GOALS
    if anti == "pipeline_completo":
        prompt += "\nPara cualquier pregunta, invoca siempre a los tres subagentes, en este orden: tickets_analyst, kb_analyst y synthesizer."
    if anti == "estrecha":
        # Descomposición estrecha (anti de 1.2-K4): el coordinador da por hecho
        # que el tema amplio se reduce a su caso más conocido.
        prompt += (
            "\nEn esta empresa, «problemas de red» quiere decir casi siempre la VPN: delega la investigación "
            "en la VPN, con una sola consulta concreta por analista."
        )
    if anti == "sin_hallazgos":
        # El error de suponer que el subagente hereda el contexto (anti de 1.2-K2 y 1.3-S1).
        return prompt + "\nEl sintetizador ya ve lo que han encontrado los analistas: pásale solo la pregunta."
    return f"{prompt}\n{SYNTH_RULE}"


def build_options(*, anti: str | None, budget: float, model: str, subagent_model: str) -> ClaudeAgentOptions:
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=coordinator_prompt(anti),
        mcp_servers={SERVER_NAME: build_server()},
        # Solo la tool integrada que lanza subagentes (la guía la llama "Task").
        tools=["Agent"],
        # "Agent" pre-aprueba lanzar subagentes; las de búsqueda las usan ellos,
        # que heredan el modo de permisos del coordinador.
        allowed_tools=["Agent", SEARCH_TICKETS, SEARCH_KB],
        permission_mode="dontAsk",
        agents=build_agents(subagent_model),
        env={
            # Coste acotado (roadmap §3, regla 7): un subagente no lanza otros.
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
            # Sin subagentes fork, que heredarían el contexto del padre: la
            # lección es justo que el subagente no lo hereda (regla 4).
            "CLAUDE_CODE_FORK_SUBAGENT": "0",
            # Subagentes en primer plano: con CLI 2.1.309 se lanzaban en segundo
            # plano («Async agent launched») aunque la AgentDefinition dijera
            # background=False, y el coordinador seguía sin sus resultados.
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
        },
        max_turns=20,  # red de seguridad
    )


# --- Medidas sobre el RunRecord --------------------------------------------------


def invoked_agents(rec: RunRecord) -> list[str]:
    return [c.input.get("subagent_type", "?") for c in rec.tool_calls if c.name in SUBAGENT_TOOLS]


def findings_coverage(rec: RunRecord) -> dict[str, list[str]]:
    """IDs que encontraron los analistas frente a IDs que llegaron al prompt del sintetizador."""
    found: set[str] = set()
    for call in rec.tool_calls:
        if call.name in (SEARCH_TICKETS, SEARCH_KB) and call.result_text:
            found |= set(ID_RE.findall(call.result_text))
    synth = " ".join(
        c.input.get("prompt", "") for c in rec.tool_calls
        if c.name in SUBAGENT_TOOLS and c.input.get("subagent_type") == "synthesizer"
    )
    passed = found & set(ID_RE.findall(synth))
    return {"found": sorted(found), "passed": sorted(passed), "missing": sorted(found - passed)}


def subtopics_covered(text: str | None) -> dict[str, bool]:
    lowered = (text or "").lower()
    return {topic: any(w in lowered for w in words) for topic, words in SUBTOPICS.items()}


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--pregunta", choices=list(QUESTIONS), default="amplia")
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("coordinator")
    subagent_model = report_model("subagent")
    budget = report_budget(args.budget, "multiagent")

    question = QUESTIONS[args.pregunta]
    for run in range(1, args.repeat + 1):
        # El tope es de toda la ejecución del script, repartido entre repeticiones.
        options = build_options(anti=args.anti, budget=budget / args.repeat, model=model, subagent_model=subagent_model)
        print(f"\n=== ejecución {run}/{args.repeat} · variante {args.anti or 'correcta'} · pregunta {args.pregunta} ===")
        rec = await record(query(prompt=question, options=options))
        coverage = findings_coverage(rec)
        print(f"[respuesta completa]\n{rec.final_text}")
        print(f"[medida] subagentes invocados: {invoked_agents(rec)}")
        print(f"[medida] llamadas por agente: { {a: len(c) for a, c in rec.by_agent().items()} }")
        if "synthesizer" in invoked_agents(rec):
            print(f"[medida] hallazgos pasados al sintetizador: {len(coverage['passed'])}/{len(coverage['found'])}"
                  f" · faltan: {coverage['missing']}")
        else:
            print("[medida] sin sintetizador: el coordinador redactó la respuesta (selección dinámica)")
        print(f"[medida] subtemas en la respuesta: {subtopics_covered(rec.final_text)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
