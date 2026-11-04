"""Errores entre agentes: contexto estructurado del fallo, resultado parcial y vacío frente a fallo.

CONCEPTO [TS 5.3-K1…K4, S1…S4 · TS 2.2-S3]: qué debe devolver un subagente cuando
una fuente falla, y qué puede hacer el coordinador con lo que recibe: recuperar,
entregar un resultado parcial con la brecha anotada o, si no sabe nada, equivocarse.

QUÉ DICE LA GUÍA:
- El coordinador decide bien la recuperación si el error le llega con contexto: tipo
  de fallo, la consulta que se intentó, los resultados parciales y las alternativas
  posibles (5.3-K1). El subagente devuelve ese contexto estructurado (5.3-S1).
- Un fallo de acceso (un *timeout* que pide decidir si reintentar) no es un resultado
  vacío válido (una consulta que funcionó y no encontró nada) (5.3-K2). El informe
  del subagente los distingue para que el coordinador decida lo adecuado en cada
  caso (5.3-S2).
- Un estado de error genérico («búsqueda no disponible») le esconde al coordinador
  justo el contexto que necesitaba (5.3-K3).
- Hay dos anti-patrones opuestos: suprimir el error en silencio, devolviendo un vacío
  como si fuera un éxito, y terminar todo el flujo por un solo fallo (5.3-K4).
- El subagente recupera en local los fallos transitorios y solo propaga los que no
  puede resolver, junto con lo que intentó y lo que sí obtuvo (5.3-S3, 2.2-S3).
- La síntesis anota la cobertura: qué hallazgos están bien respaldados y qué temas
  quedan con huecos porque una fuente no estuvo disponible (5.3-S4).

POR QUÉ IMPORTA (inferencia propia): lo que el coordinador sabe de una fuente es lo
que el subagente le cuenta. Un vacío falso convierte un fallo en una conclusión
falsa («no hay datos»), un aborto tira el trabajo de las fuentes que sí respondieron
y un resultado parcial sin la brecha anotada se lee como completo.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Devolver un error genérico sin contexto (`--anti generico`).
  - Devolver un vacío como éxito cuando la fuente ha fallado (`--anti silenciar`).
  - Abortar toda la investigación por una fuente que falla (`--anti abortar`).
  - Confundir un fallo de acceso con un resultado vacío, en cualquiera de los dos
    sentidos.
- Inferencias propias, con lo observado aquí (cifras en el README y en
  `docs/hallazgos.md`):
  - Sin contexto, el coordinador repitió a ciegas la delegación que el subagente ya
    había reintentado (`generico`). El error genérico no impide anotar la brecha;
    impide decidir bien qué hacer con ella.
  - El vacío falso solo engaña si lo produce el código. Cuando se lo pedía el prompt
    del subagente, el coordinador le pidió en la delegación «si una fuente falla, dilo»
    y la brecha llegó igual al resultado. Con el *handler* tragándose el fallo, el
    subagente no lo ve y el informe final afirma algo falso («no dio error»).
  - Reforzar el prompt del coordinador («comprueba que no falte nada») no arregla un
    fallo que se ha perdido en el origen.
- Los errores de la tool siguen el formato de `app1/04` (`errorCategory`,
  `isRetryable`); aquí lo nuevo es qué hace el subagente con ellos.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 04.

INTRODUCE: TS 5.3-K1, TS 5.3-K2, TS 5.3-K3, TS 5.3-K4, TS 5.3-S1, TS 5.3-S2, TS 5.3-S3, TS 5.3-S4, TS 2.2-S3

Uso: `uv run python app3_sistema_multiagente/04_errores_entre_agentes.py [--anti generico|silenciar|abortar] [--repeat N]`
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query  # noqa: E402

from app3_sistema_multiagente.coordinator_gate import coordinator_attempts, coordinator_gate, coordinator_hooks  # noqa: E402, F401
from app3_sistema_multiagente.servers.investigacion import SERVER_NAME, build_server, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import MAIN, SUBAGENT_TOOLS, RunRecord, ToolCall, record  # noqa: E402

ANTI_VARIANTS = ["generico", "silenciar", "abortar"]
QUERY_SOURCE = tool_name("query_source")
MAX_LOCAL_RETRIES = 2  # reintentos locales del subagente ante un error transitorio
ABORT_MARKER = "INVESTIGACIÓN ABORTADA"
GENERIC_MESSAGE = "búsqueda no disponible"  # el estado de error genérico de la variante `generico`
CONTEXT_KEYS = ("failure_type", "attempted", "partial_results", "alternatives")
ALTERNATIVE_WORDS = re.compile(r"alternativ|más tarde|reintent|volver a intentar|pedir|solicitar|contactar|otra fuente", re.I)
GAP_WORDS = re.compile(r"no se pudo|no pudo|no respond|timeout|fall[óo]|fallo|sin cubrir|sin cobertura|falta|no disponible|brecha|no se obtuvo", re.I)

LABELS = load("fuentes_investigacion_etiquetas.json")
SOURCES = {s["source_id"]: s for s in load("fuentes_investigacion.json")}
# Cinco fuentes de la lista: tres sanas, una vacía de forma legítima y una que falla por timeout.
REQUESTED = ["SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA", "SRC-MONITOR", "SRC-ARCHIVO"]

REQUEST = (
    "Prepara un informe sobre la calidad del servicio de la mesa de ayuda en el tercer trimestre con lo que digan "
    "estas fuentes:\n" + "\n".join(f"- {sid}: {SOURCES[sid]['name']}" for sid in REQUESTED)
)

# --- Subagente y coordinador ---------------------------------------------------------------------

REPORT_FORMAT = (
    "Devuelve, por cada fuente que consultes, un objeto JSON: "
    '{"source_id": …, "status": …, "findings": [{"claim": …, "figure": …}]'
)


def silences_failures(anti: str | None) -> bool:
    """`silenciar` lo hace el servidor: el handler devuelve `[]` como éxito cuando la fuente falla."""
    return anti == "silenciar"


def researcher_prompt(anti: str | None) -> str:
    """Prompt del investigador. `generico` le hace devolver un fallo sin contexto; `silenciar` no cambia el prompt."""
    if anti == "generico":
        return (
            "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador. "
            f"{REPORT_FORMAT}" + ', "message": …}. status es "ok" si hay contenido, "empty" si la fuente responde pero no '
            'tiene nada y "failed" si no responde. Si una consulta falla, no reintentes y no des detalles: devuelve para '
            f'esa fuente status "failed" y message "{GENERIC_MESSAGE}", sin ningún otro campo.'
        )
    return (
        "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador. "
        f"{REPORT_FORMAT}"
        ', "error_context": …}. status es "ok" si hay contenido, "empty" si la fuente responde pero no tiene nada '
        '(un vacío legítimo, no un fallo) y "failed" si no responde. '
        f"Si una consulta falla con un error reintentable, reintenta hasta {MAX_LOCAL_RETRIES} veces. Si sigue fallando, "
        'devuelve status "failed" y en error_context: failure_type (la categoría del error), attempted (qué consultas '
        "hiciste), partial_results (lo que sí obtuviste de esa fuente, o una lista vacía) y alternatives (qué podría "
        "hacerse para cubrir la brecha). No inventes contenido de una fuente que no respondió."
    )


def build_agents(anti: str | None, subagent_model: str) -> dict[str, AgentDefinition]:
    return {
        "researcher": AgentDefinition(
            description="Consulta fuentes de la investigación y devuelve un informe estructurado por fuente, con su estado.",
            prompt=researcher_prompt(anti),
            tools=[QUERY_SOURCE],
            model=subagent_model,
            background=False,  # en primer plano: el coordinador necesita el resultado (regla 4)
        )
    }


def coordinator_prompt(anti: str | None) -> str:
    """Objetivos y criterios, no pasos (1.3-S4). La variante `abortar` añade la regla de tirar todo ante un fallo."""
    prompt = (
        "Objetivo: entregar el informe pedido con la cobertura de cada fuente de la lista. Criterios de calidad: cada "
        "afirmación lleva su fuente; lo que no se pudo cubrir se dice (qué fuente, por qué y qué alternativas hay) en vez de "
        "darlo por vacío ni por cubierto; un resultado parcial con la brecha anotada es válido. Dispones de un subagente, "
        "researcher, que consulta las fuentes. No ve esta conversación: pásale en el prompt las fuentes que debe consultar. "
        "No busques tú: delega."
    )
    if anti == "abortar":
        prompt += f" Si alguna fuente falla, la investigación entera no es válida: no entregues nada parcial y responde solo «{ABORT_MARKER}»."
    return prompt


def build_options(anti: str | None, *, budget: float, model: str, subagent_model: str) -> ClaudeAgentOptions:
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=coordinator_prompt(anti),
        mcp_servers={SERVER_NAME: build_server(sources=True, silence_failures=silences_failures(anti))},
        tools=["Agent"],  # solo la tool integrada que lanza subagentes (la guía la llama "Task")
        allowed_tools=["Agent", QUERY_SOURCE],  # query_source la usa el subagente; al coordinador se la deniega la barrera
        permission_mode="dontAsk",
        agents=build_agents(anti, subagent_model),
        hooks=coordinator_hooks(),
        env={
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",  # coste acotado: un subagente no lanza otros
            "CLAUDE_CODE_FORK_SUBAGENT": "0",  # sin fork: el subagente no hereda el contexto
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",  # primer plano (CLI 2.1.309, ver app3/01)
        },
        max_turns=20,  # red de seguridad
    )


# --- Medidas sobre el RunRecord (sin modelo) -----------------------------------------------------


def classify_result(call: ToolCall) -> str:
    """`failure` (transitorio), `invalid` (otro error), `empty` (vacío legítimo) o `data`."""
    try:
        data = json.loads(call.result_text or "{}")
    except json.JSONDecodeError:
        data = {}
    if call.is_error:
        return "failure" if data.get("errorCategory") == "transient" else "invalid"
    return "empty" if data.get("total") == 0 else "data"


def attempts_by_source(rec: RunRecord) -> dict[str, list[ToolCall]]:
    attempts: dict[str, list[ToolCall]] = {}
    for call in rec.tool_calls:
        if call.name == QUERY_SOURCE:
            attempts.setdefault(call.input.get("source_id", "?"), []).append(call)
    return attempts


def local_retries(rec: RunRecord) -> dict[str, int]:
    """Consultas repetidas por fuente: el reintento local del subagente (no es un fallo de la ejecución)."""
    return {sid: len(calls) - 1 for sid, calls in attempts_by_source(rec).items()}


def sources_ending_as(rec: RunRecord, kind: str) -> list[str]:
    """Fuentes cuya última consulta terminó así: una recuperada en un reintento no cuenta como fallida."""
    return [sid for sid, calls in attempts_by_source(rec).items() if classify_result(calls[-1]) == kind]


def failed_sources(rec: RunRecord) -> list[str]:
    return sources_ending_as(rec, "failure")


def empty_sources(rec: RunRecord) -> list[str]:
    return sources_ending_as(rec, "empty")


def coordinator_errors(rec: RunRecord) -> int:
    """Errores en llamadas del propio coordinador (las del subagente, incluido su reintento, no cuentan)."""
    return sum(1 for c in rec.tool_calls if c.agent == MAIN and c.name not in SUBAGENT_TOOLS and c.is_error)


def subagent_reports(rec: RunRecord) -> list[dict[str, Any]]:
    """Informes JSON (con `source_id`) que el investigador devolvió al coordinador, sacados de entre su prosa."""
    reports: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    for call in rec.tool_calls:
        if call.name not in SUBAGENT_TOOLS or not call.result_text:
            continue
        text, pos = call.result_text, 0
        while pos < len(text):
            if text[pos] not in "{[":
                pos += 1
                continue
            try:
                value, end = decoder.raw_decode(text, pos)
            except json.JSONDecodeError:
                pos += 1
                continue
            pos = end
            items = value if isinstance(value, list) else [value]
            reports += [i for i in items if isinstance(i, dict) and "source_id" in i]
    return reports


def error_context_problems(report: dict[str, Any]) -> list[str]:
    """Qué le falta al informe de una fuente fallida para que el coordinador pueda decidir."""
    if report.get("status") != "failed":
        return ["status no es failed"]
    context = report.get("error_context")
    if not isinstance(context, dict):
        return ["falta error_context"]
    problems = [f"falta {key}" for key in CONTEXT_KEYS if key not in context]
    if "attempted" in context and not context["attempted"]:
        problems.append("attempted vacío: no dice qué se intentó")
    return problems


def final_report_of(rec: RunRecord, source_id: str) -> dict[str, Any] | None:
    found = [r for r in subagent_reports(rec) if r.get("source_id") == source_id]
    return found[-1] if found else None


def swallowed_sources(rec: RunRecord) -> list[str]:
    """Fuentes etiquetadas como fallidas cuyo resultado no pareció un fallo: el handler las tragó (`silenciar`)."""
    return [
        sid for sid, calls in attempts_by_source(rec).items()
        if sid in LABELS["failed_sources"] and classify_result(calls[-1]) != "failure"
    ]


def coordinator_delegations(rec: RunRecord) -> int:
    """Delegaciones del coordinador al subagente: más de una es que volvió a delegar (reintento o alternativa)."""
    return sum(1 for c in rec.tool_calls if c.agent == MAIN and c.name in SUBAGENT_TOOLS)


def alternatives_mentioned(text: str | None) -> bool:
    """¿Dice el texto cómo cubrir la brecha (alternativa, reintentar más tarde, pedir el dato)? Comprobación laxa."""
    return bool(ALTERNATIVE_WORDS.search(text or ""))


def silenced_sources(rec: RunRecord) -> list[str]:
    """Fuentes que fallaron y de las que el investigador no informó como fallidas (las dio por vacías o por cubiertas)."""
    silenced = []
    for sid in failed_sources(rec):
        report = final_report_of(rec, sid)
        if report is None or report.get("status") != "failed":
            silenced.append(sid)
    return silenced


def empty_reported_as_failed(rec: RunRecord) -> list[str]:
    """Fuentes que respondieron vacías de forma legítima y que el investigador marcó como fallo."""
    return [sid for sid in empty_sources(rec) if (final_report_of(rec, sid) or {}).get("status") == "failed"]


def coverage_of(reports: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Cobertura por estado según los informes (el último informe de cada fuente manda)."""
    last = {r["source_id"]: r.get("status") for r in reports}
    return {
        "covered": [s for s, st in last.items() if st == "ok"],
        "empty": [s for s, st in last.items() if st == "empty"],
        "gap": [s for s, st in last.items() if st == "failed"],
    }


