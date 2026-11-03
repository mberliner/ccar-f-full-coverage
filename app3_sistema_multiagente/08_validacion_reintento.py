"""Validación y reintento con error concreto: cuándo un reintento corrige y cuándo es inútil.

CONCEPTO [TS 4.4-K1, K2, K4 · S1, S2, S4]: validar la extracción sin modelo (formato,
enum, campos obligatorios y total calculado frente a total declarado), reintentar con el
error **concreto** (campo, valor y regla) y parar cuando el dato no está en la fuente.

QUÉ DICE LA GUÍA:
- Reintento con el error como retroalimentación: en el reintento se añaden al prompt
  los errores de validación concretos, para orientar al modelo hacia la corrección
  (4.4-K1). La petición de seguimiento lleva el documento original, la extracción que
  falló y esos errores (4.4-S1).
- El reintento tiene un límite: no sirve cuando la información no está en el documento
  fuente, y sí cuando el fallo es de formato o de estructura de la salida (4.4-K2). Hay
  que saber distinguir los dos casos antes de reintentar, por ejemplo cuando el dato
  solo está en otro documento que no se ha proporcionado (4.4-S2).
- Los errores semánticos (valores que no suman, un dato en el campo equivocado) son
  distintos de los de sintaxis del esquema, que la tool ya elimina (4.4-K4). Para
  detectar los primeros, se extrae un `calculated_total` junto al `stated_total` y se
  añade un booleano `conflict_detected` cuando la fuente es incoherente (4.4-S4).

POR QUÉ IMPORTA (inferencia propia): un reintento cuesta una llamada más por documento.
El que no puede funcionar cuesta lo mismo y además invita al modelo a producir un valor
que cumple el formato, así que el fallo deja de verse.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Reintentar sin decir qué falló (`--anti reintento_generico`).
  - Reintentar un dato que el documento no contiene, en vez de marcarlo como ausente
    (`--anti insistir`).
  - Dar una extracción por buena porque cumple el esquema, sin comprobar si sus valores
    cuadran entre sí.
- Inferencias propias, con lo observado aquí (cifras en el README y en
  `docs/hallazgos.md`):
  - Un valor inventado con el formato correcto pasa el validador. Solo lo delata la
    comparación con la etiqueta, aquí, o con la fuente, en producción.
  - Pedir que se revise un total que no cuadra por culpa del documento invita al modelo
    a cambiar el total declarado para que cuadre. Por eso el conflicto se marca tras un
    único reintento.
  - Cada fallo de validación lleva su causa (`pattern`) y la salida los agrupa, para
    corregir el prompt o el esquema en lugar de parchear documento a documento. El
    `detected_pattern` de la guía es otra cosa: analiza qué hallazgos de una revisión
    descartan los desarrolladores (ver TS 4.4-K3, que introduce `app3/11`).
  - La señal depende del modelo: con Haiku 5.5 no hubo fallos de formato que reintentar,
    así que el módulo usa el rol `enforcement` (Haiku 4.5), y `--rol-modelo agent` lo
    comprueba.
  - El reintento se envía como resultado de error de la tool sobre la llamada fallida,
    con el documento original en la misma conversación.
  - El `calculated_total` lo suma el código a partir de las líneas extraídas, en lugar
    de pedírselo al modelo. Se compara con el `stated_total` igual que en la guía, pero
    la suma no depende del modelo.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 08.

INTRODUCE: TS 4.4-K1, TS 4.4-K2, TS 4.4-K4, TS 4.4-S1, TS 4.4-S2, TS 4.4-S4

Uso: `uv run python app3_sistema_multiagente/08_validacion_reintento.py [--anti reintento_generico|insistir] [--rol-modelo agent|enforcement] [--repeat N]`
"""

import importlib.util
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials  # noqa: E402
from harness.budget import BudgetExceeded, CostGuard, cost_of  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402


