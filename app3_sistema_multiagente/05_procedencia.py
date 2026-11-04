"""Procedencia entre agentes: afirmación y fuente juntas, cifras en conflicto sin fusionar y hallazgos en mitad de un texto largo.

CONCEPTO [TS 5.6-K1…K4, S1…S5 · TS 5.1-K2, S4, S5, S6 · TS 1.3-S2]: cómo llega la
procedencia de lo que encuentra un subagente hasta el informe final, y qué le pasa al
hallazgo clave cuando el texto es largo.

BORRADOR (texto pendiente del pase de Opus 5.5, ver NOTAS.md): este módulo se
escribió contra el diseño de la entrega 3 y no contra el texto de la guía. Las
viñetas se citan por Task Statement; el reparto exacto de cada K y S, y la
parte de `QUÉ DICE LA GUÍA`, se contrastan con la guía en ese pase.

QUÉ DICE LA GUÍA (según el diseño de la entrega; contrastar):
- Los subagentes devuelven datos estructurados (afirmación, fuente, fecha y cifra) con
  el contenido separado de los metadatos, y el sintetizador conserva el mapeo
  afirmación–fuente al combinar (1.3-S2, 5.6).
- Cuando dos fuentes dan cifras distintas para lo mismo, el informe las anota las dos
  con su fuente y su fecha; no promedia ni elige una sin decirlo. Separa lo establecido
  de lo disputado.
- El formato de la síntesis sigue al tipo de contenido (cifras comparables en tabla,
  lo cualitativo en prosa).
- *Lost in the middle* (5.1): un hallazgo clave en mitad de un texto largo se atiende
  peor que al principio o al final; poner un resumen de lo clave al principio lo mitiga.

POR QUÉ IMPORTA (inferencia propia): la procedencia no se reconstruye después. Si el
subagente devuelve prosa, la fuente de cada cifra se pierde en el primer salto; si el
sintetizador promedia, ninguna fuente respalda ya el número del informe.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- `--anti sin_procedencia`: los subagentes devuelven prosa y la síntesis no puede
  asociar cada cifra a su fuente.
- `--anti promedio`: el sintetizador fusiona las cifras en conflicto en una sola.
- `--parte medio --texto sin_resumen|con_resumen`: el mismo informe largo con el
  hallazgo clave en mitad frente al mismo informe con una línea de resumen al principio.
- Lo observado (ver README y `docs/hallazgos.md`) es lo que cuenta: si una señal no
  aparece con el modelo usado, se documenta tal cual.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 05.

INTRODUCE: TS 5.6-K1, TS 5.6-K2, TS 5.6-K3, TS 5.6-K4, TS 5.6-S1, TS 5.6-S2, TS 5.6-S3, TS 5.6-S4, TS 5.6-S5, TS 5.1-K2, TS 5.1-S4, TS 5.1-S5, TS 5.1-S6, TS 1.3-S2

Uso: `uv run python app3_sistema_multiagente/05_procedencia.py [--parte conflictos|medio] [--texto sin_resumen|con_resumen|con_encabezados|encabezados_y_resumen] [--anti sin_procedencia|promedio] [--repeat N]`
"""

import asyncio
import json
import re
import sys
from collections.abc import Iterator
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
from harness.recorder import SUBAGENT_TOOLS, RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["sin_procedencia", "promedio"]
PARTES = ["conflictos", "medio"]
TEXTOS = ["sin_resumen", "con_resumen", "con_encabezados", "encabezados_y_resumen"]
QUERY_SOURCE = tool_name("query_source")
METADATA_KEYS = ("source_id", "published_at", "date", "fecha", "url")
DISPUTE_WORDS = re.compile(r"difier|discrep|disput|conflict|contradic|no coincid|no concuerd", re.I)

