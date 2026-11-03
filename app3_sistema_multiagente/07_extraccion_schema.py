"""Extracción estructurada con JSON Schema: nullable, enum abierto, tool_choice y few-shot.

CONCEPTO [TS 4.2-K4, S4, S5 · TS 4.3-K1…K4, S1…S6]: extraer metadatos de documentos de
compra con una tool cuyo `input_schema` es un JSON Schema; campos opcionales *nullable*,
`enum` con `unclear` y `other` más un campo de detalle, reglas de normalización en la
descripción, `tool_choice` (forzado o `any`) y ejemplos *few-shot* para estructuras
documentales variadas.

[BORRADOR de Sonnet 5.5: los textos de QUÉ DICE LA GUÍA y ANTI-PATRÓN los reescribe
Opus 5.5 (paso A4 del diseño de la entrega 3) contra la Task Statement 4.2 y 4.3.]

QUÉ DICE LA GUÍA:
- La extracción estructurada fiable se hace con una tool de JSON Schema: el esquema
  fija la forma de la salida (4.3).
- Un campo que puede no estar en el documento va como opcional y *nullable*; si es
  obligatorio, el modelo tiene que inventar algo para cumplir (4.3).
- Un `enum` con una categoría abierta (`other` con un campo de detalle, y `unclear`)
  evita forzar un tipo que no encaja (4.3).
- El esquema garantiza la sintaxis (la forma), no la semántica (que los valores sean
  los correctos) (4.3).
- `tool_choice` forzado a una tool concreta cuando el paso es siempre ese; `any` cuando
  el tipo de documento es desconocido y cada tipo tiene su tool (4.3).
- Con estructuras documentales variadas (tabla, prosa, líneas sueltas), ejemplos
  *few-shot* con las distintas formas mejoran la consistencia (4.2).

POR QUÉ IMPORTA (inferencia propia): un pipeline que extrae de cientos de documentos no
puede depender de que cada respuesta «parezca» bien. La forma se garantiza con el
esquema; lo que el esquema no garantiza hay que medirlo contra etiquetas.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía: campos opcionales como obligatorios (`--anti sin_nullable`) y un
  `enum` cerrado (`--anti enum_cerrado`).
- Lo observado aquí (README y `docs/hallazgos.md`): con campos obligatorios, 21 de 21
  campos ausentes se rellenaron (con `'null'` como texto, con `''` o con un valor
  deducido); con *nullable*, 1 o 2 de 21. Un `enum` cerrado casi no forzó el tipo: el
  modelo devolvió `other` aunque no estaba en el `enum`, porque un esquema de tool
  no se impone sin modo estricto. Por eso el módulo valida la forma además de enviarla.
- EN PRODUCCIÓN (no evaluable): el modo estricto y las *structured outputs* garantizan
  el esquema, pero la guía no los nombra y quedan fuera (`tests/perimetro_excluido.yaml`).
  `any` y el forzado devuelven 400 en Sonnet 5.5, así que el módulo usa el rol `agent`.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 07.

INTRODUCE: TS 4.2-K4, TS 4.2-S4, TS 4.2-S5, TS 4.3-K1, TS 4.3-K2, TS 4.3-K3, TS 4.3-K4, TS 4.3-S1, TS 4.3-S2, TS 4.3-S3, TS 4.3-S4, TS 4.3-S5, TS 4.3-S6

Uso: `uv run python app3_sistema_multiagente/07_extraccion_schema.py --parte forzada|tipo_desconocido|few_shot [--anti sin_nullable|enum_cerrado] [--repeat N]`
"""

import copy
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials  # noqa: E402
from harness.budget import BudgetExceeded, CostGuard  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402

PARTS = ["forzada", "tipo_desconocido", "few_shot"]
ANTI_VARIANTS = ["sin_nullable", "enum_cerrado"]  # solo de la parte `forzada`
MODES = ["forzada", "any", "auto"]
TOOL_NAME = "extract_metadata"
# Campos que un documento puede no traer: en el esquema correcto son *nullable* y no obligatorios.
OPTIONAL_FIELDS = ["vendor", "document_number", "issue_date", "po_number", "currency", "stated_total"]
DOC_TYPES = ["invoice", "delivery_note", "other", "unclear"]

