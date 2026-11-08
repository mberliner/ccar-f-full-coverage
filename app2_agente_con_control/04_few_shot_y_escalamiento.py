"""Criterios explícitos de escalamiento con ejemplos few-shot razonados.

CONCEPTO [TS 4.2-K1, K2, K3, S1 · TS 5.2-K1, K2, K3, K4, S1, S2, S3, S4, S5]: cuándo escalar a una persona y
cuándo resolver, enseñado con criterios explícitos y 2 a 4 ejemplos que muestran el razonamiento, y por qué el
sentimiento y la confianza autodeclarada no sirven de criterio.

QUÉ DICE LA GUÍA:
- Few-shot (4.2):
  - Cuando unas instrucciones detalladas, por sí solas, dan resultados inconsistentes, los ejemplos few-shot son
    la técnica más eficaz para conseguir una salida consistente en su forma y que se pueda usar (4.2-K1).
  - Su papel es enseñar cómo se resuelven los casos ambiguos; uno de los ejemplos de la guía es qué tool elegir
    ante una petición poco clara (4.2-K2).
  - Con ejemplos, el modelo puede generalizar el criterio a situaciones nuevas, no solo reconocer los casos que
    se le dieron por adelantado (4.2-K3).
  - La destreza: escribir de 2 a 4 ejemplos dirigidos a los escenarios ambiguos, cada uno con el razonamiento de
    por qué se tomó esa acción y no otra alternativa plausible (4.2-S1).
- Escalamiento (5.2):
  - Los disparadores adecuados son tres: que el cliente pida un humano, que la política tenga un vacío o una
    excepción (no basta con que el caso sea complejo) y que no se pueda avanzar de forma útil (5.2-K1).
  - No es lo mismo un cliente que exige un humano, al que se escala en el acto, que un problema sencillo, en el
    que se ofrece resolverlo (5.2-K2). Lo primero se cumple de inmediato, sin investigar antes (5.2-S2); ante la
    frustración se reconoce y se ofrece la solución si está al alcance del agente, y se escala solo si el
    cliente vuelve a pedir una persona (5.2-S3).
  - El sentimiento del mensaje y la confianza que el modelo declara sobre sí mismo no miden bien la complejidad
    real del caso: son *proxies* poco fiables para decidir el escalamiento (5.2-K3).
  - Si la política es ambigua o no dice nada sobre lo que se pide (el ejemplo de la guía: igualar el precio de
    un competidor cuando solo se contemplan ajustes en el propio sitio), se escala (5.2-S4).
  - Varias coincidencias en una búsqueda de cliente piden aclaración, no una elección por heurística (5.2-K4):
    se instruye al agente para que pida un identificador adicional (5.2-S5).
  - Las dos partes se unen en 5.2-S1: los criterios explícitos de escalamiento van en el *system prompt* con
    ejemplos few-shot de cuándo escalar y cuándo resolver sin ayuda.

POR QUÉ IMPORTA (inferencia propia): escalar mal cuesta en las dos direcciones. Escalar de más satura al equipo, y
ofrecer resolver a quien pidió un humano lo ignora; escalar de menos deja sin respuesta a quien la necesita y, con
los homónimos, actúa sobre la cuenta equivocada.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Decidir por el tono del cliente («si está enfadado, escala»: `--anti sentimiento`) o por la confianza que el
    propio modelo declara («si dice que no está seguro, escala»: `--anti confianza`) (5.2-K3).
  - Investigar o proponer pasos antes de pasar con una persona a quien ya la pidió (5.2-S2), y escalar una
    frustración sencilla a la primera (5.2-S3).
  - Elegir un empleado entre varios homónimos por una heurística («el más reciente», «el del departamento con
    más tickets») en vez de pedir un identificador (5.2-K4, S5).
  - Reservar el escalamiento a los casos «complejos» (5.2-K1).
- Lo que la medida no respalda:
  - Con Haiku 5.5, `sin_ejemplos` sale casi igual que la correcta (59/65 frente a 60/65). Las instrucciones no daban
    resultados inconsistentes con ese modelo, que es la condición de 4.2-K1, así que la medida ni demuestra ni
    contradice la guía. Con Haiku 4.5 sí hay diferencia, sobre todo en la frustración (36/39 frente a
    31/39), con una muestra pequeña (`README.md`).
  - Los ejemplos no coinciden con ningún caso evaluado, así que lo que acierta la correcta no es memoria de un
    caso; pero la medida no separa lo que aporta el ejemplo de lo que ya hacía el criterio escrito, y por eso no
    demuestra 4.2-K3 (generalizar a patrones nuevos).
  - En `confianza`, la confianza declarada no separa los aciertos de los fallos (60,8 frente a 61,7) y en medidas
    anteriores el sentido cambiaba, con pocos casos: no es una demostración de 5.2-K3. La señal de la variante es la tasa de acierto por tipo de caso.
  - El tercer disparador de 5.2-K1, «no se puede avanzar», tiene dos casos y ningún ejemplo, y solo cuenta con el
    criterio 5 del prompt. Ejercita 5.2-K1, no 4.2-K3: el patrón está dicho de antemano en el criterio, así que
    acertarlo no es generalizar a un patrón nuevo gracias a los ejemplos.
- Inferencias propias:
  - El proxy de sentimiento de `--parte proxy` es una lista de palabras inventada para esta demostración; la guía
    dice que el sentimiento es poco fiable, no que esa lista falle así.
  - Que un vacío de política suela llegar con tono neutro es una propiedad de los casos de este módulo, no algo
    que diga la guía.
  - Que sin ejemplo el agente a veces no busque a la empleada por nombre, y que por eso el criterio 4 (condicional a
    esa búsqueda) no llegue a aplicarse, es una hipótesis: salió de leer dos respuestas en un sondeo aparte, no de la
    medida.
- Límite de la medida: la acción se deduce de las llamadas a tools. En la frustración, «no escala» en el primer
  turno incluye cualquier cosa que no sea escalar (ofrecer resolver, pedir un dato o no decir nada): no se comprueba
  que se ofreciera resolver. Solo en los homónimos se lee además el texto del agente, con un detector de patrones
  (`asks_for_identifier`) que acepta como dato el ID, el correo o el departamento aunque el criterio 4 pida el ID: no
  entiende una petición escrita sin sus pistas y puede dar por buena una frase que las tenga y pida otra cosa.

Qué se mide: la acción de cada caso frente a su etiqueta, deducida de las llamadas a tools. Las variantes `sentimiento`
y `confianza` van sin ejemplos, porque los ejemplos contradirían su regla; el control con el que se comparan es
`sin_ejemplos` (mismos criterios, sin ejemplos), no la correcta.

Pregunta tipo examen: ver `app2_agente_con_control/README.md`, módulo 04.

INTRODUCE: TS 4.2-K1, TS 4.2-K2, TS 4.2-K3, TS 4.2-S1, TS 5.2-K1, TS 5.2-K2, TS 5.2-K3, TS 5.2-K4, TS 5.2-S1, TS 5.2-S2, TS 5.2-S3, TS 5.2-S4, TS 5.2-S5

Uso: `uv run python app2_agente_con_control/04_few_shot_y_escalamiento.py [--parte agente|proxy] [--anti sin_ejemplos|sentimiento|confianza] [--rol-modelo agent|enforcement] [--repeat N] [--budget USD]`
"""

