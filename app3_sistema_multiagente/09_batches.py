"""Message Batches API: lotes con `custom_id`, ventana frente a SLA, fallidos y troceo.

CONCEPTO [TS 4.5-K1…K4, S1…S4]: enviar las peticiones de extracción de `07` como un lote
(mitad de precio, procesado asíncrono de hasta 24 h y sin SLA de latencia), emparejar los
resultados por `custom_id`, reenviar solo los fallidos (partiendo los documentos demasiado
largos), decidir qué cabe en batch y qué tiene que ir síncrono, y probar antes con una
muestra síncrona.

QUÉ DICE LA GUÍA:
- La Message Batches API ahorra el 50 % y procesa en una ventana de hasta 24 h, sin
  garantía de latencia (4.5-K1).
- Encaja en trabajos que no bloquean a nadie y toleran la espera (informes nocturnos,
  auditorías semanales, generación nocturna de tests). No encaja en un flujo que bloquea,
  como una comprobación previa al merge (4.5-K2). Por eso se elige la API según la latencia
  que exige el flujo: síncrona para lo que bloquea y batch para el análisis nocturno o
  semanal (4.5-S1).
- Dentro de una petición del lote no hay tool calling de varios turnos: no se puede
  ejecutar una tool a mitad y devolverle el resultado (4.5-K3).
- `custom_id` es lo que relaciona cada petición del lote con su respuesta (4.5-K4).
- La frecuencia de envío se calcula a partir del SLA. Por ejemplo, con 24 h de procesado,
  enviar cada 4 h garantiza un SLA de 30 h (4.5-S2).
- Ante los fallos, se reenvían solo los documentos que fallaron, localizados por su
  `custom_id` y con el cambio que haga falta, como trocear los que superaron el límite de
  contexto (4.5-S3).
- Antes de procesar un volumen grande en lote, se afina el prompt con una muestra: sube
  el acierto a la primera y baja el coste de los reenvíos (4.5-S4).

POR QUÉ IMPORTA (inferencia propia): el 50 % solo se ahorra de verdad si el trabajo cabe
en la ventana contando la espera al siguiente envío, y si los fallidos se recuperan sin
repetir el lote entero. Un lote mal planteado se paga entero, porque no se puede cortar
a mitad.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Usar batch en un flujo bloqueante o con un plazo que no admite la ventana.
  - Esperar que el modelo use tools en varios turnos dentro del lote.
  - Emparejar los resultados por posición en vez de por `custom_id` (`--anti por_orden`).
  - Repetir el lote completo cuando fallan unos pocos.
  - Lanzar el volumen entero sin probar el prompt con una muestra (`--sin-muestra`).
- Inferencias propias, con lo observado aquí (cifras en el README y en
  `docs/hallazgos.md`):
  - El plazo tiene que cubrir la espera hasta el siguiente envío, la ventana completa y
    una ventana más por cada reenvío de fallidos. Con 30 h hay que enviar cada 4 h y no
    queda tiempo para reenviar nada (`--ventanas`).
  - Los resultados no llegan en el orden de envío.
  - Una respuesta cortada por `max_tokens` llega como `succeeded`. Para detectar los
    fallidos hay que mirar el `stop_reason`, no solo el tipo de resultado.
  - Un trozo también puede volver a truncarse, y entonces se parte otra vez por la
    mitad, hasta una línea. Al reenviar se manda solo el texto del trozo fallido, y la
    unión no depende del orden en que lleguen los resultados.
  - La muestra es síncrona, usa los mismos parámetros que el lote y compara las
    extracciones con las etiquetas, campo por campo. Por debajo del umbral del código no
    se lanza el lote: afinar el prompt es más barato que reenviar.
  - Una respuesta sin datos (truncada o fallida) no cuenta como cruce de documentos al
    emparejar por posición; el recuento es sobre los documentos que tienen número.
- EN PRODUCCIÓN (no evaluable): los precios y el descuento están en la tabla de
  `harness/budget.py`, que se actualiza a mano. La ventana de 24 h es un máximo: aquí los
  lotes terminaron en minutos, pero no está garantizado.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 09.

INTRODUCE: TS 4.5-K1, TS 4.5-K2, TS 4.5-K3, TS 4.5-K4, TS 4.5-S1, TS 4.5-S2, TS 4.5-S3, TS 4.5-S4

Uso: `uv run python app3_sistema_multiagente/09_batches.py [--ventanas] [--enviar [--sin-muestra]] [--batch-id ID [--reenviar] [--esperar SEGUNDOS] [--anti por_orden]]`
"""