LABELS = load("fuentes_investigacion_etiquetas.json")
SOURCES = {s["source_id"]: s for s in load("fuentes_investigacion.json")}
CONFLICT_SOURCES = ["SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA", "SRC-PROVEEDOR", "SRC-CUADRO", "SRC-OFICINA"]
LONG_SOURCE = LABELS["long_report"]["source_id"]
# Pares de cifras en conflicto según los metadatos: los que se explican por periodo, método, muestra o población
# y el que no se explica por nada (el contraste que permite saber si el informe distingue o lo atribuye todo a la fecha).
EXPLAINED_TOPICS = [c["topic"] for c in LABELS["conflicts"] if c["explained_by"] != ["sin_explicacion"]]
UNEXPLAINED_TOPICS = [c["topic"] for c in LABELS["conflicts"] if c["explained_by"] == ["sin_explicacion"]]
# Palabras con las que un informe explica una diferencia por cada tipo de contexto (comprobación laxa).
KIND_WORDS = {
    "periodo": re.compile(r"31 de agosto|agosto|corte|per[ií]odo", re.I),
    "metodo": re.compile(r"espera|m[eé]todo|metodolog|criterio de medici[oó]n|c[oó]mo se mide|definici[oó]n de la medida", re.I),
    "muestra": re.compile(r"muestra", re.I),
    "poblacion": re.compile(r"95 usuarios|212|poblaci[oó]n|encuestad|usuarios del proveedor", re.I),
}


def request_for(parte: str) -> str:
    """Petición del usuario. No dice que haya cifras en conflicto ni dónde está el hallazgo clave."""
    if parte == "medio":
        return f"Resume en tres frases los hallazgos del informe {LONG_SOURCE} ({SOURCES[LONG_SOURCE]['name']})."
    return (
        "Prepara un informe sobre la calidad del servicio de la mesa de ayuda en el tercer trimestre con lo que digan "
        "estas fuentes:\n" + "\n".join(f"- {sid}: {SOURCES[sid]['name']}" for sid in CONFLICT_SOURCES)
    )


# --- Subagentes y coordinador ---------------------------------------------------------------------


def researcher_prompt(anti: str | None) -> str:
    """Prompt del investigador. En `sin_procedencia` devuelve prosa en vez de datos estructurados."""
    if anti == "sin_procedencia":
        return (
            "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador y resume en prosa, "
            "en un párrafo corto por fuente, lo que dice cada una."
        )
    return (
        "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador. Devuelve una lista JSON de "
        "afirmaciones; cada una con el contenido separado de los metadatos: "
        '{"content": {"claim": …, "figure": …, "unit": …, "context": …}, "metadata": {"source_id": …, "published_at": …}}. '
        "figure es la cifra como número (null si la afirmación es cualitativa) y unit su unidad. context es el contexto "
        "metodológico que dé la fuente para esa cifra (periodo, método de medición, muestra o población), o null si no dice nada. "
        "Una afirmación por dato. "
        "Copia source_id y published_at de lo que devuelva la tool, sin cambiarlos."
    )


def synthesizer_prompt(anti: str | None) -> str:
    """Prompt del sintetizador. En `promedio` fusiona las cifras en conflicto."""
    base = (
        "Eres el sintetizador. Solo cuentas con lo que viene en tu prompt: no tienes tools. Redacta el informe conservando, "
        "para cada afirmación, su fuente (source_id) y su fecha. Separa lo establecido (varias fuentes coinciden) de lo disputado "
    )
    # Contexto metodológico (TS 5.6-S2): la diferencia se explica solo si el periodo, el método, la muestra o la población la explican.
    context = (
        "Cuando dos cifras difieran, usa el context de cada una (periodo, método, muestra, población) para explicar la diferencia "
        "si el contexto la explica; si ningún contexto la explica, no la explique tú: déjala como disputada. "
    )
    if anti == "promedio":
        dispute = (
            "(cifras distintas para lo mismo). Si dos fuentes dan cifras distintas para lo mismo, da una única cifra "
            "consolidada: el promedio de las dos, para que el informe sea claro. "
        )
    else:
        dispute = (
            "(cifras distintas para lo mismo). En lo disputado muestra cada cifra con su fuente y su fecha; no las combines "
            "en una sola ni elijas una sin decirlo. "
        )
    return base + dispute + context + "Usa el formato según el tipo de contenido: tabla para las cifras comparables y prosa para lo cualitativo."


def coordinator_prompt(anti: str | None) -> str:
    """Objetivos y criterios, no pasos (1.3-S4). La variante se aplica en los subagentes, no aquí."""
    return (
        "Objetivo: entregar lo pedido con la procedencia de cada afirmación (fuente y fecha) y sin ocultar los desacuerdos entre "
        "fuentes. Dispones de dos subagentes, researcher (consulta las fuentes) y synthesizer (redacta); decides cuáles necesitas. "
        "No ven esta conversación ni se hablan entre sí: todo pasa por ti. Al synthesizer pásale en el prompt la petición y las "
        "afirmaciones completas que devolvió el researcher, con sus metadatos, tal como llegaron. No busques tú: delega."
    )


