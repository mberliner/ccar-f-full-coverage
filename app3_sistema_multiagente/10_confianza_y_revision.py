"""Confianza y revisión humana: una exactitud alta no dice dónde se equivoca la extracción.

CONCEPTO [TS 5.5-K1, K2, K3, K4 · S1, S2, S3, S4]: medir la exactitud por tipo de documento y por campo,
calibrar la confianza de cada campo con un conjunto etiquetado, fijar los umbrales de revisión por segmento,
muestrear de forma estratificada lo que se acepta sin revisión y repartir una capacidad de revisión limitada.

QUÉ DICE LA GUÍA:
- Una cifra de exactitud agregada, aunque sea alta, puede ocultar que un tipo de documento o un
  campo concreto rinde mal (5.5-K1). Por eso, antes de dejar de revisar las extracciones de
  confianza alta, se comprueba la exactitud segmento a segmento, por tipo de documento y por
  campo, y se exige que sea consistente en todos (5.5-K4, S2).
- La confianza por campo la emite el propio modelo junto a cada valor; sirve para decidir dónde
  mirar solo después de calibrarla contra un conjunto de validación etiquetado, que es de donde
  salen los umbrales de revisión (5.5-K3, S3).
- Lo que se acepta con confianza alta se sigue vigilando con una muestra aleatoria estratificada:
  mide la tasa de error de forma continua y deja ver patrones de error que no se conocían
  (5.5-K2, S1).
- A una persona van las extracciones con confianza baja y las de documentos ambiguos o
  contradictorios, y la cola se prioriza porque la capacidad de revisión es limitada (5.5-S4).

POR QUÉ IMPORTA (inferencia propia): el titular de exactitud decide cuánto se revisa. Si los
errores se concentran en un tipo poco frecuente, automatizar por el titular deja pasar justo
esos, y una muestra aleatoria simple los ve poco porque ese tipo pesa poco en la población.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Reducir la revisión porque la exactitud global es alta, sin mirarla por tipo y por campo
    (`--anti precision_agregada`: un único umbral elegido con la cifra global).
  - Usar la confianza del modelo como umbral sin calibrarla contra datos etiquetados.
  - Vigilar lo automatizado con una muestra que no está estratificada.
- Inferencias propias:
  - Una sola confianza por documento esconde el campo dudoso detrás de los buenos
    (`--anti confianza_global`). La guía habla de confianza por campo; que la media por
    documento sea el error concreto es la lectura de este módulo.
  - Un segmento con pocos ejemplos etiquetados no se puede validar, así que no se automatiza:
    «sin evidencia suficiente» no es lo mismo que «por debajo del objetivo».
  - La confianza mide la extracción, no la coherencia del documento: los que traen
    `conflict_detected` (`app3/08`) o son ambiguos van a revisión aunque su confianza sea alta.
  - Con poca capacidad, ordenar la cola por confianza y ordenarla por conflictos ven errores
    distintos; ninguno de los dos órdenes lo ve todo.
  - La parte `poblacion` simula la confianza; la única confianza declarada de verdad es la de
    `--parte confianza_modelo`, y lo que enseña es que hay que medir si está calibrada.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 10.

INTRODUCE: TS 5.5-K1, TS 5.5-K2, TS 5.5-K3, TS 5.5-K4, TS 5.5-S1, TS 5.5-S2, TS 5.5-S3, TS 5.5-S4

Uso: `uv run python app3_sistema_multiagente/10_confianza_y_revision.py [--parte poblacion|confianza_modelo] [--anti confianza_global|precision_agregada] [--rol-modelo agent|enforcement] [--repeat N]`
"""

import importlib.util
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials  # noqa: E402
from harness.budget import BudgetExceeded, CostGuard  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402