import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import ClaudeSDKClient  # noqa: E402

from app2_agente_con_control.servers.helpdesk import SERVER_NAME, HelpdeskState, build_server, tool_name  # noqa: E402
from harness import credentials  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402
from harness.options import isolated_options  # noqa: E402
from harness.recorder import RunRecord, record  # noqa: E402

ANTI_VARIANTS = ["sin_ejemplos", "sentimiento", "confianza"]
# Roles de modelo que admite `--rol-modelo`: la señal de cada variante puede depender del modelo, y el nombre
# del modelo sigue saliendo de `.env`.
MODEL_ROLES = ["agent", "enforcement"]
PARTS = ["agente", "proxy"]

ESCALATE = tool_name("escalate_to_human")
FIND = tool_name("find_employee_by_name")
VERIFY = tool_name("verify_employee")
LIST_TICKETS = tool_name("list_employee_tickets")
SEARCH_KB = tool_name("search_kb")

BASE_PROMPT = (
    "Eres el agente de la mesa de ayuda TI de una empresa ficticia. Para cada mensaje decide si lo resuelves tú "
    "con las tools o lo pasas a una persona con escalate_to_human (resumen en texto libre). "
    "Responde en español y de forma breve."
)
# Criterios explícitos (5.2-K1, K2, K4). El 5 (no se puede avanzar, 5.2-K1) no tiene ejemplo. Iguales en la correcta y en `sin_ejemplos`.
CRITERIA_LINES = (
    "1. Si la persona pide de forma explícita hablar con un humano, escala de inmediato con escalate_to_human, sin investigar antes ni proponer pasos.",
    "2. Si solo expresa frustración y el problema es sencillo, reconoce la frustración y ofrece resolverlo; escala solo si insiste en querer a una persona.",
    "3. Si la política es ambigua o no dice nada sobre la solicitud, escala: decidir no te corresponde.",
    "4. Si una búsqueda de empleado devuelve varias coincidencias, no elijas por heurística: pide un identificador adicional (su ID EMP-NNNN).",
    "5. Si ya has probado lo que ofrece la base de conocimiento y el caso no avanza, escala con lo que se intentó.",
)
SENTIMENT_RULE = (
    "Escala a una persona cuando el mensaje muestre enfado, frustración o sentimiento negativo. "
    "Si el tono es neutro o positivo, resuélvelo tú."
)
CONFIDENCE_RULE = (
    "Antes de actuar escribe una línea «CONFIANZA: N» (N de 0 a 100) con lo seguro que estás de poder resolver el "
    "caso tú. Si N es menor que 70, escala a una persona con escalate_to_human; si no, resuélvelo tú."
)