SYSTEM = "Extraes metadatos de documentos de compra de equipos de una mesa de ayuda TI. Llama siempre a una tool de extracción."

# --- Schema (4.3) ------------------------------------------------------------------------


def build_tool(variant: str = "correcta", *, normalization: bool = True) -> dict:
    """La tool `extract_metadata` en una de sus tres variantes.

    - `correcta`: opcionales *nullable* y fuera de `required`, `enum` con `other` y `unclear`.
    - `sin_nullable`: todo obligatorio y sin `null`: si el dato no está, hay que inventarlo.
    - `enum_cerrado`: sin `other` ni `unclear`: el tipo raro solo cabe en una categoría que no es.
    `normalization=False` deja las descripciones sin las reglas de formato (fecha ISO, punto decimal).
    """
    if variant not in ("correcta", "sin_nullable", "enum_cerrado"):
        raise ValueError(f"variante desconocida: {variant}")
    nullable = variant != "sin_nullable"

    def optional(kind: str, description: str) -> dict:
        # Con el esquema correcto, `["string", "null"]`; con el anti, solo el tipo.
        return {"type": [kind, "null"] if nullable else kind, "description": description}

    date_rule = " en formato ISO YYYY-MM-DD" if normalization else ""
    number_rule = ", como número con punto decimal y sin separador de miles" if normalization else ""
    enum = DOC_TYPES[:2] if variant == "enum_cerrado" else DOC_TYPES
    open_enum_hint = "" if variant == "enum_cerrado" else " Usa 'other' si es otro tipo (y rellena doc_type_detail) y 'unclear' si no se puede saber."
    props = {
        "doc_type": {"type": "string", "enum": enum, "description": "Tipo de documento." + open_enum_hint},
        "doc_type_detail": optional("string", "Solo con doc_type 'other': qué tipo de documento es, en una o dos palabras."),
        "vendor": optional("string", "Proveedor tal como aparece. null si el documento no lo dice."),
        "document_number": optional("string", "Número del documento tal como aparece. null si no figura."),
        "issue_date": optional("string", f"Fecha del documento{date_rule}. null si no figura."),
        "po_number": optional("string", "Número de pedido (PO-nnnn). null si el documento no lo menciona."),
        "currency": optional("string", "Moneda en código ISO 4217 (EUR, USD). null si no hay importes."),
        "stated_total": optional("number", f"Total que declara el documento{number_rule}. null si no declara total."),
        "line_items": {
            "type": "array",
            "description": "Líneas del documento.",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": optional("number", f"Precio por unidad{number_rule}. null si no figura."),
                },
                "required": ["description", "quantity"] + ([] if nullable else ["unit_price"]),
            },
        },
    }
    required = ["doc_type", "line_items"] if nullable else list(props)
    return {
        "name": TOOL_NAME,
        "description": "Extrae los metadatos de un documento de compra de equipos.",
        "input_schema": {"type": "object", "properties": props, "required": required},
    }


def build_type_tools() -> list[dict]:
    """Una tool por tipo de documento, para `tool_choice` `any` cuando el tipo se desconoce (4.3)."""
    full = build_tool("correcta")["input_schema"]["properties"]
    header = {name: full[name] for name in ("vendor", "document_number", "issue_date", "po_number")}

    def tool(name: str, description: str, extra: dict, required: list[str]) -> dict:
        return {
            "name": name,
            "description": description,
            "input_schema": {"type": "object", "properties": {**copy.deepcopy(header), **extra}, "required": required},
        }

    lines_with_price = copy.deepcopy(full["line_items"])
    lines_no_price = copy.deepcopy(full["line_items"])
    del lines_no_price["items"]["properties"]["unit_price"]
    return [
        tool("extract_invoice", "Extrae una FACTURA: proveedor, número, fecha, pedido, moneda, total declarado y líneas con precio.",
             {"currency": full["currency"], "stated_total": full["stated_total"], "line_items": lines_with_price}, ["line_items"]),
        tool("extract_delivery_note", "Extrae un ALBARÁN de entrega: proveedor, número, fecha, pedido y líneas con cantidad (sin importes).",
             {"line_items": lines_no_price}, ["line_items"]),
        tool("extract_other", "Extrae cualquier OTRO documento (garantía, presupuesto, fragmento ilegible): lo que figure y qué tipo parece ser.",
             {"doc_type_detail": full["doc_type_detail"]}, []),
    ]