def load_sibling(filename: str) -> Any:
    """Carga otro módulo de esta carpeta (su nombre empieza por un dígito y no admite `import`)."""
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location("_app3_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# `07` define el esquema, la petición y la puntuación sobre los que trabaja este módulo.
ext = load_sibling("07_extraccion_schema.py")

ANTI_VARIANTS = ["reintento_generico", "insistir"]
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PO_FORMAT = re.compile(r"^PO-\d{4}$")
# Cuántos reintentos permite la correcta. Es una red de seguridad: lo que para el bucle es la decisión
# de `plan_retry` (dato ausente, conflicto en la fuente), no este número.
MAX_RETRIES = 2
# El anti-patrón `insistir` llega más lejos: reintenta hasta aquí aunque el dato no exista.
MAX_INSISTIR = 4
TOTAL_TOLERANCE = 0.01

# --- Validador (4.4: sin modelo) ---------------------------------------------------------------


@dataclass(frozen=True)
class Failure:
    pattern: str  # patrón de fallo: agrupa las causas (date_format, enum_value, missing_required, po_format, total_mismatch)
    field: str
    value: Any
    rule: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.pattern, self.field)


@dataclass
class Validation:
    failures: list[Failure]
    calculated_total: float | None
    conflict_detected: bool


def calculated_total(data: dict) -> float | None:
    """Suma de cantidad × precio de las líneas con precio; None si ninguna lo trae."""
    priced = [i for i in data.get("line_items") or [] if isinstance(i, dict) and isinstance(i.get("unit_price"), (int, float)) and isinstance(i.get("quantity"), (int, float))]
    return round(sum(i["quantity"] * i["unit_price"] for i in priced), 2) if priced else None


def validate(data: dict) -> Validation:
    """Comprueba la extracción con reglas de código. No llama al modelo."""
    failures: list[Failure] = []
    doc_type = data.get("doc_type")
    if doc_type not in ext.DOC_TYPES:
        failures.append(Failure("enum_value", "doc_type", doc_type, f"debe ser uno de {ext.DOC_TYPES}"))
    issue_date = data.get("issue_date")
    if issue_date is not None:
        try:
            valid = bool(ISO_DATE.match(str(issue_date))) and date.fromisoformat(str(issue_date)) is not None
        except ValueError:
            valid = False
        if not valid:
            failures.append(Failure("date_format", "issue_date", issue_date, "debe tener formato ISO YYYY-MM-DD"))
    po = data.get("po_number")
    if doc_type == "invoice" and po in (None, ""):
        failures.append(Failure("missing_required", "po_number", po, "las facturas de compra deben citar su número de pedido (PO-nnnn)"))
    elif po not in (None, "") and not PO_FORMAT.match(str(po)):
        failures.append(Failure("po_format", "po_number", po, "el número de pedido tiene la forma PO-nnnn"))
    # Todo documento de compra lleva número; si no sale, hay que saber si el documento no lo trae o lo remite a otro.
    if data.get("document_number") in (None, ""):
        failures.append(Failure("missing_required", "document_number", data.get("document_number"), "todo documento de compra lleva su número (factura, albarán, garantía, presupuesto)"))
    total = calculated_total(data)
    stated = data.get("stated_total")
    conflict = False
    if total is not None and isinstance(stated, (int, float)) and abs(stated - total) > TOTAL_TOLERANCE:
        conflict = True
        failures.append(
            Failure("total_mismatch", "stated_total", stated, f"la suma de las líneas (cantidad × precio unidad) es {total:.2f} y el total declarado es {stated:.2f}")
        )
    return Validation(failures, total, conflict)


# Dónde buscar en el texto, sin modelo, un dato que el validador exige. Sin patrón: se supone que está.
SOURCE_PATTERNS = {
    "po_number": re.compile(r"PO-\d{4}"),
    # Un número de documento tiene letras, guion y cifras (F-2026-0412, AL-5521, G-2026-077, P-2026-310).
    "document_number": re.compile(r"\b[A-Z]{1,2}-\d{2,4}(?:-\d+)?\b"),
    "issue_date": re.compile(
        r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}-\d{1,2}-\d{4}|\d{1,2} de [a-záéíóú]+ de \d{4}|\d{1,2} [A-Z][a-z]{2} \d{4}"
    ),
}