def render_examples(examples: list[dict[str, str]]) -> str:
    """4.2-S1: cada ejemplo lleva la acción, el razonamiento y la alternativa plausible que se descarta."""
    blocks = []
    for number, example in enumerate(examples, start=1):
        blocks.append(
            f"Ejemplo {number}\n"
            f"Mensaje: {example['text']}\n"
            f"Acción: {example['action']}\n"
            f"Razonamiento: {example['reasoning']}\n"
            f"Alternativa descartada: {example['rejected_alternative']}"
        )
    return "\n\n".join(blocks)


def build_system_prompt(anti: str | None) -> str:
    """Prompt por variante. La correcta es `sin_ejemplos` más el bloque de ejemplos (una sola diferencia)."""
    criteria = "Criterios de escalamiento:\n" + "\n".join(CRITERIA_LINES)
    if anti is None:
        examples = render_examples(load("escalamiento_ejemplos.json"))
        return f"{BASE_PROMPT}\n\n{criteria}\n\nEjemplos de decisión:\n\n{examples}"
    if anti == "sin_ejemplos":
        return f"{BASE_PROMPT}\n\n{criteria}"
    if anti == "sentimiento":
        return f"{BASE_PROMPT}\n\n{SENTIMENT_RULE}"
    if anti == "confianza":
        return f"{BASE_PROMPT}\n\n{CONFIDENCE_RULE}"
    raise ValueError(f"variante desconocida: {anti}")


# --- Clasificación de la acción (desde las llamadas a tools, no desde el texto) -------


@dataclass
class Turn:
    action: str  # escalate_now | escalate_after_investigating | guessed_identity | no_escalation
    looked_up: bool
    tools: list[str] = field(default_factory=list)
    asked_id: bool = False  # el texto del turno pide un identificador (solo cuenta en los homónimos)
    cut: bool = False  # el tope de gasto cortó el turno: no puntúa, el agente no llegó a decidir
    error: bool = False  # la ejecución terminó con error que no es el tope de gasto: tampoco puntúa


# Dos cosas distintas: pedir (un verbo de petición, o una pregunta que pide algo) y el dato que se pide. Un «?» solo no
# es una petición ni el posesivo solo es un dato: «¿Cuál es el error?» y «tu correo. ¿Algo más?» no piden el ID.
REQUEST_VERBS = ("indícame", "indica", "dime", "proporciona", "facilítame", "facilita", "facilit", "envíame", "pásame",
                 "pasame", "confirm", "confírm", "necesito", "necesitaría")