def expected_tool(label: dict) -> str:
    """Qué tool por tipo le toca a un documento según su etiqueta."""
    return {"invoice": "extract_invoice", "delivery_note": "extract_delivery_note"}.get(label["doc_type"], "extract_other")


# --- Few-shot (4.2-K4, S4, S5): las tres formas de documento, con documentos que no son del conjunto ---

FEW_SHOT = [
    (
        """FACTURA F-2026-0100
Proveedor: Muebles Oficina Mar S.L.
Fecha: 05/08/2026
Pedido: PO-7000

| Descripción | Uds | Precio unidad |
| Silla ergonómica | 2 | 180,00 € |

Total factura: 360,00 €
""",
        {
            "doc_type": "invoice", "doc_type_detail": None, "vendor": "Muebles Oficina Mar S.L.", "document_number": "F-2026-0100",
            "issue_date": "2026-08-05", "po_number": "PO-7000", "currency": "EUR", "stated_total": 360.0,
            "line_items": [{"description": "Silla ergonómica", "quantity": 2, "unit_price": 180.0}],
        },
    ),
    (
        "Por la presente Muebles Oficina Mar S.L. le factura, con fecha 9 de agosto de 2026 y número de factura F-2026-0107, tres lámparas de escritorio a 25,50 euros cada una. El importe total a pagar es de 76,50 euros.",
        {
            "doc_type": "invoice", "doc_type_detail": None, "vendor": "Muebles Oficina Mar S.L.", "document_number": "F-2026-0107",
            "issue_date": "2026-08-09", "po_number": None, "currency": "EUR", "stated_total": 76.5,
            "line_items": [{"description": "Lámpara de escritorio", "quantity": 3, "unit_price": 25.5}],
        },
    ),
    (
        """ALBARÁN AL-9001
Muebles Oficina Mar S.L.
Fecha de entrega: 2026-08-12
Pedido: PO-7003
4 x Reposapiés
1 x Pizarra blanca
""",
        {
            "doc_type": "delivery_note", "doc_type_detail": None, "vendor": "Muebles Oficina Mar S.L.", "document_number": "AL-9001",
            "issue_date": "2026-08-12", "po_number": "PO-7003", "currency": None, "stated_total": None,
            "line_items": [
                {"description": "Reposapiés", "quantity": 4, "unit_price": None},
                {"description": "Pizarra blanca", "quantity": 1, "unit_price": None},
            ],
        },
    ),
]


def few_shot_text() -> str:
    """Los ejemplos en el *system prompt*: documento y extracción esperada, de las tres formas."""
    blocks = [f"Documento:\n{text}\nExtracción:\n{json.dumps(extraction, ensure_ascii=False)}" for text, extraction in FEW_SHOT]
    return "\n\nEjemplos de extracción (cada formato de documento es distinto; 'null' si el dato no figura):\n\n" + "\n\n".join(blocks)


# --- Petición (4.3: tool_choice) --------------------------------------------------------------


def choice_for(mode: str, forced_name: str = TOOL_NAME) -> dict[str, str]:
    """`tool_choice` del modo: forzado a una tool, `any` (alguna) o `auto` (puede no llamar a ninguna)."""
    if mode == "forzada":
        return {"type": "tool", "name": forced_name}
    if mode == "any":
        return {"type": "any"}
    if mode == "auto":
        return {"type": "auto"}
    raise ValueError(f"modo desconocido: {mode}")


