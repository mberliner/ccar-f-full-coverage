"""Validación y reintento con error concreto: cuándo un reintento corrige y cuándo es inútil.

CONCEPTO [TS 4.4-K1…K4, S1…S4]: validar la extracción sin modelo (formato, enum, campos
obligatorios y total calculado frente a total declarado), reintentar con el error
**concreto** (campo, valor y regla), parar cuando el dato no está en la fuente, y anotar
`detected_pattern` en cada fallo para agrupar las causas.

[BORRADOR de Sonnet 5.5: los textos de QUÉ DICE LA GUÍA y ANTI-PATRÓN los reescribe
Opus 5.5 (paso A4 del diseño de la entrega 3) contra la Task Statement 4.4.]

QUÉ DICE LA GUÍA:
- Un fallo de validación se corrige reenviando al modelo la extracción original con el
  error **específico** (qué campo, qué valor, qué regla), no con un «inténtalo de nuevo» (4.4).
- El reintento sirve cuando el error es de formato o de estructura y el dato está en el
  documento; es inútil cuando la información no está en la fuente: no hay nada que
  corregir y el modelo la inventará (4.4).
- Un total calculado (suma de líneas) frente al total declarado detecta una extracción
  mala o un documento que no cuadra; se marca con `conflict_detected` (4.4).
- Un `detected_pattern` en cada fallo permite agrupar las causas y mejorar el prompt o
  el esquema, no solo parchear caso a caso (4.4).

POR QUÉ IMPORTA (inferencia propia): un reintento cuesta una llamada; uno inútil cuesta
dinero y, como se mide aquí, produce datos falsos que pasan la validación de formato.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: reintentar con un mensaje genérico (`--anti reintento_generico`) y
  reintentar hasta el tope también cuando el dato no existe (`--anti insistir`).
- Lo observado aquí (README y `docs/hallazgos.md`): con Haiku 4.5 y un esquema sin regla
  de fecha, 17 de 36 primeros intentos salen con la fecha mal escrita; el reintento
  concreto corrige 12 de 12 y el genérico 2 de 12. Con Haiku 5.5 no hay nada que
  reintentar (0 de 36), por eso este módulo usa el rol `enforcement`. Al insistir por un
  pedido que no existe, ambos modelos acaban escribiendo uno inventado.
- Inferencia propia: un valor inventado con el formato correcto pasa el validador de
  formato; solo lo delata compararlo con la etiqueta (aquí) o con la fuente (en producción).

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 08.

INTRODUCE: TS 4.4-K1, TS 4.4-K2, TS 4.4-K3, TS 4.4-K4, TS 4.4-S1, TS 4.4-S2, TS 4.4-S3, TS 4.4-S4

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
    pattern: str  # `detected_pattern`: agrupa las causas (date_format, enum_value, missing_required, po_format, total_mismatch)
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
    total = calculated_total(data)
    stated = data.get("stated_total")
    conflict = False
    if total is not None and isinstance(stated, (int, float)) and abs(stated - total) > TOTAL_TOLERANCE:
        conflict = True
        failures.append(
            Failure("total_mismatch", "stated_total", stated, f"la suma de las líneas (cantidad × precio unidad) es {total:.2f} y el total declarado es {stated:.2f}; revisa cantidades, precios y total contra el documento")
        )
    return Validation(failures, total, conflict)


# Dónde buscar en el texto, sin modelo, un dato que el validador exige. Sin patrón: se supone que está.
SOURCE_PATTERNS = {
    "po_number": re.compile(r"PO-\d{4}"),
    "issue_date": re.compile(
        r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}-\d{1,2}-\d{4}|\d{1,2} de [a-záéíóú]+ de \d{4}|\d{1,2} [A-Z][a-z]{2} \d{4}"
    ),
}


def source_has(field_name: str, text: str) -> bool:
    """¿Aparece en el documento algo que pueda ser ese dato? Si no, un reintento no tiene qué corregir."""
    pattern = SOURCE_PATTERNS.get(field_name)
    return True if pattern is None else bool(pattern.search(text))


# --- Mensajes de error (4.4: específico frente a genérico) ----------------------------------------


def concrete_message(failures: list[Failure]) -> str:
    """El error concreto: campo, valor devuelto y regla que incumple."""
    return " ".join(f"{f.field}={f.value!r} no es válido: {f.rule}. Corrige solo eso." for f in failures)


def generic_message() -> str:
    return "Inténtalo de nuevo."


def message_for(mode: str | None, failures: list[Failure]) -> str:
    return generic_message() if mode == "reintento_generico" else concrete_message(failures)


# --- Decisión de reintento ---------------------------------------------------------------------------


@dataclass
class RetryPlan:
    retry: list[Failure] = field(default_factory=list)
    stop: list[tuple[Failure, str]] = field(default_factory=list)  # (fallo, motivo)


def plan_retry(failures: list[Failure], doc_text: str, round_index: int, mode: str | None) -> RetryPlan:
    """Qué fallos se reintentan y cuáles se dejan marcados.

    Correcta: un dato que no está en la fuente no se reintenta (se marca); un total que no cuadra se
    reintenta una vez y después se marca como conflicto; el tope es una red de seguridad.
    `insistir`: reintenta todo hasta su tope, exista o no el dato.
    """
    plan = RetryPlan()
    cap = MAX_INSISTIR if mode == "insistir" else MAX_RETRIES
    for failure in failures:
        if mode != "insistir":
            if failure.pattern == "missing_required" and not source_has(failure.field, doc_text):
                plan.stop.append((failure, "missing_in_source"))
                continue
            if failure.pattern == "total_mismatch" and round_index >= 1:
                plan.stop.append((failure, "conflict_detected"))
                continue
        if round_index >= cap:
            plan.stop.append((failure, "retry_cap"))
        else:
            plan.retry.append(failure)
    return plan


def group_by_pattern(failures: list[Failure]) -> dict[str, int]:
    """Fallos agrupados por `detected_pattern`: las causas, no los casos."""
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
    verdict: str  # corregido | persiste | inventado


@dataclass
class Outcome:
    attempts: list[dict] = field(default_factory=list)
    failures_by_round: list[list[Failure]] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)
    usages: list[Any] = field(default_factory=list)
    retries: int = 0
    marked_missing: list[str] = field(default_factory=list)
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
    round_index = 0
    while True:
        validation = validate(data)
        outcome.attempts.append(data)
        outcome.failures_by_round.append(validation.failures)
        active = [f for f in validation.failures if f.key not in settled]
        if not active:
            break
        plan = plan_retry(active, doc_text, round_index, mode)
        for failure, reason in plan.stop:
            settled[failure.key] = reason
            if reason == "missing_in_source":
                outcome.marked_missing.append(failure.field)
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
    outcome.stopped_by = reasons[0] if reasons else "valido"
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
        "marcados": sum(len(o.marked_missing) for o in outcomes),
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
                    print(f"  {doc_id}: fallos={first or 'ninguno'} · reintentos={outcome.retries} {verdicts or ''} · parada={outcome.stopped_by} · marcados={outcome.marked_missing or '-'}")
            summary = summarize_outcomes(outcomes)
            cost = sum(retry_cost(o, model) for o in outcomes)
            all_first = [f for o in outcomes for f in o.failures_by_round[0]]
            print(
                f"[{run}/{args.repeat}] causas de los primeros intentos {group_by_pattern(all_first) or 'ninguna'} · reintentos {summary['reintentos']} "
                f"(útiles {summary['utiles']} · inútiles {summary['inutiles']} · inventaron {summary['inventaron']}) · "
                f"marcados sin dato {summary['marcados']} · conflictos {summary['conflictos']} · coste de los reintentos ${cost:.4f}"
            )
    except BudgetExceeded as exc:
        print(f"[corte] {exc}")
        return 1
    print(f"\n[fin] coste=${guard.spent:.4f} de ${budget}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