ASKING_QUESTION = re.compile(
    r"\b(me|nos)\s+(das|pasas|indicas|facilitas|confirmas|puedes|podrías|podrias)\b"
    r"|\b(darme|pasarme|indicarme|facilitarme|confirmarme)\b"
    r"|\b(cuál|cual|qué|que)\s+(es|era)\s+(tu|su)\b"
    r"|\b(cuál|cual|qué|que)\s+(id|identificador|departamento|correo)\b"
    r"|\b(cuál|cual)\s+(de\s+(ellas|las dos|ellos)|eres)\b|\bde\s+cuál\b|\bqui[eé]n\s+eres\b"
)
# El dato que distingue a las homónimas: el ID de empleado (o su número o código), un identificador con formato,
# el posesivo con ID, correo o departamento, o la pregunta de cuál de ellas es. Sin «tu número …» a secas: «tu número de
# ticket» no es el dato.
EMPLOYEE_DATA = re.compile(
    r"\b(id|identificador|número|numero|código|codigo)\s+de\s+empleado\b|\bemp-"
    r"|\b(tu|su)\s+(id(?!\s+de\s+ticket)|identificador|correo|email|departamento)\b"
    r"|\bidentificador\b|\b(qué|que|cuál|cual)\s+(id|identificador|departamento|correo)\b"
    r"|\b(cuál|cual)\s+(de\s+(ellas|las dos|ellos)|eres)\b|\bde\s+cuál\b|\bqui[eé]n\s+eres\b"
)


def departments() -> set[str]:
    return {user["department"].lower() for user in load("usuarios.json")}


def asks_for_identifier(text: str | None) -> bool:
    """El texto pide un dato que distinga a las empleadas homónimas (5.2-K4, S5). Detector de patrones, aproximado.

    Hace falta una petición y un dato. Petición: un verbo («dime», «confirma», «necesito», «pásame») o una pregunta
    que pide algo («¿me das…?», «¿cuál es tu…?», «¿cuál de ellas eres?»); un «?» solo no basta. Dato: el ID, número o
    código de empleado, un `EMP-`, «identificador», el posesivo con ID, correo o departamento, o preguntar por qué
    departamento o cuál de ellas es. También cuenta nombrar dos departamentos con una pregunta, para que elija.
    Acepta el departamento o el correo como dato, aunque el criterio del prompt pide el ID.
    Límites: no entiende una petición escrita sin esas formas («para seguir necesito saber a cuál corresponde la
    solicitud» lleva verbo pero ningún dato de la lista), y puede dar por buena una frase que pida un dato de esa forma
    y siga adelante con otra cosa. Una frase con verbo y dato que no sea una petición
    («necesito tu ID» dicho por el cliente) también contaría.
    """
    lowered = (text or "").lower()
    if any(verb in lowered for verb in REQUEST_VERBS) or ASKING_QUESTION.search(lowered):
        if EMPLOYEE_DATA.search(lowered):
            return True
    return len({d for d in departments() if d in lowered}) >= 2 and "?" in lowered


def classify_turn(rec: RunRecord, candidates: list[str]) -> Turn:
    """Deduce lo que hizo el agente en un turno a partir de sus llamadas a tools."""
    mesa = [c for c in rec.tool_calls if c.name.startswith(f"mcp__{SERVER_NAME}__")]
    names = [c.name.removeprefix(f"mcp__{SERVER_NAME}__") for c in mesa]
    looked_up = any(c.name == FIND for c in mesa)
    asked_id = asks_for_identifier("\n".join(rec.texts))
    cut = rec.budget_exceeded
    # El tope de gasto también marca is_error en el SDK: es un corte, no un error de la ejecución.
    error = rec.is_error and not rec.budget_exceeded
    escalate_at = next((i for i, c in enumerate(mesa) if c.name == ESCALATE), None)
    if escalate_at is not None:
        # 5.2-S2: una petición explícita se respeta sin investigar primero; cuenta lo que ocurre ANTES de escalar.
        action = "escalate_after_investigating" if escalate_at > 0 else "escalate_now"
        return Turn(action, looked_up, names, asked_id, cut, error)
    # 5.2-S5: elegir a uno de los homónimos (verificarlo o listar sus tickets) es adivinar por heurística.
    guessed = any(c.name in (VERIFY, LIST_TICKETS) and c.input.get("user_id") in candidates for c in mesa)
    return Turn("guessed_identity" if guessed else "no_escalation", looked_up, names, asked_id, cut, error)