def build_request(
    doc_text: str, *, tools: list[dict], mode: str, model: str, few_shot: bool = False, forced_name: str = TOOL_NAME, max_tokens: int = 4096
) -> dict[str, Any]:
    """Argumentos de `messages.create` para un documento. Sin el identificador del documento: el modelo lo copiaba como número."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM + (few_shot_text() if few_shot else ""),
        "tools": tools,
        "tool_choice": choice_for(mode, forced_name),
        "messages": [{"role": "user", "content": f"Documento:\n\n{doc_text}"}],
    }


def first_tool_use(response: Any) -> tuple[str, dict] | None:
    """(nombre, entrada) de la primera llamada a tool de la respuesta, o None si no hubo."""
    for block in response.content:
        if block.type == "tool_use":
            return block.name, dict(block.input)
    return None


# --- Sintaxis (el esquema) frente a semántica (las etiquetas) -----------------------------------

_JSON_TYPES = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def conforms(value: Any, schema: dict, path: str = "") -> list[str]:
    """Violaciones del JSON Schema (tipo, `enum`, `required`, propiedades y elementos). Vacía si la forma es válida.

    Hace falta porque la API no lo comprueba por ti: sin modo estricto el modelo puede devolver
    un valor fuera del `enum` o un tipo distinto (docs/hallazgos.md).
    """
    problems: list[str] = []
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else (kinds or [])
    if kinds and not any(_JSON_TYPES[k](value) for k in kinds):
        return [f"{path or 'raíz'}: tipo {type(value).__name__} no admitido ({'/'.join(kinds)})"]
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r} no está en el enum {schema['enum']}")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"falta {path + '.' if path else ''}{name}")
        for name, sub in schema.get("properties", {}).items():
            if name in value:
                problems += conforms(value[name], sub, f"{path + '.' if path else ''}{name}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            problems += conforms(item, schema["items"], f"{path}[{index}]")
    return problems


def label_to_extraction(label: dict) -> dict:
    """La extracción perfecta de un documento, construida desde su etiqueta (para probar la puntuación)."""
    return {"doc_type": label["doc_type"], "doc_type_detail": label["doc_type_detail"], **label["fields"], "line_items": copy.deepcopy(label["line_items"])}


@dataclass
class Score:
    """Cómo salió una extracción frente a su etiqueta."""

    invented: list[str] = field(default_factory=list)  # etiqueta null y el modelo puso algo
    missing: list[str] = field(default_factory=list)  # etiqueta con valor y el modelo puso null
    wrong: list[str] = field(default_factory=list)  # valor distinto del de la etiqueta
    absent_total: int = 0  # campos que la etiqueta dice que no están en el documento
    type_ok: bool = False
    in_enum: bool = False  # el tipo devuelto es uno de los del esquema
    detail_ok: bool | None = None  # solo para `other`
    lines_ok: bool = False
    syntax_ok: bool = False
    syntax_errors: list[str] = field(default_factory=list)


def _same(got: Any, want: Any) -> bool:
    if isinstance(want, (int, float)) and not isinstance(want, bool):
        return isinstance(got, (int, float)) and not isinstance(got, bool) and abs(got - want) < 0.01
    if isinstance(want, str):
        return isinstance(got, str) and got.strip().casefold() == want.strip().casefold()
    return got == want


def _line_key(item: dict) -> tuple:
    price = item.get("unit_price")
    return (round(float(item.get("quantity", 0)), 2), None if price is None else round(float(price), 2))


def score_extraction(data: dict, label: dict, schema: dict) -> Score:
    """Compara una extracción con su etiqueta, campo a campo, y con el esquema que se le envió."""
    score = Score()
    for name, want in label["fields"].items():
        got = data.get(name)
        if want is None:
            score.absent_total += 1
            if got is not None:  # `'null'`, `''`, `'N/A'` o un valor deducido: todo cuenta como inventado
                score.invented.append(name)
        elif got is None:
            score.missing.append(name)
        elif not _same(got, want):
            score.wrong.append(name)
    score.type_ok = data.get("doc_type") == label["doc_type"]
    score.in_enum = data.get("doc_type") in schema["properties"]["doc_type"].get("enum", [data.get("doc_type")])
    if label["doc_type"] == "other":
        detail = data.get("doc_type_detail")
        score.detail_ok = bool(detail) and str(label["doc_type_detail"]).casefold() in str(detail).casefold()
    try:
        score.lines_ok = sorted(map(_line_key, data.get("line_items") or []), key=str) == sorted(map(_line_key, label["line_items"]), key=str)
    except (TypeError, ValueError):
        score.lines_ok = False
    score.syntax_errors = conforms(data, schema)
    score.syntax_ok = not score.syntax_errors
    return score


def summarize(scores: list[Score]) -> dict[str, int]:
    return {
        "documentos": len(scores),
        "inventados": sum(len(s.invented) for s in scores),
        "ausentes": sum(s.absent_total for s in scores),
        "valores_incorrectos": sum(len(s.wrong) for s in scores),
        "tipo_ok": sum(s.type_ok for s in scores),
        "fuera_de_enum": sum(not s.in_enum for s in scores),
        "sintaxis_ok": sum(s.syntax_ok for s in scores),
        "lineas_ok": sum(s.lines_ok for s in scores),
    }


# --- Ejecución -----------------------------------------------------------------------------------

DOCS = {d["doc_id"]: d["text"] for d in load("documentos_compra.json")}
LABELS = load("documentos_compra_etiquetas.json")


def run_documents(create: Callable[..., Any], tools: list[dict], mode: str, model: str, *, few_shot: bool = False, forced_name: str = TOOL_NAME) -> dict[str, tuple[str, dict] | None]:
    """Una petición por documento. Devuelve (tool, entrada) o None si el modelo no llamó a ninguna tool."""
    results = {}
    for doc_id, text in DOCS.items():
        request = build_request(text, tools=tools, mode=mode, model=model, few_shot=few_shot, forced_name=forced_name)
        results[doc_id] = first_tool_use(create(**request))
    return results


def print_scores(title: str, results: dict, schema: dict) -> list[Score]:
    scores = []
    for doc_id, found in results.items():
        data = found[1] if found else {}
        score = score_extraction(data, LABELS[doc_id], schema)
        scores.append(score)
        marks = f"forma={'ok' if score.syntax_ok else 'MAL'} tipo={'ok' if score.type_ok else 'MAL'}"
        notes = [f"{label}={getattr(score, attr)}" for label, attr in (("inventados", "invented"), ("faltan", "missing"), ("distintos", "wrong")) if getattr(score, attr)]
        if not score.in_enum:
            notes.append(f"tipo fuera del enum ({data.get('doc_type')!r})")
        print(f"  {doc_id}: {marks} {' '.join(notes)}")
    summary = summarize(scores)
    print(
        f"[{title}] forma válida {summary['sintaxis_ok']}/{summary['documentos']} · tipo correcto {summary['tipo_ok']}/{summary['documentos']} · "
        f"fuera del enum {summary['fuera_de_enum']} · campos ausentes rellenados {summary['inventados']}/{summary['ausentes']} · "
        f"valores incorrectos {summary['valores_incorrectos']} · líneas correctas {summary['lineas_ok']}/{summary['documentos']}"
    )
    return scores


def make_create(client: Any, guard: CostGuard) -> Callable[..., Any]:
    def create(**request: Any) -> Any:
        response = client.messages.create(**request)
        guard.add(response.usage)
        return response

    return create


def run_forzada(args: Any, create: Callable[..., Any], model: str) -> None:
    variant = args.anti or "correcta"
    tool = build_tool(variant)
    print(f"\n=== forzada · esquema {variant} · {len(DOCS)} documentos × {args.repeat} ===")
    print("[esperado] con el esquema correcto, un campo ausente sale como null; con campos obligatorios hay que rellenarlo")
    for run in range(1, args.repeat + 1):
        results = run_documents(create, [tool], "forzada", model)
        print_scores(f"{run}/{args.repeat}", results, tool["input_schema"])
    print("[sintaxis frente a semántica] «forma válida» solo dice que el JSON cumple el esquema; «incorrectos» e «inventados» salen de comparar con las etiquetas")


def run_tipo_desconocido(args: Any, create: Callable[..., Any], model: str) -> None:
    tools = build_type_tools()
    print(f"\n=== tipo desconocido · {len(tools)} tools por tipo · {len(DOCS)} documentos × {args.repeat} ===")
    print("[esperado] con `any` siempre hay una tool y suele ser la de su tipo; forzar una sola tool trata todo como ese tipo")
    for run in range(1, args.repeat + 1):
        for title, mode, forced in (("any", "any", TOOL_NAME), ("auto", "auto", TOOL_NAME), ("forzada a factura", "forzada", "extract_invoice")):
            results = run_documents(create, tools, mode, model, forced_name=forced)
            right = sum(1 for d, found in results.items() if found and found[0] == expected_tool(LABELS[d]))
            no_tool = sum(1 for found in results.values() if found is None)
            wrong = {d: found[0] for d, found in results.items() if found and found[0] != expected_tool(LABELS[d])}
            print(f"[{run}/{args.repeat}] {title}: tool de su tipo {right}/{len(results)} · sin tool {no_tool} · otra tool {wrong or 'ninguna'}")


def run_few_shot(args: Any, create: Callable[..., Any], model: str) -> None:
    # Descripciones sin reglas de formato: así los ejemplos son lo único que dice cómo se escribe una fecha.
    tool = build_tool("correcta", normalization=False)
    print(f"\n=== few-shot · esquema sin reglas de formato · {len(DOCS)} documentos × {args.repeat} ===")
    print("[esperado] los ejemplos de las tres formas deberían dar más consistencia de formato; con un modelo reciente puede no verse")
    for run in range(1, args.repeat + 1):
        for title, shots in (("sin ejemplos", False), ("con ejemplos", True)):
            results = run_documents(create, [tool], "forzada", model, few_shot=shots)
            scores = [score_extraction(found[1] if found else {}, LABELS[d], tool["input_schema"]) for d, found in results.items()]
            summary = summarize(scores)
            date_wrong = sum("issue_date" in s.wrong for s in scores)
            print(
                f"[{run}/{args.repeat}] {title}: fechas incorrectas {date_wrong} · valores incorrectos {summary['valores_incorrectos']} · "
                f"inventados {summary['inventados']}/{summary['ausentes']} · líneas correctas {summary['lineas_ok']}/{summary['documentos']}"
            )


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTS, required=True)
    # Con Haiku 5.5 el *few-shot* no cambió nada (ya escribe bien las fechas sin ejemplos); Haiku 4.5 sí necesita ayuda.
    parser.add_argument("--rol-modelo", choices=["agent", "enforcement"], default="agent", help="rol del modelo; `enforcement` es Haiku 4.5")
    args = parser.parse_args()
    if args.anti and args.parte != "forzada":
        parser.error("--anti sin_nullable y enum_cerrado son de la parte forzada")
    print(credentials.describe())
    # La Messages API solo admite API key. Rol `agent` (Haiku 5.5): Sonnet 5.5 devuelve 400 con `any` y forzado.
    credentials.require_api_key()
    model = report_model(args.rol_modelo)
    budget = report_budget(args.budget, args.rol_modelo)
    import anthropic

    # El tope es de toda la ejecución del script, repartido entre documentos, repeticiones y partes.
    guard = CostGuard(model, budget)
    create = make_create(anthropic.Anthropic(), guard)
    try:
        {"forzada": run_forzada, "tipo_desconocido": run_tipo_desconocido, "few_shot": run_few_shot}[args.parte](args, create, model)
    except BudgetExceeded as exc:
        print(f"[corte] {exc}")
        return 1
    print(f"\n[fin] coste=${guard.spent:.4f} de ${budget}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