import importlib.util
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
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


# `07` define el esquema, la petición de extracción y la puntuación; este módulo solo cambia cómo se envía.
ext = load_sibling("07_extraccion_schema.py")

ANTI_VARIANTS = ["por_orden"]
# Salida corta a propósito: solo el albarán largo (40 líneas) no cabe, y esa respuesta truncada es el fallido
# que se recupera troceando. Con un valor holgado no habría nada que reenviar.
BATCH_MAX_TOKENS = 600
CHUNK_LINES = 10  # líneas de artículo por trozo al partir un documento largo por primera vez
# Si un trozo vuelve a truncarse, el documento se parte en trozos de la mitad, y así hasta una línea por trozo.
SAMPLE_SIZE = 3  # documentos de la muestra síncrona previa
# Acierto mínimo de la muestra frente a las etiquetas (campos correctos / campos comprobados). Por debajo, el lote
# no se lanza (salvo `--sin-muestra`): hay que afinar el prompt o el esquema antes de pagar el volumen.
SAMPLE_MIN_ACCURACY = 0.85
ACCURACY_FIELDS = ["doc_type", "vendor", "document_number", "issue_date", "po_number", "currency", "stated_total", "line_items"]
# Qué cubre el tope `--budget`: es POR INVOCACIÓN. Con `--enviar` suma la muestra síncrona y la estimación del lote
# (que no se puede cortar a mitad). Con `--batch-id --reenviar`, solo la estimación del reenvío: el lote que se lee
# ya se pagó en otra invocación y no se vuelve a contar.
BUDGET_SCOPE = "por invocación"
BATCH_WINDOW_HOURS = 24  # un lote puede tardar hasta 24 h y no tiene SLA de latencia
ITEM_LINE = re.compile(r"^\d+ x ")
# `<doc>--s<líneas>-c<n>`: el tamaño del trozo viaja en el id, para saber cuánto partir si vuelve a truncarse.
CHUNK_SUFFIX = re.compile(r"--s(\d+)-c(\d+)$")

# --- Construcción del lote (4.5) -----------------------------------------------------------------------


def build_batch_requests(docs: dict[str, str], *, model: str) -> list[dict]:
    """Una petición de extracción por documento, cada una con su `custom_id`.

    Cada petición es de una sola vuelta (un mensaje de usuario): dentro de un lote no se puede
    devolver un `tool_result` y seguir la conversación, así que nada de tools de varios turnos.
    El `custom_id` (letras, cifras, `-` y `_`) es lo único que une cada resultado con su documento.
    """
    tool = ext.build_tool("correcta")
    return [
        {"custom_id": doc_id, "params": ext.build_request(text, tools=[tool], mode="forzada", model=model, max_tokens=BATCH_MAX_TOKENS)}
        for doc_id, text in docs.items()
    ]


# --- Resultados: clasificar y emparejar ------------------------------------------------------------------


@dataclass
class Item:
    custom_id: str
    status: str  # ok | truncated | invalid | errored | expired | canceled
    data: dict | None = None
    usage: Any = None
    error_type: str | None = None