# El documento no trae el dato pero dice dónde está: otro documento que no se ha proporcionado (4.4-S2).
EXTERNAL_REFERENCE = re.compile(r"\b(?:ver|véase|vea|según) (?:el )?(?:adjunto|anexo)|\bsee (?:the )?attach", re.IGNORECASE)


def source_has(field_name: str, text: str) -> bool:
    """¿Aparece en el documento algo que pueda ser ese dato? Si no, un reintento no tiene qué corregir."""
    pattern = SOURCE_PATTERNS.get(field_name)
    return True if pattern is None else bool(pattern.search(text))


def source_status(field_name: str, text: str) -> str:
    """`present` (el dato está), `external` (no está, pero el texto remite a otro documento) o `missing` (no está en ninguna parte).

    Búsqueda en el texto, sin modelo. Los dos últimos no se reintentan, cada uno con su causa.
    """
    if source_has(field_name, text):
        return "present"
    return "external" if EXTERNAL_REFERENCE.search(text) else "missing"


# --- Mensajes de error (4.4: específico frente a genérico) ----------------------------------------


def concrete_message(failures: list[Failure]) -> str:
    """El error concreto: campo, valor devuelto y regla que incumple."""
    return " ".join(f"{f.field}={f.value!r} no es válido: {f.rule}. Corrige solo eso." for f in failures)


def generic_message() -> str:
    return "Inténtalo de nuevo."


def message_for(mode: str | None, failures: list[Failure]) -> str:
    if mode == "reintento_generico":
        return generic_message()
    text = concrete_message(failures)
    # Solo `insistir` reintenta un total que no cuadra, y lo hace pidiendo que se revise: invita a cambiar datos.
    if mode == "insistir" and any(f.pattern == "total_mismatch" for f in failures):
        text += " Revisa cantidades, precios y total contra el documento."
    return text


# --- Decisión de reintento ---------------------------------------------------------------------------


@dataclass
class RetryPlan:
    retry: list[Failure] = field(default_factory=list)
    stop: list[tuple[Failure, str]] = field(default_factory=list)  # (fallo, motivo)


def plan_retry(failures: list[Failure], doc_text: str, round_index: int, mode: str | None) -> RetryPlan:
    """Qué fallos se reintentan y cuáles se dejan marcados.

    Correcta: un dato que no está en la fuente no se reintenta, se marca (con su causa: no existe o
    remite a otro documento); un total que no cuadra tampoco, porque el documento es incoherente y se
    marca `conflict_detected` (4.4-S4); el tope es una red de seguridad.
    `insistir`: reintenta todo hasta su tope, exista o no el dato y cuadre o no el total.
    """
    plan = RetryPlan()
    cap = MAX_INSISTIR if mode == "insistir" else MAX_RETRIES
    for failure in failures:
        if mode != "insistir":
            if failure.pattern == "missing_required":
                status = source_status(failure.field, doc_text)
                if status != "present":
                    plan.stop.append((failure, "external_reference" if status == "external" else "missing_in_source"))
                    continue
            if failure.pattern == "total_mismatch":
                plan.stop.append((failure, "conflict_detected"))
                continue
        if round_index >= cap:
            plan.stop.append((failure, "retry_cap"))
        else:
            plan.retry.append(failure)
    return plan


def group_by_pattern(failures: list[Failure]) -> dict[str, int]:
    """Fallos agrupados por patrón de fallo: las causas, no los casos."""
    return dict(Counter(f.pattern for f in failures))


# --- Conversación del reintento ----------------------------------------------------------------------------