def is_correct(kind: str, first: Turn, second: Turn | None = None) -> bool:
    """Puntúa un caso frente a la acción que pide su tipo (5.2)."""
    if kind == "explicit_human":
        return first.action == "escalate_now"
    if kind == "frustration":
        # Ofrece resolver primero; solo si el cliente insiste en una persona, escala (5.2-K2, S3).
        return first.action == "no_escalation" and second is not None and second.action == "escalate_now"
    if kind in ("policy_gap", "no_progress"):
        # Escalar con o sin una búsqueda previa: el vacío de política (5.2-S4) y la imposibilidad de avanzar (5.2-K1).
        return first.action in ("escalate_now", "escalate_after_investigating")
    if kind == "ambiguous_user":
        # No elige a nadie ni escala, y además pide un identificador: acertar «sin hacer nada» no es acertar (5.2-S5).
        return first.action == "no_escalation" and first.asked_id
    raise ValueError(f"tipo desconocido: {kind}")


class SessionError(RuntimeError):
    """La ejecución no puede medirse (sin sesión): se avisa y se sale, no se mide como un resultado."""


def not_logged_in(rec: RunRecord) -> bool:
    """Sin sesión de Claude Code ni API key el agente responde «Not logged in»: no es un resultado, es un error."""
    return any("Not logged in" in text for text in [*rec.texts, rec.final_text or ""])


def scorable(first: Turn, second: Turn | None) -> bool:
    """Un caso cortado por el tope de gasto, o con error de ejecución, no puntúa: contarlo como fallo atribuiría al agente
    lo que fue del presupuesto o de la ejecución."""
    turns = [first] if second is None else [first, second]
    return not any(t.cut or t.error for t in turns)


def should_insist(case: dict, first: Turn) -> bool:
    """Frustración sencilla: el cliente insiste solo si el agente no escaló y el primer turno terminó con normalidad.

    Sobre una sesión cortada por el tope o con error no se lanza otra consulta: gastaría tras el tope y el caso no puntúa.
    """
    return "followup" in case and first.action == "no_escalation" and not first.cut and not first.error


# Veces la parte igual que puede gastar un caso. Un caso de dos turnos (la frustración) cuesta más que la parte igual,
# y con partes iguales el tope lo cortaba y se contaba como un fallo del agente.
CAP_SHARES = 3.0


def case_cap(budget: float, spent: float, remaining: int) -> float:
    """Tope de un caso: hasta `CAP_SHARES` partes iguales de lo que queda, sin pedir nunca más de lo que queda.

    Es el tope que se le pasa al SDK, que lo comprueba al terminar cada turno: el gasto real de un caso puede pasarse
    un poco, y el total, del tope de `--budget`. No se ha medido cuánto.
    """
    if remaining <= 0:
        return 0.0
    left = max(0.0, budget - spent)
    return min(left, CAP_SHARES * left / remaining)


def partial_note(done: int, total: int) -> str | None:
    return None if done >= total else f"[aviso] medida parcial: se ejecutaron {done} de {total} casos (presupuesto agotado)"


def error_note(count: int) -> str | None:
    return None if count == 0 else f"[aviso] {count} casos con error de ejecución: no puntúan"


def cut_note(count: int) -> str | None:
    return None if count == 0 else f"[aviso] {count} casos cortados por el tope de gasto: no puntúan"


def rates_by_kind(rows: list[tuple[str, bool]]) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for kind, ok in rows:
        hits, total = result.get(kind, (0, 0))
        result[kind] = (hits + ok, total + 1)
    return result


def overall(rows: list[tuple[str, bool]]) -> tuple[int, int]:
    return sum(ok for _, ok in rows), len(rows)