def classify_result(entry: Any) -> Item:
    """Un resultado del lote como `Item`. Un `succeeded` con `max_tokens` o con un JSON fuera del esquema es un fallo."""
    result = entry.result
    if result.type != "succeeded":
        error_type = getattr(getattr(getattr(result, "error", None), "error", None), "type", None)
        return Item(entry.custom_id, result.type, error_type=error_type)
    message = result.message
    block = next((b for b in message.content if b.type == "tool_use"), None)
    data = dict(block.input) if block else None
    item = Item(entry.custom_id, "ok", data, message.usage)
    if message.stop_reason == "max_tokens":
        # La API lo da por «succeeded»: la respuesta se cortó y el `tool_use` está incompleto.
        item.status = "truncated"
    elif data is None or ext.conforms(data, ext.build_tool("correcta")["input_schema"]):
        item.status = "invalid"
    return item


def failed_items(items: list[Item]) -> list[Item]:
    """Los que hay que reenviar, identificados por su `custom_id`."""
    return [item for item in items if item.status != "ok"]


def pair_results(sent_ids: list[str], items: list[Item], *, by: str) -> dict[str, Item]:
    """Une cada documento enviado con su resultado: por `custom_id` (correcto) o por posición (anti-patrón)."""
    if by == "custom_id":
        return {item.custom_id: item for item in items}
    if by == "order":
        # Los resultados no llegan en el orden de envío: emparejar por posición mezcla documentos.
        return dict(zip(sent_ids, items))
    raise ValueError(f"emparejado desconocido: {by}")


def mismatched(paired: dict[str, Item], labels: dict) -> list[str]:
    """Documentos cuyo resultado emparejado trae un número de documento distinto del suyo.

    Solo cuenta los que tienen número en la etiqueta: si no lo tienen y el modelo escribe uno, es un invento
    (se mide en 07), no un cruce de documentos. Un resultado sin datos (truncado o fallido) tampoco es «datos
    de otro documento»: no trae ninguno.
    """
    return [
        doc_id
        for doc_id, item in paired.items()
        if item.status == "ok"
        and labels[doc_id]["fields"]["document_number"] is not None
        and (item.data or {}).get("document_number") != labels[doc_id]["fields"]["document_number"]
    ]


def numbered(paired: dict[str, Item], labels: dict) -> int:
    """Documentos emparejados con número en la etiqueta: el denominador del cruce."""
    return sum(labels[doc_id]["fields"]["document_number"] is not None for doc_id in paired)


def mismatch_summary(paired: dict[str, Item], labels: dict) -> str:
    """«ninguno (de 11)» o «['DC-01', …] (2 de 11)»: cuántos con los datos de otro, sobre los que tienen número."""
    mixed, total = mismatched(paired, labels), numbered(paired, labels)
    return f"{mixed} ({len(mixed)} de {total})" if mixed else f"ninguno (de {total})"


# --- Reenvío de los fallidos y troceo (4.5) ----------------------------------------------------------------


def chunk_document(text: str, max_lines: int = CHUNK_LINES) -> list[str]:
    """Parte un documento largo en trozos de `max_lines` líneas de artículo, repitiendo la cabecera en cada uno."""
    lines = text.splitlines()
    positions = [i for i, line in enumerate(lines) if ITEM_LINE.match(line)]
    if len(positions) <= max_lines:
        return [text]
    header, items = lines[: positions[0]], [lines[i] for i in positions]
    return ["\n".join(header + items[start : start + max_lines]) + "\n" for start in range(0, len(items), max_lines)]


def chunk_ids(base: str, count: int, size: int) -> list[str]:
    return [f"{base}--s{size}-c{k}" for k in range(1, count + 1)]


def parse_chunk_id(custom_id: str) -> tuple[str, int, int] | None:
    """(documento, líneas por trozo, número de trozo) de un id de trozo, o None si es un documento entero."""
    match = CHUNK_SUFFIX.search(custom_id)
    return (base_id(custom_id), int(match.group(1)), int(match.group(2))) if match else None


def base_id(custom_id: str) -> str:
    """El documento al que pertenece un `custom_id`, sea de un trozo o no."""
    return CHUNK_SUFFIX.sub("", custom_id)


def item_count(text: str) -> int:
    return sum(bool(ITEM_LINE.match(line)) for line in text.splitlines())