def gap_noted(text: str | None, source_id: str, name: str) -> bool:
    """¿Dice el texto, en una misma frase, qué fuente falta (por id o nombre) y que falta?"""
    for sentence in re.split(r"[.;\n]", (text or "").lower()):
        if (source_id.lower() in sentence or name.lower() in sentence) and GAP_WORDS.search(sentence):
            return True
    return False


def healthy_figures() -> list[str]:
    """Cifras de las fuentes que sí responden, sin unidad (`18 horas` → `18`)."""
    figures = [LABELS["established"]["figure_text"]]
    figures += [claim["figure_text"].split()[0] for conflict in LABELS["conflicts"] for claim in conflict["claims"]]
    return figures


def aborted(text: str | None) -> bool:
    return ABORT_MARKER in (text or "")


def partial_delivered(text: str | None) -> bool:
    """¿Entrega cifras de las fuentes sanas y no es un aborto?"""
    if not text or aborted(text):
        return False
    return any(re.search(rf"(?<![\d.,]){re.escape(f)}(?![\d.,]\d)", text) for f in healthy_figures())


# --- Ejecución -----------------------------------------------------------------------------------


def expectation(anti: str | None) -> str:
    return {
        None: "reintento local en la fuente que falla, informe `failed` con su contexto, vacío legítimo como `empty` y resultado parcial con la brecha anotada",
        "generico": "el subagente devuelve `failed` sin contexto: el coordinador no sabe qué se intentó ni qué alternativas hay, y decide a ciegas (reintentar, buscar otra vía o solo anotar)",
        "silenciar": "el handler traga el fallo y devuelve `[]` como éxito: ni el subagente ni el coordinador pueden saber que la fuente falló, y la brecha no se anota",
        "abortar": "un fallo tumba la investigación: sin resultado parcial, aunque otras fuentes respondieron",
    }[anti]