def retry_messages(doc_text: str, history: list[tuple[str, dict, str]]) -> list[dict]:
    """Mensajes para el reintento: el documento, y por cada intento fallido, la llamada y el error como `tool_result`."""
    messages = ext.build_request(doc_text, tools=[], mode="auto", model="")["messages"]
    for tool_use_id, tool_input, error_text in history:
        messages.append({"role": "assistant", "content": [{"type": "tool_use", "id": tool_use_id, "name": ext.TOOL_NAME, "input": tool_input}]})
        messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": error_text, "is_error": True}]})
    return messages


# --- Bucle -----------------------------------------------------------------------------------------------------


@dataclass
class Effect:
    failure: Failure
    verdict: str  # corregido | persiste | falta | inventado


@dataclass
class Outcome:
    attempts: list[dict] = field(default_factory=list)
    failures_by_round: list[list[Failure]] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)
    usages: list[Any] = field(default_factory=list)
    retries: int = 0
    marked_missing: list[str] = field(default_factory=list)  # el dato no está en el documento
    marked_external: list[str] = field(default_factory=list)  # el documento remite a otro («Ver adjunto»)
    conflict_detected: bool = False
    stopped_by: str = "valido"


def retry_effect(failure: Failure, new_data: dict, new_failures: list[Failure], label: dict) -> str:
    """Qué hizo el reintento con un fallo, juzgado contra la etiqueta (solo para medir; el bucle no la ve)."""
    if any(f.key == failure.key for f in new_failures):
        return "persiste"
    if failure.pattern == "total_mismatch":
        # El documento no cuadra: si el modelo hizo que cuadre, cambió datos para satisfacer al validador.
        return "inventado" if label["total_mismatch"] else "corregido"
    name = failure.field
    want = label["doc_type"] if name == "doc_type" else label["fields"].get(name)
    got = new_data.get(name)
    if want is None:
        return "inventado" if got is not None else "corregido"
    if got is None:
        return "falta"  # el reintento dejó vacío un campo que la etiqueta sí tiene: ni corregido ni inventado
    return "corregido" if ext._same(got, want) else "inventado"


def _call(create: Any, request: dict, messages: list[dict], outcome: Outcome) -> tuple[dict, str]:
    response = create(**{**request, "messages": messages})
    outcome.usages.append(response.usage)
    block = next((b for b in response.content if b.type == "tool_use"), None)
    return (dict(block.input), block.id) if block else ({}, "")


def process_document(create: Any, doc_text: str, label: dict, mode: str | None, *, tool: dict, model_name: str) -> Outcome:
    """Extrae, valida y reintenta según `mode` (None = correcta, `reintento_generico` o `insistir`)."""
    request = ext.build_request(doc_text, tools=[tool], mode="forzada", model=model_name)
    outcome = Outcome()
    history: list[tuple[str, dict, str]] = []
    data, use_id = _call(create, request, request["messages"], outcome)
    settled: dict[tuple[str, str], str] = {}  # fallos que se dejan marcados y ya no se reintentan
    last_stop = "valido"  # el último motivo registrado antes de salir: lo que para el bucle
    round_index = 0
    while True:
        validation = validate(data)
        outcome.attempts.append(data)
        outcome.failures_by_round.append(validation.failures)
        active = [f for f in validation.failures if f.key not in settled]
        if not active:
            # Lo que queda ya estaba marcado: si hay algo, el motivo es el último que se marcó.
            break
        plan = plan_retry(active, doc_text, round_index, mode)
        for failure, reason in plan.stop:
            settled[failure.key] = reason
            last_stop = reason
            if reason == "missing_in_source":
                outcome.marked_missing.append(failure.field)
            elif reason == "external_reference":
                outcome.marked_external.append(failure.field)
        if not plan.retry:
            break
        history.append((use_id, data, message_for(mode, plan.retry)))
        data, use_id = _call(create, request, retry_messages(doc_text, history), outcome)
        outcome.retries += 1
        round_index += 1
        new_failures = validate(data).failures
        outcome.effects += [Effect(f, retry_effect(f, data, new_failures, label)) for f in plan.retry]
    reasons = list(settled.values())
    outcome.conflict_detected = "conflict_detected" in reasons
    outcome.stopped_by = last_stop if reasons else "valido"
    return outcome