def next_chunk_size(current: int) -> int | None:
    """Trozo más fino tras un truncado: la mitad, hasta una línea. None si ya era de una línea (no se puede partir más)."""
    return current // 2 if current > 1 else None


def resend_plan(items: list[Item], docs: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Qué reenviar (`custom_id` → texto) y qué ids no tienen salida (un trozo de una línea que aun así se trunca).

    - Un truncado se parte (o se parte más fino): el documento entero se re-trocea con la mitad de líneas por trozo.
    - Un trozo que falla sin estar truncado (`invalid`, `errored`, `expired`) se reenvía con SU texto, no con el
      documento entero: así no se duplican líneas al unir.
    - Si el mismo documento tiene un trozo truncado y otro que falló de otra forma, el re-troceo cubre los dos y el
      otro no se reenvía aparte. El orden de salida es el de los documentos y sus trozos, no el de llegada: el
      resultado no depende de en qué orden devolvió la API los resultados.
    - Un `invalid_request_error` no mejora reenviándolo igual: no se repite.
    """
    by_doc: dict[str, list[Item]] = {}
    for item in failed_items(items):
        if not (item.status == "errored" and item.error_type == "invalid_request_error"):
            by_doc.setdefault(base_id(item.custom_id), []).append(item)
    pending: dict[str, str] = {}
    stuck: list[str] = []
    for base in docs:
        group = by_doc.get(base)
        if not group:
            continue
        truncated = [item for item in group if item.status == "truncated"]
        if truncated:
            lines = item_count(docs[base])
            candidates = []
            for item in truncated:
                parsed = parse_chunk_id(item.custom_id)
                size = CHUNK_LINES if parsed is None else next_chunk_size(parsed[1])
                if size is None or lines <= 1:
                    stuck.append(item.custom_id)
                else:
                    candidates.append(min(size, lines - 1))  # un documento corto se parte aunque tenga menos de CHUNK_LINES líneas
            if candidates:
                size = min(candidates)
                chunks = chunk_document(docs[base], size)
                pending.update(zip(chunk_ids(base, len(chunks), size), chunks))
            continue
        for item in sorted(group, key=lambda i: (parse_chunk_id(i.custom_id) or (base, 0, 0))[2]):
            parsed = parse_chunk_id(item.custom_id)
            chunks = chunk_document(docs[base], parsed[1]) if parsed else [docs[base]]
            pending[item.custom_id] = chunks[parsed[2] - 1] if parsed and parsed[2] <= len(chunks) else docs[base]
    return pending, sorted(stuck)


def build_resend(items: list[Item], docs: dict[str, str], *, model: str) -> list[dict]:
    """Peticiones de reenvío de los fallidos (ver `resend_plan`)."""
    return build_batch_requests(resend_plan(items, docs)[0], model=model)


def stuck_ids(items: list[Item], docs: dict[str, str]) -> list[str]:
    """Ids que no se pueden reenviar mejor: ya eran de una línea (o el documento no tiene líneas por las que partir)."""
    return resend_plan(items, docs)[1]


def _chunk_groups(items: list[Item]) -> dict[str, list[tuple[int, int, Item]]]:
    groups: dict[str, list[tuple[int, int, Item]]] = {}
    for item in items:
        parsed = parse_chunk_id(item.custom_id)
        if parsed:
            groups.setdefault(parsed[0], []).append((parsed[1], parsed[2], item))
    return groups


def merge_chunks(items: list[Item]) -> dict[str, dict]:
    """Une los resultados de los trozos de cada documento (cabecera del primero, líneas de todos).

    Solo une un documento con todos sus trozos, del mismo tamaño y numerados sin huecos, y todos correctos; el
    resto sigue pendiente. Ordena por número de trozo, así que no depende del orden de llegada.
    """
    merged = {}
    for base, parts in _chunk_groups(items).items():
        parts.sort(key=lambda part: part[1])
        if len({size for size, _, _ in parts}) != 1 or [k for _, k, _ in parts] != list(range(1, len(parts) + 1)):
            continue
        if any(item.status != "ok" for _, _, item in parts):
            continue
        merged[base] = {**parts[0][2].data, "line_items": [line for _, _, item in parts for line in item.data.get("line_items", [])]}
    return merged


def unmerged_documents(items: list[Item]) -> list[str]:
    """Documentos con trozos en estos resultados que no se han podido unir."""
    return sorted(set(_chunk_groups(items)) - set(merge_chunks(items)))


# --- Ventana frente a SLA (4.5) -------------------------------------------------------------------------------


def route_workload(sla_hours: float | None, *, resubmissions: int = 1) -> str:
    """`batch`, `batch_sin_margen` o `sync` según el plazo de entrega.

    Usa el mismo peor caso que `submission_interval`: la espera hasta el siguiente envío, la ventana
    entera y el margen. Si queda intervalo también con los reenvíos, cabe con margen; si solo con
    una pasada, no queda tiempo para recuperar fallos; si ni con una, tiene que ir síncrono.
    """
    if sla_hours is None:
        return "batch"  # sin plazo, nadie espera
    if submission_interval(sla_hours, resubmissions=resubmissions) is not None:
        return "batch"
    if submission_interval(sla_hours) is not None:
        return "batch_sin_margen"
    return "sync"


# (nombre del trabajo, plazo de entrega en horas o None si nadie espera)
WORKLOADS = [
    ("Conciliación semanal de albaranes con pedidos", 72),
    ("Cierre contable mensual de facturas", None),
    ("Auditoría trimestral de compras de equipos", None),
    ("Extracción de las facturas del turno de noche", 30),
    ("Facturas que hay que pagar hoy", 8),
    ("Albarán en recepción (el almacén espera la respuesta)", 0.1),
]


SUBMISSION_MARGIN_HOURS = 2  # holgura para crear el lote, leerlo y entregar el resultado


def submission_interval(sla_hours: float, *, resubmissions: int = 0, margin_hours: float = SUBMISSION_MARGIN_HOURS) -> float | None:
    """Cada cuántas horas hay que enviar un lote para cumplir el plazo, o None si no se puede.

    Un documento que llega justo después de un envío espera un intervalo entero al siguiente y,
    en el peor caso, otra ventana completa de procesado (y una más por cada reenvío de fallidos).
    Así que `intervalo + ventana × (1 + reenvíos) + margen ≤ SLA`. Con 30 h salen 4 h, el ejemplo
    de la guía. Si no queda un intervalo positivo, el trabajo no cabe en batch.
    """
    interval = sla_hours - BATCH_WINDOW_HOURS * (1 + resubmissions) - margin_hours
    return interval if interval > 0 else None


def split_workloads(workloads: list[tuple[str, float | None]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"batch": [], "batch_sin_margen": [], "sync": []}
    for name, sla in workloads:
        groups[route_workload(sla)].append(name)
    return groups


# --- Muestra previa y coste (4.5) -------------------------------------------------------------------------------


def sample_ids(docs: dict[str, str], count: int = SAMPLE_SIZE) -> list[str]:
    """Unos pocos documentos cortos para probar de forma síncrona antes de lanzar el lote."""
    return [doc_id for doc_id, text in docs.items() if len(chunk_document(text)) == 1][:count]


def field_accuracy(extractions: dict[str, dict], labels: dict, schema: dict) -> dict[str, tuple[int, int]]:
    """(correctos, comprobados) por campo, comparando cada extracción con su etiqueta.

    Un campo cuenta como correcto si el valor coincide con la etiqueta; uno que la etiqueta dice que no está
    y el modelo rellena, o uno que sale vacío teniendo valor, cuenta como fallo.
    """
    counts = {name: [0, 0] for name in ACCURACY_FIELDS}
    for doc_id, data in extractions.items():
        score = ext.score_extraction(data, labels[doc_id], schema)
        wrong = {*score.wrong, *score.missing, *score.invented}
        for name in labels[doc_id]["fields"]:
            counts[name][1] += 1
            counts[name][0] += name not in wrong
        counts["doc_type"][1] += 1
        counts["doc_type"][0] += score.type_ok
        counts["line_items"][1] += 1
        counts["line_items"][0] += score.lines_ok
    return {name: (right, total) for name, (right, total) in counts.items()}


def overall_accuracy(accuracy: dict[str, tuple[int, int]]) -> float:
    total = sum(t for _, t in accuracy.values())
    return sum(r for r, _ in accuracy.values()) / total if total else 0.0


def preview_passes(extractions: dict[str, dict], labels: dict, schema: dict, min_accuracy: float = SAMPLE_MIN_ACCURACY) -> bool:
    """La muestra sirve si no está vacía, toda extracción cumple el esquema y el acierto llega al umbral."""
    if not extractions or any(ext.conforms(data, schema) for data in extractions.values()):
        return False
    return overall_accuracy(field_accuracy(extractions, labels, schema)) >= min_accuracy


def remaining_budget(budget: float, spent: float) -> float:
    """Lo que queda del tope de esta invocación."""
    return max(0.0, budget - spent)


def fits_budget(spent: float, estimate: float, budget: float) -> bool:
    """¿Cabe la estimación de un lote en lo que queda del tope, contando lo ya gastado en esta invocación?"""
    return spent + estimate <= budget


def batch_cost(model: str, usages: list[Any]) -> float:
    """Coste real de lo leído del lote, con el descuento."""
    return sum(cost_of(model, usage, batch=True) for usage in usages)


def estimate_batch_cost(requests: list[dict], model: str) -> float:
    """Cota superior antes de enviar: un lote no se corta a mitad (no hay `max_budget_usd` que lo pare).

    Entrada ≈ un token cada 3 caracteres de la petición; salida: todo `max_tokens`; con el descuento.
    """
    total = 0.0
    for request in requests:
        params = request["params"]
        usage = SimpleNamespace(input_tokens=len(json.dumps(params, ensure_ascii=False)) // 3, output_tokens=params["max_tokens"])
        total += cost_of(model, usage, batch=True)
    return total


# --- Ejecución --------------------------------------------------------------------------------------------------------


def print_windows() -> None:
    print("\n=== ventana frente a SLA · la ventana del lote es de 24 h y no hay SLA de latencia ===")
    labels = {"batch": "cabe en batch", "batch_sin_margen": "cabe en batch, sin margen para reenviar fallidos", "sync": "tiene que ir síncrono"}
    for route, names in split_workloads(WORKLOADS).items():
        print(f"[{labels[route]}]")
        for name in names:
            sla = dict(WORKLOADS)[name]
            print(f"  - {name} (plazo: {'sin plazo' if sla is None else f'{sla} h'}){frequency_note(sla)}")
    print(f"\nFrecuencia de envío: intervalo + {BATCH_WINDOW_HOURS} h de ventana (+ {BATCH_WINDOW_HOURS} h por reenvío) + {SUBMISSION_MARGIN_HOURS} h de margen ≤ plazo.")
    print("Sin modelo: es solo aritmética.")
    print("Con --enviar se lanza un lote de verdad (cuesta unos céntimos).")


def frequency_note(sla: float | None) -> str:
    """Cada cuánto enviar, con y sin margen para reenviar los fallidos."""
    if sla is None or sla < BATCH_WINDOW_HOURS:
        return ""
    once, with_resend = submission_interval(sla), submission_interval(sla, resubmissions=1)
    if once is None:
        return " → no queda intervalo de envío"
    resend = f"; con un reenvío, cada {with_resend:g} h" if with_resend else "; un reenvío no cabe"
    return f" → enviar cada {once:g} h{resend}"


def run_preview(client: Any, model: str, guard: CostGuard, docs: dict[str, str]) -> bool:
    """Muestra síncrona con los mismos parámetros que el lote: forma y acierto frente a las etiquetas, antes de gastar en el lote."""
    schema = ext.build_tool("correcta")["input_schema"]
    extractions = {}
    for request in build_batch_requests({i: docs[i] for i in sample_ids(docs)}, model=model):
        response = client.messages.create(**request["params"])
        guard.add(response.usage)
        found = ext.first_tool_use(response)
        extractions[request["custom_id"]] = found[1] if found else {}
        print(f"  muestra {request['custom_id']}: {'forma válida' if found and not ext.conforms(found[1], schema) else 'FORMA INVÁLIDA'}")
    accuracy = field_accuracy(extractions, ext.LABELS, schema)
    print("  acierto por campo: " + " · ".join(f"{name} {right}/{total}" for name, (right, total) in accuracy.items()))
    overall = overall_accuracy(accuracy)
    print(f"[muestra] acierto {overall:.0%} (umbral {SAMPLE_MIN_ACCURACY:.0%}): los campos con menos acierto son los que hay que afinar en el prompt antes del lote")
    return preview_passes(extractions, ext.LABELS, schema)


def run_send(client: Any, model: str, budget: float, args: Any) -> int:
    docs = ext.DOCS
    requests = build_batch_requests(docs, model=model)
    estimate = estimate_batch_cost(requests, model)
    print(f"[estimación] cota superior del lote ${estimate:.4f} (con el 50 %) · tope ${budget} ({BUDGET_SCOPE}: muestra síncrona + estimación del lote)")
    if estimate > budget:
        print("[corte] la estimación supera el tope: el lote no se envía")
        return 1
    guard = CostGuard(model, budget)
    if not args.sin_muestra:
        print(f"[muestra síncrona] {SAMPLE_SIZE} documentos antes del lote")
        if not run_preview(client, model, guard, docs):
            print(f"[corte] la muestra no cumple el esquema o no llega al {SAMPLE_MIN_ACCURACY:.0%} de acierto: no se lanza el lote (--sin-muestra lo salta)")
            return 1
        print(f"[muestra] coste síncrono ${guard.spent:.4f}")
        if not fits_budget(guard.spent, estimate, budget):
            print(f"[corte] la muestra (${guard.spent:.4f}) más la estimación del lote (${estimate:.4f}) superan el tope ${budget}: el lote no se envía")
            return 1
    batch = client.messages.batches.create(requests=requests)
    print(f"[lote] id={batch.id} estado={batch.processing_status} peticiones={len(requests)}")
    print(f"[siguiente] copia el id y léelo más tarde: uv run python app3_sistema_multiagente/09_batches.py --batch-id {batch.id}")
    print("[nota] este módulo no guarda nada: el id lo guardas tú. El lote tarda entre minutos y 24 h.")
    return 0


def wait_for(client: Any, batch_id: str, seconds: int) -> Any:
    deadline = time.time() + seconds
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended" or time.time() >= deadline:
            return batch
        time.sleep(15)


def run_read(client: Any, model: str, budget: float, args: Any) -> int:
    batch = wait_for(client, args.batch_id, args.esperar)
    counts = batch.request_counts
    print(f"[lote] id={batch.id} estado={batch.processing_status} procesando={counts.processing} correctas={counts.succeeded} con error={counts.errored} caducadas={counts.expired} canceladas={counts.canceled}")
    if batch.processing_status != "ended":
        print("[pendiente] el lote no ha terminado; vuelve a ejecutar con el mismo --batch-id (o añade --esperar 120)")
        return 0
    items = [classify_result(entry) for entry in client.messages.batches.results(batch.id)]
    arrival = [item.custom_id for item in items]
    sent = [i for i in ext.DOCS if base_id(i) in {base_id(a) for a in arrival}]
    print(f"[orden de llegada] {arrival}")
    if arrival != sent and set(arrival) == set(sent):
        print("[orden] los resultados NO llegaron en el orden de envío")
    statuses = Counter(item.status for item in items)
    print(f"[resultados] {dict(statuses)}")
    for item in failed_items(items):
        print(f"  fallido {item.custom_id}: {item.status}{f' ({item.error_type})' if item.error_type else ''}")

    if args.anti == "por_orden":
        if set(arrival) != set(ext.DOCS):
            print("[aviso] --anti por_orden necesita el lote completo de documentos; se usa el emparejado por custom_id")
        else:
            paired = pair_results(list(ext.DOCS), items, by="order")
            print(f"[anti por orden] documentos con los datos de otro: {mismatch_summary(paired, ext.LABELS)}")
    paired = {i: item for i, item in pair_results(list(ext.DOCS), items, by="custom_id").items() if i in ext.LABELS}
    print(f"[por custom_id] documentos con los datos de otro: {mismatch_summary(paired, ext.LABELS)}")

    schema = ext.build_tool("correcta")["input_schema"]
    for doc_id, data in merge_chunks(items).items():
        score = ext.score_extraction(data, ext.LABELS[doc_id], schema)
        print(f"[trozos unidos] {doc_id}: {len(data['line_items'])} líneas · líneas correctas {score.lines_ok} · forma válida {score.syntax_ok}")
    for doc_id in unmerged_documents(items):
        print(f"[trozos sin unir] {doc_id}: faltan trozos o alguno falló; se unen cuando todos estén en un mismo lote")

    usages = [item.usage for item in items if item.usage is not None]
    real = batch_cost(model, usages)
    print(f"[coste] lote con el 50 %: ${real:.4f} · el mismo trabajo síncrono: ${real * 2:.4f}")
    # El lote que se lee ya se pagó en otra invocación: no se suma al tope de esta, que solo cubre lo que esta
    # invocación vaya a gastar, es decir, la estimación del reenvío.
    guard = CostGuard(model, budget)

    if args.reenviar:
        for stuck in stuck_ids(items, ext.DOCS):
            print(f"[sin salida] {stuck}: no se puede partir más; revisa el documento o sube BATCH_MAX_TOKENS")
        requests = build_resend(items, ext.DOCS, model=model)
        if not requests:
            print("[reenvío] no hay nada que reenviar")
            return 0
        estimate = estimate_batch_cost(requests, model)
        left = remaining_budget(budget, guard.spent)
        if not fits_budget(guard.spent, estimate, budget):
            print(f"[corte] la estimación del reenvío ${estimate:.4f} supera lo que queda del tope de esta invocación (${left:.4f} de ${budget}; el lote leído ya se pagó antes)")
            return 1
        new = client.messages.batches.create(requests=requests)
        print(f"[reenvío] {len(requests)} peticiones {[r['custom_id'] for r in requests]}")
        print(f"[lote] id={new.id}; léelo con --batch-id {new.id}")
    return 0


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--ventanas", action="store_true", help="reparte unos trabajos entre batch y síncrono (sin modelo)")
    parser.add_argument("--enviar", action="store_true", help="envía el lote y escribe su id")
    parser.add_argument("--sin-muestra", action="store_true", help="con --enviar, salta la muestra síncrona previa")
    parser.add_argument("--batch-id", help="lee el estado y los resultados de un lote ya enviado")
    parser.add_argument("--reenviar", action="store_true", help="con --batch-id, reenvía los fallidos (troceando los largos)")
    parser.add_argument("--esperar", type=int, default=0, help="con --batch-id, segundos que espera a que termine (por defecto 0)")
    args = parser.parse_args()
    if args.anti and not args.batch_id:
        parser.error("--anti por_orden se usa al leer los resultados (--batch-id)")
    if args.reenviar and not args.batch_id:
        parser.error("--reenviar necesita --batch-id")
    if args.ventanas or not (args.enviar or args.batch_id):
        print_windows()
        return 0
    print(credentials.describe())
    credentials.require_api_key()
    model = report_model("agent")
    budget = report_budget(args.budget, "agent")
    import anthropic

    client = anthropic.Anthropic()
    try:
        return run_send(client, model, budget, args) if args.enviar else run_read(client, model, budget, args)
    except BudgetExceeded as exc:
        print(f"[corte] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