def load_sibling(filename: str) -> Any:
    """Carga otro módulo de esta carpeta (su nombre empieza por un dígito y no admite `import`)."""
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location("_app3_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# `07` define el esquema, la petición y la puntuación sobre los que trabaja la parte con modelo.
ext = load_sibling("07_extraccion_schema.py")

PARTS = ["poblacion", "confianza_modelo"]
ANTI_VARIANTS = ["confianza_global", "precision_agregada"]
FIELDS = ["vendor", "document_number", "issue_date", "po_number", "currency", "stated_total"]
RARE_TYPE = "other"
# Qué se considera confianza alta: lo que el modelo declara con 0,85 o más.
HIGH_CONFIDENCE = 0.85
# Bandas de confianza para la tabla de calibración (la última incluye el 1,0).
BAND_EDGES = (0.0, 0.5, 0.7, 0.85, 0.95, 1.01)
# Objetivo de exactitud para automatizar y mínimo de ejemplos para poder afirmarlo (elecciones propias).
TARGET_ACCURACY = 0.98
MIN_EXAMPLES = 20
# Documentos que el equipo de revisión puede mirar en el periodo (elección propia: un cuarto de la cola).
REVIEW_CAPACITY_SHARE = 0.25


# --- Celdas: un valor extraído, su confianza y si era correcto ------------------------------------------------


@dataclass(frozen=True)
class Cell:
    record_id: str
    split: str
    doc_type: str
    doc_format: str
    field: str
    confidence: float | None  # la que declara el modelo para ese campo
    doc_confidence: float | None  # una sola confianza para todo el documento
    correct: bool
    conflict: bool  # `conflict_detected` de app3/08
    ambiguous: bool
    value_present: bool = True  # False si el modelo dejó el campo en null (su confianza habla entonces de la ausencia)


def build_cells(records: list[dict], labels: dict, split: str | None = None) -> list[Cell]:
    """Una celda por registro y campo. La corrección sale de las etiquetas, que los registros no llevan."""
    cells = []
    for record in records:
        if split and record["split"] != split:
            continue
        truth = labels[record["record_id"]]["correct"]
        for name in FIELDS:
            cells.append(
                Cell(
                    record["record_id"], record["split"], record["doc_type"], record["doc_format"], name,
                    record["confidences"][name], record["doc_confidence"], bool(truth[name]),
                    bool(record["conflict_detected"]), bool(record["ambiguous"]),
                )
            )
    return cells


def error_count(cells: list[Cell]) -> int:
    return sum(not c.correct for c in cells)


def accuracy(cells: list[Cell]) -> float | None:
    return None if not cells else sum(c.correct for c in cells) / len(cells)


def error_rate(cells: list[Cell]) -> float | None:
    value = accuracy(cells)
    return None if value is None else 1 - value


def error_patterns(cells: list[Cell]) -> set[tuple[str, str]]:
    """Patrones de error: qué tipo de documento y qué campo se equivocan (5.5-K2: patrones nuevos)."""
    return {(c.doc_type, c.field) for c in cells if not c.correct}


# --- 5.5-K1: la exactitud agregada esconde un segmento --------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    n: int
    correct: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.n


def segments(cells: list[Cell], key: Callable[[Cell], Any]) -> dict[Any, Segment]:
    tally: dict[Any, list[int]] = defaultdict(lambda: [0, 0])
    for c in cells:
        tally[key(c)][0] += 1
        tally[key(c)][1] += c.correct
    return {k: Segment(n, ok) for k, (n, ok) in tally.items()}


def worst_segments(cells: list[Cell], key: Callable[[Cell], Any], *, min_n: int) -> list[tuple[Any, Segment]]:
    """Segmentos de peor a mejor exactitud, sin los que tienen menos de `min_n` valores (no se pueden juzgar)."""
    found = [(k, s) for k, s in segments(cells, key).items() if s.n >= min_n]
    return sorted(found, key=lambda item: (item[1].accuracy, str(item[0])))


# --- 5.5-K3, S3: calibración de la confianza ---------------------------------------------------------------------


@dataclass(frozen=True)
class Band:
    low: float
    high: float
    n: int
    accuracy: float | None
    mean_confidence: float | None


def confidence_bands(cells: list[Cell], edges: tuple[float, ...] = BAND_EDGES) -> list[Band]:
    """Exactitud real y confianza media por banda de confianza declarada."""
    bands = []
    for low, high in zip(edges, edges[1:]):
        inside = [c for c in cells if c.confidence is not None and low <= c.confidence < high]
        bands.append(
            Band(low, high, len(inside), accuracy(inside), sum(c.confidence for c in inside) / len(inside) if inside else None)
        )
    return bands


def calibration_gap(bands: list[Band]) -> float:
    """Distancia media (ponderada por n) entre lo que el modelo dice y lo que acierta. 0 = calibrado."""
    total = sum(b.n for b in bands)
    if not total:
        return 0.0
    return sum(b.n * abs(b.mean_confidence - b.accuracy) for b in bands if b.n) / total


def pick_threshold(cells: list[Cell], target: float, min_n: int, *, by: str = "confidence") -> float | None:
    """Menor confianza desde la que la exactitud alcanza `target` con al menos `min_n` ejemplos; None si ninguna."""
    values = [(getattr(c, by), c.correct) for c in cells if getattr(c, by) is not None]
    for candidate in sorted({v for v, _ in values}):
        above = [ok for v, ok in values if v >= candidate]
        if len(above) >= min_n and sum(above) / len(above) >= target:
            return candidate
    return None


def thresholds_by(cells: list[Cell], key: Callable[[Cell], Any], target: float, min_n: int) -> dict[Any, float | None]:
    groups: dict[Any, list[Cell]] = defaultdict(list)
    for c in cells:
        groups[key(c)].append(c)
    return {k: pick_threshold(group, target, min_n) for k, group in groups.items()}


# --- 5.5-K4, S2: validar por segmento antes de automatizar ------------------------------------------------------------


def segment_status(cells: list[Cell], key: Callable[[Cell], Any], *, target: float, min_n: int, high: float = HIGH_CONFIDENCE) -> dict[Any, str]:
    """`ready`, `below_target` o `insufficient_data`, mirando solo las extracciones de confianza alta.

    Las de confianza baja ya van a revisión: sus errores no cuentan contra la automatización.
    """
    status = {}
    for k, segment in segments([c for c in cells if c.confidence is not None and c.confidence >= high], key).items():
        if segment.n < min_n:
            status[k] = "insufficient_data"
        else:
            status[k] = "ready" if segment.accuracy >= target else "below_target"
    return status


def automation_plan(
    calibration: list[Cell], *, key: Callable[[Cell], Any], target: float, min_n: int, aggregate: bool
) -> dict[Any, float | None]:
    """Umbral de automatización por segmento.

    Correcta (`aggregate=False`): uno por segmento, y `None` (todo a revisión) si no hay evidencia
    suficiente. `--anti precision_agregada` (`aggregate=True`): se mira solo la exactitud global y
    el mismo umbral vale para todos los segmentos, también para los que no se han validado.
    """
    keys = {key(c) for c in calibration}
    if aggregate:
        shared = pick_threshold(calibration, target, min_n)
        return {k: shared for k in keys}
    return thresholds_by(calibration, key, target, min_n)


# --- Enrutado: automático o a revisión -----------------------------------------------------------------------------


def auto_accept(
    cells: list[Cell], thresholds: Any, *, level: str, force_review: bool = True
) -> tuple[list[Cell], list[Cell]]:
    """Reparte las celdas en (aceptadas sin revisión, a revisión).

    `level="campo"`: la confianza de cada campo contra el umbral de su segmento `(tipo, campo)`; un
    segmento sin umbral va entero a revisión. `level="documento"` (`--anti confianza_global`): una
    sola confianza por documento contra un único umbral. Con `force_review`, los documentos con
    `conflict_detected` o ambiguos van a revisión aunque su confianza sea alta (5.5-S4).
    """
    if level not in ("campo", "documento"):
        raise ValueError(f"nivel desconocido: {level}")
    auto, review = [], []
    for c in cells:
        if level == "campo":
            threshold = thresholds.get((c.doc_type, c.field))
            confidence = c.confidence
        else:
            threshold, confidence = thresholds, c.doc_confidence
        sure = threshold is not None and confidence is not None and confidence >= threshold
        if force_review and (c.conflict or c.ambiguous):
            sure = False
        (auto if sure else review).append(c)
    return auto, review


# --- 5.5-K2, S1: muestreo aleatorio estratificado ---------------------------------------------------------------------


def simple_sample(items: list, n: int, rng: random.Random) -> list:
    return rng.sample(items, min(n, len(items)))


def stratified_sample(items: list, n: int, *, key: Callable[[Any], Any], min_per_stratum: int, rng: random.Random) -> list:
    """Un mínimo por estrato (o el estrato entero si es menor) y el resto en proporción a su tamaño."""
    strata: dict[Any, list] = defaultdict(list)
    for item in items:
        strata[key(item)].append(item)
    names = sorted(strata, key=str)
    n = min(n, len(items))
    floor = {name: min(min_per_stratum, len(strata[name])) for name in names}
    # Reparto proporcional al tamaño (mayor resto), con el mínimo como suelo y el tamaño como techo.
    raw = {name: n * len(strata[name]) / len(items) for name in names}
    quota = {name: min(len(strata[name]), max(floor[name], int(raw[name]))) for name in names}
    # Si sobra o falta, se ajusta por los restos decimales: se quita primero a quien más pasa de su proporción.
    while sum(quota.values()) > n:
        cuttable = [name for name in names if quota[name] > floor[name]]
        if not cuttable:
            break
        quota[max(cuttable, key=lambda x: (quota[x] - raw[x], str(x)))] -= 1
    while sum(quota.values()) < n:
        growable = [name for name in names if quota[name] < len(strata[name])]
        if not growable:
            break
        quota[max(growable, key=lambda x: (raw[x] - quota[x], str(x)))] += 1
    sample = []
    for name in names:
        sample += rng.sample(strata[name], quota[name])
    return sample


def sampling_experiment(
    pool: list[Cell], *, n: int, key: Callable[[Cell], Any], min_per_stratum: int, trials: int, seed: int
) -> dict[str, dict[str, float]]:
    """Repite el muestreo `trials` veces y cuenta cuántas ve el error del tipo raro y cuántos patrones de error."""
    out = {}
    for name in ("simple", "estratificado"):
        rng = random.Random(f"{seed}-{name}")
        sees_rare, patterns = 0, 0
        for _ in range(trials):
            sample = simple_sample(pool, n, rng) if name == "simple" else stratified_sample(pool, n, key=key, min_per_stratum=min_per_stratum, rng=rng)
            found = error_patterns(sample)
            sees_rare += any(kind == RARE_TYPE for kind, _ in found)
            patterns += len(found)
        out[name] = {"ve_error_del_tipo_raro": sees_rare / trials, "patrones": patterns / trials}
    return out


# --- 5.5-S4: cola de revisión con capacidad limitada -----------------------------------------------------------------


@dataclass(frozen=True)
class ReviewItem:
    record_id: str
    flagged: bool  # conflicto o ambiguo: va a revisión aunque la confianza sea alta
    lowest_confidence: float | None
    errors: int  # errores que la revisión de este documento sí vería (los de sus celdas en revisión)


def review_items(cells: list[Cell], thresholds: Any, *, level: str) -> list[ReviewItem]:
    """Un elemento por documento con algo que revisar, en orden de llegada."""
    _, review = auto_accept(cells, thresholds, level=level)
    by_doc: dict[str, list[Cell]] = {}
    for c in review:
        by_doc.setdefault(c.record_id, []).append(c)
    items = []
    for record_id, group in by_doc.items():
        confidences = [c.confidence for c in group if c.confidence is not None]
        items.append(ReviewItem(record_id, any(c.conflict or c.ambiguous for c in group), min(confidences) if confidences else None, error_count(group)))
    return items


def order_queue(items: list[ReviewItem], how: str) -> list[ReviewItem]:
    """`llegada`: tal cual. `confianza`: la más baja primero. `prioridad`: conflictos y ambiguos primero y después la confianza más baja."""
    low = lambda i: 2.0 if i.lowest_confidence is None else i.lowest_confidence  # noqa: E731
    if how == "llegada":
        return list(items)
    if how == "confianza":
        return sorted(items, key=lambda i: (low(i), i.record_id))
    if how == "prioridad":
        return sorted(items, key=lambda i: (not i.flagged, low(i), i.record_id))
    raise ValueError(f"orden desconocido: {how}")


@dataclass(frozen=True)
class CapacityOutcome:
    reviewed: int
    deferred: int
    errors_caught: int  # errores de extracción que la revisión ve
    errors_total: int
    flagged_caught: int  # documentos con conflicto o ambiguos que la revisión llega a mirar
    flagged_total: int


def review_capacity(queue: list[ReviewItem], capacity: int) -> CapacityOutcome:
    """Lo que se revisa con `capacity` documentos: errores de extracción vistos y documentos conflictivos vistos."""
    reviewed = queue[: max(capacity, 0)]
    return CapacityOutcome(
        len(reviewed), len(queue) - len(reviewed), sum(i.errors for i in reviewed), sum(i.errors for i in queue),
        sum(i.flagged for i in reviewed), sum(i.flagged for i in queue),
    )


# --- 5.5-K3, S3: la confianza que da el propio modelo ------------------------------------------------------------------


def confidence_tool(*, normalization: bool = True) -> dict:
    """La tool de `07` con un campo más: la confianza (0 a 1) que el modelo declara en cada campo.

    `normalization=False` quita de las descripciones las reglas de formato (fecha ISO, punto decimal), como en `08`:
    es la forma de que un modelo capaz cometa errores que calibrar.
    """
    tool = ext.build_tool("correcta", normalization=normalization)
    schema = tool["input_schema"]
    schema["properties"]["field_confidence"] = {
        "type": "object",
        "description": "Tu confianza, de 0 a 1, en que el valor de cada campo es el correcto según el documento (también si lo dejas en null).",
        "properties": {name: {"type": "number", "minimum": 0, "maximum": 1} for name in FIELDS},
        "required": list(FIELDS),
    }
    schema["required"] = [*schema["required"], "field_confidence"]
    return tool


def _valid_confidence(value: Any) -> float | None:
    """Solo un número entre 0 y 1 cuenta como confianza; el resto (texto, fuera de rango) es «sin confianza»."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        return None
    return float(value)


def cells_from_extraction(doc_id: str, data: dict, label: dict) -> list[Cell]:
    """Celdas de una extracción del modelo, puntuadas contra la etiqueta (que el modelo no ve)."""
    declared = data.get("field_confidence")
    declared = declared if isinstance(declared, dict) else {}
    confidences = {name: _valid_confidence(declared.get(name)) for name in FIELDS}
    valid = [v for v in confidences.values() if v is not None]
    doc_conf = sum(valid) / len(valid) if valid else None
    cells = []
    for name in FIELDS:
        want, got = label["fields"][name], data.get(name)
        # Ausente en la fuente: acierta quien deja null; con valor en la etiqueta, acierta quien lo iguala.
        correct = got is None if want is None else got is not None and ext._same(got, want)
        cells.append(Cell(doc_id, "modelo", label["doc_type"], "", name, confidences[name], doc_conf, correct, False, False, got is not None))
    return cells


def summarize_model_confidence(cells: list[Cell]) -> dict[str, Any]:
    """Confianza media cuando acierta y cuando falla, y los errores con confianza alta."""
    with_conf = [c for c in cells if c.confidence is not None]
    right = [c.confidence for c in with_conf if c.correct]
    wrong = [c.confidence for c in with_conf if not c.correct]
    return {
        "n": len(with_conf),
        "sin_confianza": len(cells) - len(with_conf),
        "acierta": len(right),
        "falla": len(wrong),
        "media_si_acierta": sum(right) / len(right) if right else None,
        "media_si_falla": sum(wrong) / len(wrong) if wrong else None,
        "errores_con_confianza_alta": sum(v >= HIGH_CONFIDENCE for v in wrong),
    }


def extract_with_confidence(create: Callable[..., Any], docs: dict[str, str], *, model: str, few_shot: bool = False, normalization: bool = True) -> dict[str, dict]:
    """Una petición forzada a `extract_metadata` por documento, con la confianza por campo en el esquema."""
    tool = confidence_tool(normalization=normalization)
    out = {}
    for doc_id, text in docs.items():
        request = ext.build_request(text, tools=[tool], mode="forzada", model=model, few_shot=few_shot)
        found = ext.first_tool_use(create(**request))
        out[doc_id] = found[1] if found else {}
    return out


# --- Ejecución -------------------------------------------------------------------------------------------------------------


def pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def run_poblacion(anti: str | None) -> None:
    records, labels = load("poblacion_extracciones.json"), load("poblacion_extracciones_etiquetas.json")
    calibration = build_cells(records, labels, split="calibracion")
    production = build_cells(records, labels, split="produccion")
    docs = len({c.record_id for c in production})
    print(f"\n=== población · variante {anti or 'correcta'} · {len(records)} documentos ({len(calibration) // len(FIELDS)} de calibración, {docs} de producción) ===")

    print("\n[1 · exactitud agregada frente a segmentos] (TS 5.5-K1)")
    print(f"  exactitud global: {pct(accuracy(production + calibration))} de {len(production + calibration)} valores")
    for label, key, shown in (("tipo de documento", lambda c: c.doc_type, 3), ("formato y campo (facturas)", lambda c: (c.doc_format, c.field), 3)):
        cells = [c for c in production + calibration if label != "formato y campo (facturas)" or c.doc_type == "invoice"]
        for name, segment in worst_segments(cells, key, min_n=30)[:shown]:
            print(f"  peor por {label}: {name} → {pct(segment.accuracy)} ({segment.n} valores, {segment.n - segment.correct} errores)")

    print("\n[2 · calibración con el conjunto etiquetado] (TS 5.5-K3, S3)")
    for band in confidence_bands(calibration):
        if band.n:
            print(f"  confianza {band.low:.2f}–{min(band.high, 1.0):.2f}: {band.n} valores, acierta {pct(band.accuracy)}, el modelo decía {pct(band.mean_confidence)}")
    print(f"  hueco de calibración (|dice − acierta|, ponderado): {calibration_gap(confidence_bands(calibration)):.3f}")

    key = lambda c: (c.doc_type, c.field)  # noqa: E731
    status = segment_status(calibration, key, target=TARGET_ACCURACY, min_n=MIN_EXAMPLES)
    print("\n[3 · validación por tipo y campo antes de automatizar] (TS 5.5-K4, S2)")
    print(f"  segmentos (tipo, campo): {dict(Counter(status.values()))}; objetivo {TARGET_ACCURACY:.0%} con al menos {MIN_EXAMPLES} extracciones de confianza alta")
    for name in sorted(k for k, v in status.items() if v != "ready"):
        print(f"  no se automatiza: {name} → {status[name]}")

    if anti == "confianza_global":
        threshold = pick_threshold(calibration, TARGET_ACCURACY, MIN_EXAMPLES, by="doc_confidence")
        auto, review = auto_accept(production, threshold, level="documento")
        plan, level = threshold, "documento"
        how = f"una confianza por documento, umbral {threshold}"
    else:
        plan = automation_plan(calibration, key=key, target=TARGET_ACCURACY, min_n=MIN_EXAMPLES, aggregate=anti == "precision_agregada")
        level = "campo"
        auto, review = auto_accept(production, plan, level="campo")
        how = "un umbral para todos (solo la exactitud global)" if anti == "precision_agregada" else "un umbral por tipo y campo"
    rare_auto = [c for c in auto if c.doc_type == RARE_TYPE]
    print(f"\n[4 · enrutado de producción] ({how})")
    print(f"  automático: {len(auto)} valores, errores entre ellos {error_count(auto)} ({pct(error_rate(auto))}) · a revisión: {len(review)} valores")
    print(f"  tipo raro ('{RARE_TYPE}') aceptado sin revisión: {len(rare_auto)} valores, {error_count(rare_auto)} errores")

    pool = [c for c in production if c.confidence is not None and c.confidence >= HIGH_CONFIDENCE]
    result = sampling_experiment(pool, n=60, key=key, min_per_stratum=3, trials=500, seed=1)
    print(f"\n[5 · muestra de 60 de las {len(pool)} extracciones de confianza alta, 500 repeticiones] (TS 5.5-K2, S1)")
    for name, row in result.items():
        print(f"  {name}: ve algún error del tipo raro en {pct(row['ve_error_del_tipo_raro'])} de las muestras · patrones de error distintos por muestra {row['patrones']:.1f} (hay {len(error_patterns(pool))})")

    items = review_items(production, plan, level=level)
    capacity = max(1, round(len(items) * REVIEW_CAPACITY_SHARE))
    print(f"\n[6 · cola de revisión con capacidad limitada] (TS 5.5-S4): {len(items)} documentos con algo que revisar, capacidad {capacity}")
    for how_name in ("llegada", "confianza", "prioridad"):
        outcome = review_capacity(order_queue(items, how_name), capacity)
        print(
            f"  orden de {how_name}: {outcome.reviewed} revisados, ven {outcome.errors_caught} de {outcome.errors_total} errores de extracción "
            f"y {outcome.flagged_caught} de {outcome.flagged_total} documentos con conflicto o ambiguos"
        )


def fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def run_confianza_modelo(args: Any, create: Callable[..., Any], model: str) -> None:
    labels = ext.LABELS
    rules = "sin reglas de formato" if args.sin_reglas_de_formato else "con reglas de formato"
    print(f"\n=== confianza del modelo · {len(ext.DOCS)} documentos × {args.repeat} · modelo {model} · descripciones {rules} ===")
    pooled: list[Cell] = []
    for run in range(1, args.repeat + 1):
        data = extract_with_confidence(create, ext.DOCS, model=model, normalization=not args.sin_reglas_de_formato)
        cells = [c for doc_id, extraction in data.items() for c in cells_from_extraction(doc_id, extraction, labels[doc_id])]
        pooled += cells
        # La confianza de un campo en null habla de la ausencia, no del valor: se mide aparte (ver la salida).
        valued = [c for c in cells if c.value_present]
        s = summarize_model_confidence(valued)
        nulls = [c for c in cells if not c.value_present and c.confidence is not None]
        print(
            f"[{run}/{args.repeat}] con valor {s['n']}: aciertos {s['acierta']} (confianza media {fmt(s['media_si_acierta'])}), fallos {s['falla']} ({fmt(s['media_si_falla'])}), "
            f"errores con confianza ≥ {HIGH_CONFIDENCE}: {s['errores_con_confianza_alta']} · en null {len(nulls)} campos, confianza media {fmt(sum(c.confidence for c in nulls) / len(nulls) if nulls else None)}, "
            f"de los que {sum(not c.correct for c in nulls)} debían tener valor"
        )
        for c in cells:
            if not c.correct:
                print(f"    {c.record_id} {c.field}: erróneo ({'valor' if c.value_present else 'null'}), el modelo dijo {c.confidence}")
    edges = (0.0, 0.7, 0.9, 0.97, 1.01)
    valued = [c for c in pooled if c.value_present]
    for band in confidence_bands(valued, edges=edges):
        if band.n:
            print(f"  banda {band.low:.2f}–{min(band.high, 1.0):.2f}: {band.n} valores, acierta {pct(band.accuracy)}, decía {pct(band.mean_confidence)}")
    print(f"  hueco de calibración (solo valores extraídos): {calibration_gap(confidence_bands(valued, edges=edges)):.3f}")


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTS, default="poblacion", help="`poblacion` no usa modelo; `confianza_modelo` extrae con confianza por campo")
    parser.add_argument("--rol-modelo", choices=["agent", "enforcement"], default="agent", help="rol del modelo de `confianza_modelo`; `enforcement` es Haiku 4.5")
    parser.add_argument("--sin-reglas-de-formato", action="store_true", help="quita de las descripciones las reglas de formato, para provocar errores que calibrar")
    args = parser.parse_args()
    if args.parte == "poblacion":
        run_poblacion(args.anti)
        return 0
    if args.anti:
        parser.error("--anti es de la parte poblacion")
    print(credentials.describe())
    credentials.require_api_key()
    model = report_model(args.rol_modelo)
    budget = report_budget(args.budget, args.rol_modelo)
    import anthropic

    guard = CostGuard(model, budget)
    create = ext.make_create(anthropic.Anthropic(), guard)
    try:
        run_confianza_modelo(args, create, model)
    except BudgetExceeded as exc:
        print(f"[corte] {exc}")
        return 1
    print(f"\n[fin] coste=${guard.spent:.4f} de ${budget}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