def retry_cost(outcome: Outcome, model_name: str) -> float:
    """Coste de las llamadas de reintento (todas menos la primera)."""
    return sum(cost_of(model_name, usage) for usage in outcome.usages[1:])


def summarize_outcomes(outcomes: list[Outcome]) -> dict[str, int]:
    verdicts = Counter(e.verdict for o in outcomes for e in o.effects)
    return {
        "documentos": len(outcomes),
        "reintentos": sum(o.retries for o in outcomes),
        "utiles": verdicts["corregido"],
        "inutiles": verdicts["persiste"],
        "inventaron": verdicts["inventado"],
        "faltan": verdicts["falta"],
        "marcados": sum(len(o.marked_missing) for o in outcomes),
        "remiten_a_otro_documento": sum(len(o.marked_external) for o in outcomes),
        "conflictos": sum(o.conflict_detected for o in outcomes),
    }


# --- Ejecución -----------------------------------------------------------------------------------------------------


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    # Haiku 5.5 no falló el formato en 36 intentos: sin fallos no hay qué reintentar. Por defecto, Haiku 4.5.
    parser.add_argument("--rol-modelo", choices=["agent", "enforcement"], default="enforcement", help="`enforcement` es Haiku 4.5 (por defecto)")
    args = parser.parse_args()
    print(credentials.describe())
    credentials.require_api_key()
    model = report_model(args.rol_modelo)
    budget = report_budget(args.budget, args.rol_modelo)
    import anthropic

    # Las descripciones sin regla de fecha dejan que aparezcan fallos de formato reales en el primer intento.
    tool = ext.build_tool("correcta", normalization=False)
    guard = CostGuard(model, budget)  # el tope es de toda la ejecución, repartido entre documentos y repeticiones
    create = ext.make_create(anthropic.Anthropic(), guard)
    mode = args.anti
    print(f"\n=== validación y reintento · variante {mode or 'correcta'} · {len(ext.DOCS)} documentos × {args.repeat} ===")
    print("[esperado] el reintento con error concreto corrige los fallos de formato; no hay nada que corregir en un dato que no está en el documento")
    try:
        for run in range(1, args.repeat + 1):
            outcomes = []
            for doc_id, text in ext.DOCS.items():
                outcome = process_document(create, text, ext.LABELS[doc_id], mode, tool=tool, model_name=model)
                outcomes.append(outcome)
                first = group_by_pattern(outcome.failures_by_round[0])
                verdicts = [f"{e.failure.field}:{e.verdict}" for e in outcome.effects]
                if first or outcome.retries:
                    print(f"  {doc_id}: fallos={first or 'ninguno'} · reintentos={outcome.retries} {verdicts or ''} · parada={outcome.stopped_by} · marcados={outcome.marked_missing or '-'} · remite a otro documento={outcome.marked_external or '-'}")
            summary = summarize_outcomes(outcomes)
            cost = sum(retry_cost(o, model) for o in outcomes)
            all_first = [f for o in outcomes for f in o.failures_by_round[0]]
            print(
                f"[{run}/{args.repeat}] causas de los primeros intentos {group_by_pattern(all_first) or 'ninguna'} · reintentos {summary['reintentos']} "
                f"(útiles {summary['utiles']} · inútiles {summary['inutiles']} · inventaron {summary['inventaron']} · dejaron vacío {summary['faltan']}) · "
                f"marcados sin dato {summary['marcados']} · remiten a otro documento {summary['remiten_a_otro_documento']} · conflictos {summary['conflictos']} · coste de los reintentos ${cost:.4f}"
            )
    except BudgetExceeded as exc:
        print(f"[corte] {exc}")
        return 1
    print(f"\n[fin] coste=${guard.spent:.4f} de ${budget}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