def build_agents(anti: str | None, subagent_model: str) -> dict[str, AgentDefinition]:
    descriptions = {
        "researcher": "Consulta fuentes de la investigación y devuelve las afirmaciones con su fuente y su fecha.",
        "synthesizer": "Redacta el informe a partir de las afirmaciones que le pases en el prompt.",
    }
    prompts = {"researcher": researcher_prompt(anti), "synthesizer": synthesizer_prompt(anti)}
    tools = {"researcher": [QUERY_SOURCE], "synthesizer": []}
    return {
        name: AgentDefinition(
            description=descriptions[name], prompt=prompts[name], tools=tools[name], model=subagent_model,
            background=False,  # en primer plano: el coordinador necesita el resultado (regla 4)
        )
        for name in descriptions
    }


def text_flags(texto: str) -> dict[str, bool]:
    """Qué técnica de 5.1 aplica el servidor al informe largo: resumen al principio y/o encabezados de sección."""
    return {"summary_first": texto in ("con_resumen", "encabezados_y_resumen"), "headings": texto in ("con_encabezados", "encabezados_y_resumen")}


def build_options(anti: str | None, *, texto: str, budget: float, model: str, subagent_model: str) -> ClaudeAgentOptions:
    return isolated_options(
        max_budget_usd=budget,
        model=model,
        system_prompt=coordinator_prompt(anti),
        # El servidor aplica al informe largo la técnica de 5.1 que pida `texto`: línea de resumen al principio, encabezados o ambas.
        mcp_servers={SERVER_NAME: build_server(sources=True, **text_flags(texto))},
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


# --- Lo que devuelve cada subagente ---------------------------------------------------------------


def claim_problems(item: dict[str, Any]) -> list[str]:
    """Qué le falta o le sobra a una afirmación para conservar su procedencia."""
    content, metadata = item.get("content"), item.get("metadata")
    problems = [f"falta {name}" for name, value in (("content", content), ("metadata", metadata)) if not isinstance(value, dict)]
    if problems:
        return problems
    if not content.get("claim"):
        problems.append("content sin claim")
    mixed = [key for key in METADATA_KEYS if key in content]
    if mixed:
        problems.append(f"content mezcla metadatos: {', '.join(mixed)}")
    source_id, published_at = metadata.get("source_id"), metadata.get("published_at")
    if not source_id:
        problems.append("metadata sin source_id")
    elif source_id not in SOURCES:
        problems.append(f"source_id desconocido: {source_id}")
    if not published_at:
        problems.append("metadata sin published_at")
    elif source_id in SOURCES and published_at != SOURCES[source_id]["published_at"]:
        problems.append(f"fecha no coincide con la de {source_id}")
    return problems


def json_values(text: str) -> Iterator[Any]:
    """Valores JSON que hay en un texto con prosa alrededor."""
    decoder, pos = json.JSONDecoder(), 0
    while pos < len(text):
        if text[pos] not in "{[":
            pos += 1
            continue
        try:
            value, pos = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            pos += 1
            continue
        yield value


def iter_claims(value: Any) -> Iterator[dict[str, Any]]:
    """Afirmaciones (`content` + `metadata`) dentro de un valor JSON: sueltas, en lista o dentro de `{"claims": [...]}`."""
    if isinstance(value, dict) and isinstance(value.get("content"), dict) and isinstance(value.get("metadata"), dict):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_claims(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_claims(child)


def delegated(rec: RunRecord, subagent: str):
    return [c for c in rec.tool_calls if c.name in SUBAGENT_TOOLS and c.input.get("subagent_type") == subagent]


def subagent_claims(rec: RunRecord) -> list[dict[str, Any]]:
    """Afirmaciones estructuradas que el investigador devolvió al coordinador."""
    return [item for call in delegated(rec, "researcher") for value in json_values(call.result_text or "") for item in iter_claims(value)]


def structured_share(rec: RunRecord) -> tuple[int, int]:
    """(afirmaciones sin problemas, afirmaciones estructuradas devueltas)."""
    claims = subagent_claims(rec)
    return sum(not claim_problems(c) for c in claims), len(claims)


def sources_passed(rec: RunRecord) -> dict[str, list[str]]:
    """Fuentes que el investigador devolvió frente a las que llegaron al prompt del sintetizador."""
    found = {c["metadata"].get("source_id") for c in subagent_claims(rec)} - {None}
    prompt = " ".join(c.input.get("prompt", "") for c in delegated(rec, "synthesizer"))
    passed = {sid for sid in found if sid in prompt}
    return {"found": sorted(found), "passed": sorted(passed), "missing": sorted(found - passed)}


# --- Lo que llega al informe final ----------------------------------------------------------------


def has_number(text: str, figure: str) -> bool:
    """La cifra aparece como número propio, no dentro de otro (`18` no está en `118` ni en `2026-10-18`)."""
    return bool(re.search(rf"(?<!\d)(?<!\d[.,/-]){re.escape(figure)}(?!\d)(?![.,/-]\d)", text))


def figure_sources() -> dict[str, list[str]]:
    """Cifra (sin unidad) → fuentes que la respaldan, según las etiquetas."""
    sources = {LABELS["established"]["figure_text"]: list(LABELS["established"]["source_ids"])}
    for conflict in LABELS["conflicts"]:
        for claim in conflict["claims"]:
            sources[claim["figure_text"].split()[0]] = [claim["source_id"]]
    return sources


def figures_with_source(text: str | None) -> dict[str, bool]:
    """Para cada cifra de las fuentes que aparece en el texto: ¿hay, en su misma frase o fila, su fuente (id o nombre)?"""
    result: dict[str, bool] = {}
    sentences = [s.lower() for s in re.split(r"[;\n]|(?<=[.!?])\s+", text or "")]
    for figure, source_ids in figure_sources().items():
        if not has_number(text or "", figure):
            continue
        marks = [m.lower() for sid in source_ids for m in (sid, SOURCES[sid]["name"])]
        result[figure] = any(has_number(s, figure) and any(m in s for m in marks) for s in sentences)
    return result


def provenance_share(text: str | None) -> tuple[int, int]:
    """(cifras con su fuente en la frase, cifras de las fuentes presentes en el texto)."""
    found = figures_with_source(text)
    return sum(found.values()), len(found)


def merged_figures(text: str | None) -> list[tuple[str, str]]:
    """Cifras del texto que son el promedio de las de un conflicto (ninguna fuente dice eso)."""
    merged = []
    for conflict in LABELS["conflicts"]:
        figures = [c["figure"] for c in conflict["claims"]]
        average = sum(figures) / len(figures)
        forms = {f"{average:g}", f"{int(average * 10) / 10:g}", f"{(int(average * 10) + 1) / 10:g}", f"{average:.2f}".rstrip("0").rstrip(".")}
        for form in sorted(forms):
            for variant in {form, form.replace(".", ",")}:
                if text and has_number(text, variant):
                    merged.append((conflict["topic"], variant))
    return sorted(set(merged), key=lambda pair: (pair[0], pair[1]))


def conflicts_presented(text: str | None) -> dict[str, bool]:
    """Por conflicto: las dos cifras aparecen y el texto dice, en algún sitio, que difieren (comprobación laxa)."""
    disputed = bool(DISPUTE_WORDS.search(text or ""))
    return {
        conflict["topic"]: disputed and all(has_number(text or "", c["figure_text"].split()[0]) for c in conflict["claims"])
        for conflict in LABELS["conflicts"]
    }


def explanation_found(text: str | None) -> dict[str, list[str]]:
    """Por par: qué tipos de contexto (periodo, método, muestra, población) usa el texto, leyendo las líneas que nombran el par.

    Una línea cuenta si lleva una de las cifras del par o su tema; es laxo (una línea con cifras de varios pares vale para todos).
    """
    lines = (text or "").splitlines()
    found: dict[str, list[str]] = {}
    for conflict in LABELS["conflicts"]:
        figures = [c["figure_text"].split()[0] for c in conflict["claims"]]
        relevant = [line for line in lines if conflict["topic"] in line.lower() or any(has_number(line, f) for f in figures)]
        found[conflict["topic"]] = [kind for kind, words in KIND_WORDS.items() if any(words.search(line) for line in relevant)]
    return found


def explained_by_metadata(text: str | None) -> dict[str, bool]:
    """Por par con explicación: ¿el informe explica la diferencia con alguno de los contextos que la explican de verdad?"""
    found = explanation_found(text)
    explained = {c["topic"]: c["explained_by"] for c in LABELS["conflicts"]}
    return {topic: any(kind in found[topic] for kind in explained[topic]) for topic in EXPLAINED_TOPICS}


def unexplained_status(text: str | None) -> dict[str, dict[str, bool]]:
    """Por par sin explicación: ¿lo atribuye a la fecha o al método (que son iguales) y lo deja como disputado?"""
    found, presented = explanation_found(text), conflicts_presented(text)
    return {topic: {"attributed": bool(found[topic]), "disputed": presented[topic]} for topic in UNEXPLAINED_TOPICS}


def uses_table(text: str | None) -> bool:
    """Al menos dos filas de tabla Markdown: el formato que pide el tipo de contenido «cifras comparables»."""
    return sum(line.lstrip().startswith("|") for line in (text or "").splitlines()) >= 2


def key_finding_reported(text: str | None) -> bool:
    """¿Cita la cifra del hallazgo clave del informe largo?"""
    return bool(re.search(r"(?<!\d)41\s?(%|por ciento)", text or ""))


# --- Ejecución ------------------------------------------------------------------------------------


def expectation(anti: str | None, parte: str, texto: str) -> str:
    if parte == "medio":
        return {
            "sin_resumen": "el hallazgo clave está en mitad de un texto largo: puede que el resumen no lo recoja",
            "con_resumen": "la línea de resumen al principio pone el hallazgo clave a la vista",
            "con_encabezados": "los encabezados de sección ayudan a ubicar el hallazgo clave dentro del texto largo",
            "encabezados_y_resumen": "resumen al principio y encabezados de sección: las dos técnicas de 5.1 juntas",
        }[texto]
    return {
        None: "afirmaciones estructuradas con fuente y fecha, cada cifra con su fuente, las diferencias explicadas por el periodo o el método cuando los metadatos lo permiten, el par sin explicación como disputado y ningún promedio",
        "sin_procedencia": "prosa del investigador: al informe llegan cifras sin su fuente en la frase",
        "promedio": "el sintetizador fusiona las cifras en conflicto en un promedio que ninguna fuente respalda",
    }[anti]


def print_measures(rec: RunRecord, parte: str) -> None:
    if parte == "medio":
        print(f"[medida] hallazgo clave ({LABELS['long_report']['figure_text']}) en el resumen entregado: {key_finding_reported(rec.final_text)}")
        return
    ok, total = structured_share(rec)
    print(f"[medida] afirmaciones estructuradas sin problemas: {ok}/{total} · fuentes que llegaron al sintetizador: {sources_passed(rec)}")
    with_source, figures = provenance_share(rec.final_text)
    print(f"[medida] cifras del informe con su fuente en la frase: {with_source}/{figures} · {figures_with_source(rec.final_text)}")
    print(f"[medida] conflictos presentados como disputados (sin fusionar): {conflicts_presented(rec.final_text)}")
    print(f"[medida] cifras fusionadas (promedio de un conflicto): {merged_figures(rec.final_text) or 'ninguna'} · tabla para las cifras: {uses_table(rec.final_text)}")
    print(f"[medida] contexto que usa el informe por par: {explanation_found(rec.final_text)}")
    print(f"[medida] diferencia explicada con el periodo o el método (pares que los metadatos explican): {explained_by_metadata(rec.final_text)}")
    print(f"[medida] par sin explicación (atribuido a fecha o método · dejado como disputado): {unexplained_status(rec.final_text)}")


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTES, default="conflictos")
    parser.add_argument("--texto", choices=TEXTOS, default="sin_resumen", help="técnica de 5.1 sobre el informe largo; solo con --parte medio")
    args = parser.parse_args()
    print(credentials.describe())
    model = report_model("coordinator")
    subagent_model = report_model("subagent")
    budget = report_budget(args.budget, "multiagent")

    for run in range(1, args.repeat + 1):
        # El tope es de toda la ejecución del script, repartido entre repeticiones.
        options = build_options(args.anti, texto=args.texto, budget=budget / args.repeat, model=model, subagent_model=subagent_model)
        print(f"\n=== ejecución {run}/{args.repeat} · parte {args.parte} · variante {args.anti or 'correcta'}"
              + (f" · texto {args.texto}" if args.parte == "medio" else "") + " ===")
        print(f"[esperado] {expectation(args.anti, args.parte, args.texto)}")
        rec = await record(query(prompt=request_for(args.parte), options=options))
        print(f"[respuesta completa]\n{rec.final_text}")
        print(f"[medida] intentos del coordinador con tools de fuentes, denegados: {coordinator_attempts(rec)}")
        print_measures(rec, args.parte)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