def print_measures(rec: RunRecord) -> None:
    failed = [s for s in failed_sources(rec)]
    print(f"[medida] consultas por fuente: { {s: len(c) for s, c in attempts_by_source(rec).items()} } · reintentos locales: {local_retries(rec)}")
    print(f"[medida] fuentes que terminaron en fallo: {failed} · vacías legítimas: {empty_sources(rec)} · errores del coordinador: {coordinator_errors(rec)}")
    reports = subagent_reports(rec)
    print(f"[medida] cobertura según los informes del subagente: {coverage_of(reports)}")
    for sid in failed:
        report = final_report_of(rec, sid)
        problems = error_context_problems(report) if report else ["sin informe de esa fuente"]
        print(f"[medida] contexto de error de {sid}: {'completo' if not problems else problems}")
    print(f"[medida] fuentes silenciadas: {silenced_sources(rec)} · vacío marcado como fallo: {empty_reported_as_failed(rec)}")
    print(f"[medida] fallos tragados por el handler (llegaron como vacío): {swallowed_sources(rec)}")
    # La brecha se mide sobre las fuentes etiquetadas como fallidas, incluso si el handler las tragó.
    for sid in LABELS["failed_sources"]:
        print(f"[medida] brecha de {sid} anotada en el resultado: {gap_noted(rec.final_text, sid, SOURCES[sid]['name'])}")
    queries_to_failing = sum(len(attempts_by_source(rec).get(sid, [])) for sid in LABELS["failed_sources"])
    print(
        f"[medida] decisiones del coordinador: delegaciones {coordinator_delegations(rec)} · consultas a la fuente que falla "
        f"{queries_to_failing} · alternativa o reintento mencionados en el resultado: {alternatives_mentioned(rec.final_text)}"
    )
    print(f"[medida] resultado parcial con cifras de las fuentes sanas: {partial_delivered(rec.final_text)} · abortado: {aborted(rec.final_text)}")


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
        print(f"[respuesta completa]\n{rec.final_text}")
        print(f"[medida] intentos del coordinador con tools de fuentes, denegados: {coordinator_attempts(rec)}")
        print_measures(rec)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
