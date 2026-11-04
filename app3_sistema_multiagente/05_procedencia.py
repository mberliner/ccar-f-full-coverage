"""Procedencia entre agentes: afirmación y fuente juntas, cifras en conflicto sin fusionar y hallazgos en mitad de un texto largo.

CONCEPTO [TS 5.6-K1…K4, S1…S5 · TS 5.1-K2, S4, S5, S6 · TS 1.3-S2]: cómo llega la
procedencia de lo que encuentra un subagente hasta el informe final, cómo se tratan
las cifras que no coinciden y qué le pasa al hallazgo clave cuando el texto es largo.

QUÉ DICE LA GUÍA:
- Procedencia:
  - La atribución se pierde cuando un resumen comprime los hallazgos sin conservar
    qué afirmación sale de qué fuente (5.6-K1). El mapeo afirmación–fuente es una
    estructura que el sintetizador conserva y combina (5.6-K2).
  - Los subagentes devuelven ese mapeo estructurado, con la fuente y el fragmento
    que la respalda (5.6-S1), y el contenido va separado de los metadatos al pasar
    contexto entre agentes (1.3-S2).
  - Si el agente de abajo tiene poco contexto, el de arriba le pasa datos
    estructurados (hechos clave, citas) en vez de contenido verboso (5.1-S6).
- Cifras que no coinciden:
  - Dos estadísticas creíbles que no coinciden se anotan con su fuente; no se elige
    una arbitrariamente (5.6-K3). El análisis termina con los valores en conflicto
    incluidos y anotados, y la reconciliación se decide antes de la síntesis (5.6-S3).
  - Las fechas de publicación o de recogida van en la salida estructurada, para que
    una diferencia temporal no se lea como una contradicción (5.6-K4, S4). Los
    subagentes incluyen metadatos (fechas, ubicación en la fuente, contexto
    metodológico) para que la síntesis sea correcta (5.1-S5).
  - El informe separa en secciones lo bien establecido de lo disputado y conserva
    cómo lo caracteriza cada fuente y su contexto metodológico (5.6-S2).
  - Cada tipo de contenido tiene su formato: los datos financieros, en tabla; las
    noticias, en prosa, y los hallazgos técnicos, en listas estructuradas (5.6-S5).
- Texto largo:
  - *Lost in the middle*: el modelo procesa bien el principio y el final de una
    entrada larga, y puede omitir lo que está en mitad (5.1-K2). Se mitiga con un
    resumen de los hallazgos clave al principio y con encabezados de sección
    explícitos en los resultados detallados (5.1-S4).

POR QUÉ IMPORTA (inferencia propia): la procedencia no se reconstruye después. Si el
subagente devuelve prosa, la fuente de cada cifra se pierde en el primer salto; si el
sintetizador promedia, ninguna fuente respalda ya el número del informe; y si una
diferencia de periodo se lee como contradicción, se descarta un dato que era correcto.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Subagentes que devuelven prosa en vez del mapeo afirmación–fuente
    (`--anti sin_procedencia`).
  - Fusionar dos cifras en conflicto en una sola, o quedarse con una sin decirlo
    (`--anti promedio`).
  - Tomar por contradicción lo que es una diferencia de fecha o de método.
  - Poner el hallazgo clave en mitad de un texto largo sin resumen ni encabezados
    (`--parte medio --texto sin_resumen`, frente a `con_resumen`, `con_encabezados` y
    `encabezados_y_resumen`).
- Inferencias propias, con lo observado aquí (cifras en el README y en
  `docs/hallazgos.md`):
  - Explicar una diferencia solo vale si los metadatos la explican. Por eso hay un
    tercer par sin explicación, de contraste: si el informe atribuyera también ese
    par a la fecha o al método, estaría inventando la explicación. No lo hizo.
  - `sin_procedencia` y *lost in the middle* no dieron señal en el informe final con
    estos tamaños: lo que se pierde con la prosa es la estructura (la cifra ya no va
    unida a su fuente en un campo), y un informe de unos 9.000 caracteres no basta
    para que el modelo omita el hallazgo. Se documenta, no se fuerza.
  - En este módulo el coordinador pasa las afirmaciones tal como llegan y el
    sintetizador deja como disputado lo que no se explica. La guía pone la decisión
    de reconciliar antes de la síntesis (5.6-S3); aquí esa decisión se reduce a «no
    reconciliar sin contexto que lo justifique».
  - El formato por tipo se mide solo con la tabla de las cifras comparables; aquí no
    hay noticias ni hallazgos técnicos.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 05.

INTRODUCE: TS 5.6-K1, TS 5.6-K2, TS 5.6-K3, TS 5.6-K4, TS 5.6-S1, TS 5.6-S2, TS 5.6-S3, TS 5.6-S4, TS 5.6-S5, TS 5.1-K2, TS 5.1-S4, TS 5.1-S5, TS 5.1-S6, TS 1.3-S2

Uso: `uv run python app3_sistema_multiagente/05_procedencia.py [--parte conflictos|medio] [--texto sin_resumen|con_resumen|con_encabezados|encabezados_y_resumen] [--anti sin_procedencia|promedio|formato_uniforme|inventar_explicacion] [--repeat N]`
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

ANTI_VARIANTS = ["sin_procedencia", "promedio", "formato_uniforme", "inventar_explicacion"]
PARTES = ["conflictos", "medio"]
TEXTOS = ["sin_resumen", "con_resumen", "con_encabezados", "encabezados_y_resumen"]
QUERY_SOURCE = tool_name("query_source")
METADATA_KEYS = ("source_id", "published_at", "date", "fecha", "url", "location", "excerpt", "relevance")
DISPUTE_WORDS = re.compile(r"difier|discrep|disput|conflict|contradic|no coincid|no concuerd", re.I)
# Una palabra de desacuerdo negada («no hay discrepancias», «no difieren», «sin conflicto») no presenta ningún desacuerdo.
NEGATED_DISPUTE = re.compile(r"\b(?:no|ni|sin|ningun[ao]?|nada)\s+(?:\w+\s+){0,3}?(?:difier\w*|discrep\w*|disput\w*|conflict\w*|contradic\w*)", re.I)
# Decisión de reconciliación del coordinador (TS 5.6-S3), leída de su prompt al sintetizador. La negación manda: «no queda explicado» es disputado.
DECISION_DISPUTED = re.compile(r"disputad|sin explicaci|no se explica|no queda explicad|no (?:est[aá]|queda) reconcili|sin reconcili", re.I)
DECISION_EXPLAINED = re.compile(r"explicad|se explica|lo explica|queda explicad", re.I)
PROXIMITY = 300  # caracteres a cada lado del source_id en los que debe ir su afirmación (sources_passed)

LABELS = load("fuentes_investigacion_etiquetas.json")
SOURCES = {s["source_id"]: s for s in load("fuentes_investigacion.json")}
CONFLICT_SOURCES = ["SRC-TICKETS", "SRC-AUDITORIA", "SRC-ENCUESTA", "SRC-PROVEEDOR", "SRC-CUADRO", "SRC-OFICINA"]
LONG_SOURCE = LABELS["long_report"]["source_id"]
# Pares de cifras en conflicto según los metadatos: los que se explican por periodo, método, muestra o población
# y el que no se explica por nada (el contraste que permite saber si el informe distingue o lo atribuye todo a la fecha).
EXPLAINED_TOPICS = [c["topic"] for c in LABELS["conflicts"] if c["explained_by"] != ["sin_explicacion"]]
UNEXPLAINED_TOPICS = [c["topic"] for c in LABELS["conflicts"] if c["explained_by"] == ["sin_explicacion"]]
# Palabras con las que un informe explica una diferencia por cada tipo de contexto (comprobación laxa).
# «espera» (verbo: «se espera confirmar») y «muestra» (verbo: «la tabla muestra») no cuentan: solo las esperas y la muestra como sustantivo.
KIND_WORDS = {
    "periodo": re.compile(r"31 de agosto|agosto|corte|per[ií]odo", re.I),
    "metodo": re.compile(r"\besperas\b|esperas? de respuesta|tiempos? de espera|m[eé]todo|metodolog|criterio de medici[oó]n|c[oó]mo se mide|definici[oó]n de la medida", re.I),
    "muestra": re.compile(
        r"\b(?:una|la|esa|dicha|otra|su|de|con|sobre|menor|peque[ñn]a|distinta)\s+muestra\b|muestra de \d|tama[ñn]o de (?:la )?muestra|\bmuestras?\s+(?:menor|m[aá]s|reducida|parcial)", re.I),
    "poblacion": re.compile(r"95 usuarios|\b212\b|poblaci[oó]n|encuestad|usuarios del proveedor", re.I),
}
# Decir que el contexto es el mismo («mismo periodo», «la misma población») no es atribuirle esa explicación a la diferencia.
SAME_CONTEXT = re.compile(r"\b(?:mism[oa]s?|id[ée]ntic[oa]s?)\s+(?:\w+\s+){0,2}?(?:per[ií]odo|m[eé]todo|muestra|poblaci[oó]n|metodolog\w*|criterio)", re.I)
# Unidad que acompaña a un promedio redondeado a entero («≈4 sobre 5», «10 %»): sin ella, un entero suelto no cuenta.
UNIT_AFTER = {"horas": r"\s?(?:h\b|horas?\b)", "sobre 5": r"\s?(?:sobre 5\b|/\s?5\b)", "%": r"\s?(?:%|por ciento)"}
# Palabra más larga del tema de cada par: basta para saber de qué par habla una línea («resolución», «satisfacción», «reabiertos»).
TOPIC_KEYS = {c["topic"]: max(c["topic"].split(), key=len) for c in LABELS["conflicts"]}


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
    """Prompt del investigador. En `sin_procedencia` devuelve prosa verbosa con su razonamiento y sin metadatos."""
    if anti == "sin_procedencia":
        return (
            "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador. Escribe en prosa, sin "
            "listas ni datos estructurados, uno o dos párrafos largos por fuente con tu razonamiento paso a paso: qué dice la "
            "fuente, cómo interpretas cada dato y qué conclusiones sacas. No incluyas identificadores de fuente, fechas ni apartados."
        )
    return (
        "Eres el investigador. Consulta con query_source las fuentes que te indique el coordinador. Devuelve una lista JSON de "
        "afirmaciones; cada una con el contenido separado de los metadatos: "
        '{"content": {"claim": …, "figure": …, "unit": …, "context": …}, '
        '"metadata": {"source_id": …, "published_at": …, "location": …, "excerpt": …, "relevance": …}}. '
        "figure es la cifra como número (null si la afirmación es cualitativa) y unit su unidad. context es el contexto "
        "metodológico que dé la fuente para esa cifra (periodo, método de medición, muestra o población), o null si no dice nada. "
        "location es el título de la sección de la fuente donde está el dato (los informes traen secciones `## título`); excerpt, "
        "la frase literal de la fuente que respalda la afirmación, copiada sin cambios; relevance, un número de 0 a 1 que dice "
        "cuánto responde la afirmación a lo que se pide. "
        "Una afirmación por dato. "
        "Copia source_id y published_at de lo que devuelva la tool, sin cambiarlos."
    )


def synthesizer_prompt(anti: str | None) -> str:
    """Prompt del sintetizador. `promedio` fusiona cifras, `inventar_explicacion` explica siempre y `formato_uniforme` no distingue formatos."""
    base = (
        "Eres el sintetizador. Solo cuentas con lo que viene en tu prompt: no tienes tools. Redacta el informe conservando, "
        "para cada afirmación, su fuente (source_id) y su fecha. Separa lo establecido (varias fuentes coinciden) de lo disputado "
    )
    # La reconciliación la decide el coordinador (TS 5.6-S3); el sintetizador la respeta: explica lo que el contexto explica
    # (periodo, método, muestra, población, TS 5.6-S2) y deja disputado lo que no.
    context = (
        "El coordinador te pasa su decisión de reconciliación por cada magnitud con cifras distintas: respétala. Si es «explicada», "
        "cuenta la explicación con el contexto de cada cifra (periodo, método, muestra, población); si es «disputada», no la explique tú: "
        "déjala como disputada. "
    )
    if anti == "inventar_explicacion":
        context = (
            "El coordinador te pasa su decisión de reconciliación por cada magnitud con cifras distintas, pero explica siempre por qué "
            "difieren las cifras (periodo, método, muestra o población), aunque el contexto no lo diga; no dejes ninguna diferencia como disputada. "
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
    if anti == "formato_uniforme":
        form = "Redacta todo en prosa continua, igual para cualquier tipo de contenido."
    else:
        form = "Usa el formato según el tipo de contenido: tabla para las cifras comparables y prosa para lo cualitativo."
    return base + dispute + context + form


def coordinator_prompt(anti: str | None) -> str:
    """Objetivos y criterios, no pasos (1.3-S4). Decide la reconciliación antes de la síntesis (TS 5.6-S3). La variante se aplica en los subagentes."""
    return (
        "Objetivo: entregar lo pedido con la procedencia de cada afirmación (fuente y fecha) y sin ocultar los desacuerdos entre "
        "fuentes. Dispones de dos subagentes, researcher (consulta las fuentes) y synthesizer (redacta); decides cuáles necesitas. "
        "No ven esta conversación ni se hablan entre sí: todo pasa por ti. Antes de pasarle nada al synthesizer, decide tú la "
        "reconciliación: por cada magnitud con cifras distintas entre fuentes, decide si el contexto que traen las afirmaciones "
        "(periodo, método, muestra, población) explica la diferencia (explicada) o no la explica (disputada), sin fusionar ni descartar "
        "ninguna cifra. Al synthesizer pásale en el prompt la petición, las afirmaciones completas que devolvió el researcher, con sus "
        "metadatos, y tu decisión: una línea por magnitud, «<magnitud>: explicada por <contexto>» o «<magnitud>: disputada». "
        "No busques tú: delega."
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
    problems += detail_problems(metadata)
    relevance = metadata.get("relevance")
    if isinstance(relevance, bool) or not isinstance(relevance, int | float) or not 0 <= relevance <= 1:
        problems.append("relevance no es un número de 0 a 1")
    return problems


def squash(text: str) -> str:
    """Espacios normalizados: un fragmento copiado con espacios de más sigue siendo literal."""
    return " ".join(text.split())


def location_problem(metadata: dict[str, Any]) -> str | None:
    """La ubicación debe ser el título de una sección del informe de esa fuente (TS 5.1-S5)."""
    location, source_id = metadata.get("location"), metadata.get("source_id")
    if not location or not isinstance(location, str):
        return "metadata sin location"
    if source_id in SOURCES and f"## {location}\n" not in (SOURCES[source_id]["report"] or ""):
        return f"location no es una sección de {source_id}"
    return None


def excerpt_problem(metadata: dict[str, Any]) -> str | None:
    """El fragmento debe estar tal cual en el informe de esa fuente (TS 5.6-S1)."""
    excerpt, source_id = metadata.get("excerpt"), metadata.get("source_id")
    if not excerpt or not isinstance(excerpt, str):
        return "metadata sin excerpt"
    if source_id in SOURCES and squash(excerpt) not in squash(SOURCES[source_id]["report"] or ""):
        return f"excerpt no es literal de {source_id}"
    return None


def detail_problems(metadata: dict[str, Any]) -> list[str]:
    return [p for p in (location_problem(metadata), excerpt_problem(metadata)) if p]


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


def detail_share(rec: RunRecord) -> dict[str, int]:
    """Afirmaciones del investigador con ubicación válida y con fragmento literal, sobre el total (TS 5.1-S5, 5.6-S1)."""
    claims = subagent_claims(rec)
    return {
        "location": sum(location_problem(c["metadata"]) is None for c in claims),
        "excerpt": sum(excerpt_problem(c["metadata"]) is None for c in claims),
        "total": len(claims),
    }


def figure_forms(figure: Any) -> list[str]:
    """Una cifra tal como puede escribirse: `4.1` → `4.1` y `4,1`; `1240` → `1240` y `1.240`."""
    if figure is None:
        return []
    text = f"{figure:g}" if isinstance(figure, float) else str(figure)
    forms = [text, text.replace(".", ",")]
    if isinstance(figure, int) and figure >= 1000:
        forms.append(f"{figure:,}".replace(",", "."))
    return forms


def claim_near_id(prompt: str, source_id: str, item: dict[str, Any]) -> bool:
    """¿Va la afirmación con su fuente? El source_id tiene cerca (`PROXIMITY`) el texto de la afirmación o su cifra."""
    text = str(item["content"].get("claim", "")).lower()[:30]
    forms = figure_forms(item["content"].get("figure"))
    for match in re.finditer(re.escape(source_id), prompt):
        window = prompt[max(0, match.start() - PROXIMITY): match.end() + PROXIMITY]
        if (text and text in window.lower()) or any(has_number(window, f) for f in forms):
            return True
    return False


def sources_passed(rec: RunRecord) -> dict[str, list[str]]:
    """Fuentes que el investigador devolvió frente a las que llegaron al sintetizador junto con su afirmación.

    Que el id aparezca en cualquier parte del prompt no basta: tiene que ir con su afirmación o con su cifra.
    """
    claims = subagent_claims(rec)
    found = {c["metadata"].get("source_id") for c in claims} - {None}
    prompt = " ".join(c.input.get("prompt", "") for c in delegated(rec, "synthesizer"))
    passed = {sid for sid in found if any(claim_near_id(prompt, sid, c) for c in claims if c["metadata"].get("source_id") == sid)}
    return {"found": sorted(found), "passed": sorted(passed), "missing": sorted(found - passed)}


def coordinator_decisions(rec: RunRecord) -> dict[str, str | None]:
    """Decisión de reconciliación por par (`explicado`, `disputado` o None), leída de los prompts del sintetizador.

    Comprobación laxa: una línea o frase que nombra el par (su tema o una de sus fuentes) y trae una palabra de decisión.
    La negación manda: «no queda explicado» es disputado.
    """
    prompt = "\n".join(c.input.get("prompt", "") for c in delegated(rec, "synthesizer"))
    pieces = [piece for piece in re.split(r"[;\n]|(?<=[.!?])\s+", prompt) if piece.strip()]
    decisions: dict[str, str | None] = {}
    for conflict in LABELS["conflicts"]:
        marks = [TOPIC_KEYS[conflict["topic"]].lower(), conflict["topic"], *(c["source_id"].lower() for c in conflict["claims"])]
        relevant = [piece for piece in pieces if any(m in piece.lower() for m in marks)]
        decision = None
        if any(DECISION_DISPUTED.search(piece) for piece in relevant):
            decision = "disputado"
        elif any(DECISION_EXPLAINED.search(piece) for piece in relevant):
            decision = "explicado"
        decisions[conflict["topic"]] = decision
    return decisions


def decisions_correct(rec: RunRecord) -> dict[str, bool]:
    """¿Coincide la decisión del coordinador con lo que dicen las etiquetas (explicable por contexto o sin explicación)?"""
    decisions = coordinator_decisions(rec)
    return {
        c["topic"]: decisions[c["topic"]] == ("disputado" if c["explained_by"] == ["sin_explicacion"] else "explicado")
        for c in LABELS["conflicts"]
    }


def researcher_output_size(rec: RunRecord) -> int:
    """Caracteres que el investigador devolvió al coordinador (estructurado u verboso)."""
    return sum(len(c.result_text or "") for c in delegated(rec, "researcher"))


def synthesizer_input_size(rec: RunRecord) -> int:
    """Caracteres que llegan al sintetizador: lo que el coordinador le pasa en el prompt (TS 5.1-S6)."""
    return sum(len(c.input.get("prompt", "")) for c in delegated(rec, "synthesizer"))


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
        # Promedio redondeado a entero («≈4 sobre 5», «10 %»): solo con la unidad del par, para no confundirlo con otro número.
        rounded = str(round(average))
        if text and conflict["unit"] in UNIT_AFTER and re.search(rf"(?<!\d)(?<!\d[.,/-]){rounded}(?![\d]|[.,]\d){UNIT_AFTER[conflict['unit']]}", text):
            merged.append((conflict["topic"], rounded))
    return sorted(set(merged), key=lambda pair: (pair[0], pair[1]))


def conflicts_presented(text: str | None) -> dict[str, bool]:
    """Por conflicto: las dos cifras aparecen y el texto dice, en algún sitio, que difieren (comprobación laxa)."""
    disputed = bool(DISPUTE_WORDS.search(NEGATED_DISPUTE.sub("", text or "")))
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
        relevant = [SAME_CONTEXT.sub("", line) for line in relevant]
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


def table_covers_pairs(text: str | None) -> dict[str, bool]:
    """Por par: las dos cifras están dentro de las filas de la tabla (no basta con que haya una tabla)."""
    rows = "\n".join(line for line in (text or "").splitlines() if line.lstrip().startswith("|"))
    return {c["topic"]: all(has_number(rows, claim["figure_text"].split()[0]) for claim in c["claims"]) for c in LABELS["conflicts"]}


def words_of(text: str) -> list[str]:
    return re.sub(r"[^\w%]+", " ", text.lower()).split()


def shares_fragment(text: str, excerpt: str, figure: str, size: int = 6) -> bool:
    """¿Reproduce el texto, palabra por palabra, un tramo de `size` palabras del fragmento que incluya la cifra?"""
    haystack = " " + " ".join(words_of(text)) + " "
    words, digits = words_of(excerpt), words_of(figure)
    windows = [words[i: i + size] for i in range(max(1, len(words) - size + 1))]
    return any(all(d in w for d in digits) and " " + " ".join(w) + " " in haystack for w in windows)


def detail_in_report(text: str | None) -> dict[str, dict[str, bool]]:
    """Por fuente en conflicto cuya cifra aparece en el texto: ¿llegan su sección y un tramo de su fragmento (TS 5.1-S5, 5.6-S1)?

    La sección cuenta si su título va en la misma frase o fila que la cifra; el fragmento, si el texto reproduce un tramo de él con la cifra.
    """
    result: dict[str, dict[str, bool]] = {}
    sentences = [s.lower() for s in re.split(r"[;\n]|(?<=[.!?])\s+", text or "")]
    for conflict in LABELS["conflicts"]:
        for claim in conflict["claims"]:
            figure = claim["figure_text"].split()[0]
            if not has_number(text or "", figure):
                continue
            result[claim["source_id"]] = {
                "location": any(has_number(s, figure) and claim["location"].lower() in s for s in sentences),
                "excerpt": shares_fragment(text or "", claim["excerpt"], figure),
            }
    return result


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
        "formato_uniforme": "todo en prosa, sin tabla: las cifras comparables no quedan en una tabla con sus pares",
        "inventar_explicacion": "el sintetizador explica siempre las diferencias: también atribuye a un periodo, un método o una muestra el par que el contexto no explica",
    }[anti]


def print_measures(rec: RunRecord, parte: str) -> None:
    if parte == "medio":
        print(f"[medida] hallazgo clave ({LABELS['long_report']['figure_text']}) en el resumen entregado: {key_finding_reported(rec.final_text)}")
        return
    ok, total = structured_share(rec)
    print(f"[medida] afirmaciones estructuradas sin problemas: {ok}/{total} · fuentes que llegaron al sintetizador con su afirmación: {sources_passed(rec)}")
    print(f"[medida] ubicación y fragmento literal en las afirmaciones del investigador: {detail_share(rec)}")
    print(f"[medida] decisión del coordinador en el prompt del sintetizador: {coordinator_decisions(rec)} · acertadas: {decisions_correct(rec)}")
    print(f"[medida] tamaño (caracteres): lo que devuelve el investigador {researcher_output_size(rec)} · lo que llega al sintetizador {synthesizer_input_size(rec)}")
    with_source, figures = provenance_share(rec.final_text)
    print(f"[medida] cifras del informe con su fuente en la frase: {with_source}/{figures} · {figures_with_source(rec.final_text)}")
    print(f"[medida] conflictos presentados como disputados (sin fusionar): {conflicts_presented(rec.final_text)}")
    print(f"[medida] cifras fusionadas (promedio de un conflicto): {merged_figures(rec.final_text) or 'ninguna'}")
    print(f"[medida] tabla: {uses_table(rec.final_text)} · pares con sus dos cifras dentro de la tabla: {table_covers_pairs(rec.final_text)}")
    print(f"[medida] sección y fragmento de la fuente en el informe final: {detail_in_report(rec.final_text)}")
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