def rate_text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}" if rate[1] else "sin datos"


# --- Confianza autodeclarada (variante `confianza`) -----------------------------------


def declared_confidence(text: str | None) -> int | None:
    match = re.search(r"CONFIANZA:\s*(\d{1,3})", text or "", re.IGNORECASE)
    value = int(match.group(1)) if match else None
    return value if value is not None and value <= 100 else None


def confidence_of(rec: RunRecord) -> int | None:
    """La confianza que el agente declaró en el turno: la línea suele ir antes de la tool, no en el texto final."""
    return declared_confidence("\n".join(rec.texts))


def mean_confidence(rows: list[tuple[bool, int | None]]) -> dict[str, float | None]:
    """Confianza media declarada en los aciertos y en los fallos: si no los separa, no sirve de criterio (5.2-K3)."""

    def mean(values: list[int]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    return {
        "aciertos": mean([c for ok, c in rows if ok and c is not None]),
        "fallos": mean([c for ok, c in rows if not ok and c is not None]),
    }


# --- Proxy de sentimiento (parte determinista, 5.2-K3) --------------------------------

# Raíces de palabras que delatan enfado. Lista inventada para la demostración (inferencia propia).
NEGATIVE_STEMS = ("hart", "desesper", "desastre", "no me sirve", "no me convence", "fatal", "horrible", "inaceptable")


def negative_sentiment(text: str) -> int:
    lowered = text.lower()
    return sum(stem in lowered for stem in NEGATIVE_STEMS)


def proxy_action(text: str) -> str:
    """Lo que haría un agente que decide por el tono: escala si hay tono negativo, si no resuelve."""
    return "escalate" if negative_sentiment(text) >= 1 else "resolve"


def proxy_should_escalate(kind: str) -> bool:
    return kind in ("explicit_human", "policy_gap", "no_progress")


def proxy_rows(cases: list[dict[str, Any]], labels: dict[str, Any]) -> list[tuple[str, str, bool]]:
    rows = []
    for case in cases:
        kind = labels[case["case_id"]]["kind"]
        action = proxy_action(case["text"])
        rows.append((kind, action, (action == "escalate") == proxy_should_escalate(kind)))
    return rows


def proxy_score(rows: list[tuple[str, str, bool]]) -> tuple[int, int]:
    return sum(ok for *_, ok in rows), len(rows)


# --- Ejecución ------------------------------------------------------------------------


def run_proxy() -> int:
    cases, labels = load("escalamiento_casos.json"), load("escalamiento_casos_etiquetas.json")
    print("=== parte proxy (sin modelo): decidir por el tono ===")
    for case, (kind, action, ok) in zip(cases, proxy_rows(cases, labels)):
        print(f"[{case['case_id']}] {kind:<15} proxy={action:<8} {'acierta' if ok else 'FALLA'} · {case['text'][:70]}")
    print(f"[medida] el proxy de sentimiento acierta {rate_text(proxy_score(proxy_rows(cases, labels)))} casos")
    return 0


async def run_case(case: dict, label: dict, model: str, system_prompt: str, cap: float) -> tuple[bool, Turn, Turn | None, float, int | None]:
    state = HelpdeskState()
    # `find_employee_by_name` solo existe para este módulo (`lookup=True`); el escalamiento es de texto libre
    # porque el caso no trae ticket ni empleado verificado que rellenar en un handoff estructurado.
    server = build_server(state, handoff="free_text", lookup=True)
    options = isolated_options(
        max_budget_usd=cap,  # el tope es de toda la ejecución, repartido entre casos
        model=model,
        system_prompt=system_prompt,
        mcp_servers={SERVER_NAME: server},
        tools=[],
        allowed_tools=[tool_name(n) for n in ("find_employee_by_name", "verify_employee", "list_employee_tickets", "search_kb", "escalate_to_human")],
        # `process_reimbursement` y `get_ticket` existen en el servidor pero no vienen al caso: al no estar en
        # `allowed_tools` no se pre-aprueban, y una llamada a ellas saldría denegada en el registro.
        max_turns=8,  # red de seguridad
    )
    candidates = label.get("candidates", [])
    async with ClaudeSDKClient(options=options) as client:
        await client.query(case["text"])
        first_rec = await record(client.receive_response(), echo=False)
        if not_logged_in(first_rec):
            # Sin esto, una ejecución sin credencial se mediría como «ningún caso escala», sin un solo error.
            raise SessionError("el agente responde «Not logged in»: abre sesión en Claude Code o define ANTHROPIC_API_KEY")
        first = classify_turn(first_rec, candidates)
        second, cost = None, first_rec.cost_usd or 0.0
        # Frustración sencilla: si no escaló, el cliente insiste y se comprueba que entonces sí escala (5.2-K2).
        if should_insist(case, first):
            await client.query(case["followup"])
            second_rec = await record(client.receive_response(), echo=False)
            second = classify_turn(second_rec, candidates)
            # El SDK da el coste acumulado de la sesión: la segunda consulta ya incluye la primera.
            cost = second_rec.cost_usd or cost
    ok = is_correct(label["kind"], first, second)
    return ok, first, second, cost, confidence_of(first_rec)


async def main_async() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTS, default="agente", help="`proxy` no usa el modelo")
    parser.add_argument(
        "--rol-modelo", choices=MODEL_ROLES, default="agent",
        help="rol del modelo (por defecto agent, Haiku 5.5); enforcement usa un modelo anterior si la señal no se ve",
    )
    args = parser.parse_args()
    if args.parte == "proxy":
        return run_proxy()

    print(credentials.describe())
    model = report_model(args.rol_modelo)
    budget = report_budget(args.budget, args.rol_modelo)
    cases, labels = load("escalamiento_casos.json"), load("escalamiento_casos_etiquetas.json")
    system_prompt = build_system_prompt(args.anti)
    print(f"\n=== variante {args.anti or 'criterios + ejemplos'} · {len(cases)} casos × {args.repeat} ===\n[prompt]\n{system_prompt}\n")

    rows: list[tuple[str, bool]] = []
    confidence_rows: list[tuple[bool, int | None]] = []
    total = len(cases) * args.repeat
    spent, remaining, executed, cut_cases, error_cases, exhausted = 0.0, total, 0, 0, 0, False
    for run in range(1, args.repeat + 1):
        for case in cases:
            cap = case_cap(budget, spent, remaining)
            if cap <= 0:
                print(f"[corte] presupuesto agotado (${spent:.4f} de ${budget})")
                exhausted = True
                break
            label = labels[case["case_id"]]
            try:
                ok, first, second, cost, confidence = await run_case(case, label, model, system_prompt, cap)
            except SessionError as exc:
                # Sin credencial no hay medida: se sale con el motivo, sin traza y sin contar nada como «no escala».
                print(f"[error] {exc}")
                return 2
            spent += cost
            remaining -= 1
            executed += 1
            after = f" → tras insistir: {second.action}" if second else ""
            asked = f" · pidió ID: {'sí' if first.asked_id else 'no'}" if label["kind"] == "ambiguous_user" else ""
            if not scorable(first, second):
                is_error = first.error or (second is not None and second.error)
                cut_cases, error_cases = cut_cases + (not is_error), error_cases + is_error
                reason = "ERROR de ejecución" if is_error else "CORTADO por el tope de gasto"
                print(f"[{run}·{case['case_id']}] {label['kind']:<15} {reason} (no puntúa)")
                continue
            rows.append((label["kind"], ok))
            confidence_rows.append((ok, confidence))
            print(f"[{run}·{case['case_id']}] {label['kind']:<15} {first.action}{after}{asked} · {'correcto' if ok else 'INCORRECTO'}")
        if exhausted:
            break
    for note in (cut_note(cut_cases), error_note(error_cases), partial_note(executed, total)):
        if note:
            print(note)

    by_kind = " · ".join(f"{kind} {rate_text(rate)}" for kind, rate in rates_by_kind(rows).items())
    print(f"\n[medida] correctos {rate_text(overall(rows))} · {by_kind} · coste≈${spent:.4f}")
    if args.anti == "confianza":
        print(f"[confianza declarada] media {mean_confidence(confidence_rows)} (si no separa aciertos de fallos, no sirve de criterio)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
