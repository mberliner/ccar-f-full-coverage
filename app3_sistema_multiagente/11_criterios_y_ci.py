"""Criterios categóricos y revisión en CI con `claude -p`: salida estructurada, contexto de proyecto y falsos positivos.

CONCEPTO [TS 3.6-K1, K2, K3 · S1, S2, S3, S4, S5 · TS 4.1-K1, K2, K3 · S1, S2, S3 · TS 4.2-S2, S3 · TS 4.4-K3, S3]:
revisar un cambio con `claude -p --output-format json --json-schema` desde un directorio cuyo `CLAUDE.md` es el contexto
de CI, con criterios categóricos y severidades con ejemplos de código, *few-shot* de formato y de patrón aceptable,
`detected_pattern` en cada hallazgo y un registro de los descartados; revisar de nuevo tras otro commit y pedir los tests
que faltan.

QUÉ DICE LA GUÍA:
- En un pipeline, Claude Code se lanza en modo no interactivo con `-p` (o `--print`), para que no se quede esperando una
  entrada que nadie va a dar (3.6-K1, S1).
- `--output-format json` junto con `--json-schema` imponen una salida estructurada; en CI eso da hallazgos que una
  máquina puede leer y publicar como comentarios en línea del PR (3.6-K2, S2).
- El contexto del proyecto le llega a Claude Code en CI por `CLAUDE.md`: estándares de tests, convenciones de *fixtures*,
  criterios de revisión (3.6-K3). Documentar ahí los estándares, qué hace valioso un test y qué *fixtures* hay mejora los
  tests generados y reduce los que aportan poco (3.6-S5).
- Al generar tests, los tests existentes van en el contexto, para no proponer escenarios que la suite ya cubre (3.6-S4).
- Al revisar otra vez tras commits nuevos, los hallazgos anteriores van en el contexto con la orden de informar solo de lo
  nuevo o de lo que sigue sin resolver, para no repetir comentarios (3.6-S3).
- Un criterio explícito precisa más que una instrucción vaga: marcar un comentario solo cuando lo que dice que hace el
  código no es lo que hace, en vez de pedir que se compruebe que los comentarios son correctos (4.1-K1). Las instrucciones
  generales del tipo «sé conservador» o «informa solo de lo que tengas muy claro» no mejoran la precisión como lo hacen
  los criterios categóricos (4.1-K2).
- Los falsos positivos cuestan confianza: una categoría que se equivoca a menudo hace que se desconfíe también de las que
  aciertan (4.1-K3). Por eso los criterios dicen qué se informa (bugs, seguridad) y qué se deja (estilo menor, patrones
  locales) en vez de filtrar por confianza (4.1-S1); una categoría con muchos falsos positivos se apaga por un tiempo,
  mientras se mejora su prompt (4.1-S2); y cada severidad se define con ejemplos de código concretos (4.1-S3).
- Los *few-shot* fijan el formato de cada hallazgo (ubicación, problema, severidad, arreglo propuesto) (4.2-S2) y enseñan a
  distinguir un patrón aceptable de un problema real, lo que reduce falsos positivos sin impedir generalizar (4.2-S3).
- Un campo `detected_pattern` en cada hallazgo registra qué construcción del código lo provocó, y permite analizar de forma
  sistemática los patrones que los desarrolladores descartan (4.4-K3, S3).

POR QUÉ IMPORTA (inferencia propia): un revisor automático vive de la confianza de quien lee sus comentarios. Un patrón que
falla a menudo hace que se ignoren también los hallazgos buenos, y lo que se puede corregir es el criterio y lo que se
aprende de los descartes, no la prudencia que se le pide al modelo.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Sustituir los criterios por «sé conservador» o «solo alta confianza» (`--anti conservador`, 4.1-K2).
  - Dar instrucciones detalladas sin ejemplos cuando el formato o los casos ambiguos salen inconsistentes
    (`--anti sin_ejemplos`, 4.2-S2, S3).
  - Dejar activa una categoría con muchos falsos positivos (`--sin-categoria comment` es la medida de 4.1-S2).
  - Revisar de nuevo sin los hallazgos previos (`--anti sin_previos`, 3.6-S3); generar tests sin los existentes
    (`--anti sin_tests_existentes`, 3.6-S4) o sin los estándares en `CLAUDE.md` (`--anti sin_estandares`, 3.6-S5).
  - Lanzar Claude Code en CI sin `-p`, o leer los hallazgos del texto libre en vez de una salida con schema.
- Lo medido aquí no respalda todas las viñetas (cifras, con «antes» y «después», en el README y en `docs/hallazgos.md`):
  - `conservador`, `sin_ejemplos` y `--sin-categoria comment` no dieron una señal estable. Con tres ejecuciones,
    `conservador` parecía perder un fallo; con cinco más, no. La medida no separa las variantes, así que ni respalda ni
    contradice 4.1-K2: esa lección es conceptual.
  - Con los tests existentes en el contexto salió 1 escenario repetido por ejecución y sin ellos 0, al revés de lo
    esperado. En el examen manda 3.6-S4.
- Inferencias propias:
  - Desactivar una categoría no quita el falso positivo si el modelo puede reclasificarlo en otra; 4.1-S2 es una medida
    temporal mientras se arregla el criterio, no el arreglo.
  - La confianza declarada y el `detected_pattern` los rellena el propio modelo: sirven para agrupar los descartes, y
    agrupar sin normalizar el nombre los dispersa.
  - Los hallazgos previos de la segunda revisión son una lista fija construida desde las etiquetas, para que las dos
    ramas partan de lo mismo.
- Producto observado (no evaluable): `--setting-sources project` no basta para que a `claude -p` le llegue solo el
  `CLAUDE.md` del directorio de CI; hace falta además `claudeMdExcludes` (sonda C1 en `docs/hallazgos.md`,
  `harness/headless.py`). Con un schema imposible, la CLI responde `success` sin objeto, así que el módulo valida otra vez.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 11.

INTRODUCE: TS 3.6-K1, TS 3.6-K2, TS 3.6-K3, TS 3.6-S1, TS 3.6-S2, TS 3.6-S3, TS 3.6-S4, TS 3.6-S5, TS 4.1-K1, TS 4.1-K2, TS 4.1-K3, TS 4.1-S1, TS 4.1-S2, TS 4.1-S3, TS 4.2-S2, TS 4.2-S3, TS 4.4-K3, TS 4.4-S3

Uso: `uv run python app3_sistema_multiagente/11_criterios_y_ci.py [--parte orden|revision|rerevision|tests] [--anti conservador|sin_ejemplos|sin_previos|sin_tests_existentes|sin_estandares] [--sin-categoria comment] [--repeat N]`
"""

import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials, headless  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import copy_to_temp, load  # noqa: E402

PARTS = ["orden", "revision", "rerevision", "tests"]
ANTI_BY_PART = {
    "revision": ["conservador", "sin_ejemplos"],
    "rerevision": ["sin_previos"],
    "tests": ["sin_tests_existentes", "sin_estandares"],
}
ANTI_VARIANTS = [v for variants in ANTI_BY_PART.values() for v in variants]
CATEGORIES = ["bug", "comment", "security"]
SEVERITIES = ["critical", "major", "minor"]
# Ventana (en líneas) con la que un hallazgo cuenta como el de un fallo sembrado.
LINE_WINDOW = 2
# Funciones que el cambio añade o modifica: un test sobre ellas toca lo que cambió.
CHANGED_FUNCTIONS = {"debe_escalar_lote", "texto_vencido", "enviar_aviso", "promedio_restante"}

# --- Contexto de CI: el CLAUDE.md del directorio de trabajo (3.6-K3, S5) -------------------------------------------------------------

CLAUDE_MD_PROJECT = """# Contexto del proyecto (CI)

Mesa de ayuda TI: paquete `repo_mesa`. Los tests viven junto al código (`tests/` y `*/tests/`) y se ejecutan con pytest.

## Convenciones

- Nombres de funciones y comentarios en español.
- `calcular_sla` lanza `ValueError` cuando el plazo venció; usar esa excepción como señal (`try/except ValueError`) es el patrón local del proyecto.
- Los clientes leen su configuración de `config.py`.
"""

CLAUDE_MD_TEST_STANDARDS = """
## Estándares de tests

- Un test por escenario; nombre `test_<función>_<caso>`.
- Si varias entradas prueban lo mismo, `pytest.mark.parametrize` en lugar de copiar el test.
- Un test valioso cubre un límite (en plazo, justo en el límite, vencido) o una rama de error, y no repite un escenario ya cubierto.
- Fixtures disponibles: `ticket` (un diccionario con `ticket_id`, `prioridad` y `horas`).
"""


def ci_claude_md(*, standards: bool) -> str:
    """El `CLAUDE.md` del cwd de CI. Sin los estándares de tests solo cambia esa sección."""
    return CLAUDE_MD_PROJECT + (CLAUDE_MD_TEST_STANDARDS if standards else "")


# --- Criterios, severidades y ejemplos (4.1, 4.2) -----------------------------------------------------------------------------------

CATEGORY_LINES = {
    "bug": "- bug: el código nuevo hace algo distinto de lo que esperan su nombre, su docstring o quien lo llama (por ejemplo, argumentos en el orden equivocado, o una clave o una unidad que cambia sin que cambien sus llamadores).",
    "comment": "- comment: un comentario o docstring cuya afirmación contradice el código que describe (por ejemplo, el comentario dice un valor y el código usa otro).",
    "security": "- security: entrada externa que llega sin validar a una shell, una consulta o una ruta.",
}


def criteria_line(category: str) -> str:
    return CATEGORY_LINES[category]


CRITERIA = (
    "Criterios de la revisión (informa SOLO de lo que cumpla alguno):\n"
    + criteria_line("bug") + "\n"
    + criteria_line("comment") + "\n"
    + criteria_line("security") + "\n"
    + """No informes de estilo menor (nombres, longitud de línea, docstrings ausentes) ni de patrones locales del proyecto (están en CLAUDE.md), aunque te parezcan mejorables.

Severidades, con un ejemplo de código de cada una:
- critical: permite ejecutar o filtrar algo ajeno. Ejemplo:
```python
subprocess.run(f"convert {nombre_subido}", shell=True)
```
- major: el código falla o da un resultado incorrecto con entradas normales. Ejemplo:
```python
def total(precio, unidades):
    return precio + unidades
```
- minor: el comportamiento es correcto, pero un comentario engaña. Ejemplo:
```python
LIMITE = 10  # máximo 5 elementos
```
"""
)

CONSERVATIVE = "Sé conservador: informa solo de los problemas de los que estés muy seguro y evita los falsos positivos.\n"

FEW_SHOT_FINDINGS = [
    {
        "file": "pagos/cobro.py", "line": 14, "category": "bug", "severity": "major",
        "problem": "`aplicar_descuento(importe, porcentaje)` se llama con los argumentos intercambiados y descuenta el importe en lugar del porcentaje.",
        "suggested_fix": "Llamar a `aplicar_descuento(importe, porcentaje)` con el orden de la firma.",
        "detected_pattern": "arguments_swapped",
    },
    {
        "file": "informes/exporta.py", "line": 31, "category": "security", "severity": "critical",
        "problem": "El nombre del archivo que llega en la petición se concatena en una orden de shell sin validar.",
        "suggested_fix": "Pasar los argumentos como lista a `subprocess.run` sin `shell=True` y validar el nombre.",
        "detected_pattern": "shell_injection",
    },
]

FEW_SHOT = (
    "Formato de cada hallazgo (ubicación, problema, severidad y arreglo propuesto), con dos ejemplos de lo que SÍ se informa:\n"
    + "\n".join(json.dumps(example, ensure_ascii=False) for example in FEW_SHOT_FINDINGS)
    + """

Un patrón aceptable que NO informes (convención del proyecto: una función devuelve None cuando no hay dato y quien llama lo comprueba):
```python
def buscar_usuario(identificador):
    for usuario in USUARIOS:
        if usuario["id"] == identificador:
            return usuario
    return None
```
Para un fragmento así la respuesta correcta no incluye ningún hallazgo.
"""
)

REVIEW_TASK = (
    "Eres un revisor de código en CI. Revisa el cambio de este commit y responde solo con el objeto JSON del schema. "
    "Puedes leer el repositorio con Read, Grep y Glob para comprobar a quién afecta un cambio.\n"
)
REREVIEW_TASK = (
    "Eres un revisor de código en CI. La rama ha recibido commits nuevos: revisa el cambio completo de la rama (diff contra la base) "
    "y responde solo con el objeto JSON del schema. Puedes leer el repositorio con Read, Grep y Glob para comprobar a quién afecta un cambio.\n"
)
TESTS_TASK = (
    "Eres un revisor de código en CI. Propón los tests que faltan para el cambio de este commit y responde solo con el objeto JSON del schema: "
    "para cada test, la función, los argumentos (nombre y valor) y el resultado esperado.\n"
)


def review_schema(disabled: tuple[str, ...] = ()) -> dict[str, Any]:
    """Schema de la salida: una lista de hallazgos con ubicación, problema, severidad, arreglo y `detected_pattern`."""
    unknown = set(disabled) - set(CATEGORIES)
    if unknown:
        raise ValueError(f"categoría desconocida: {sorted(unknown)}")
    categories = [c for c in CATEGORIES if c not in disabled]
    item = {
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "line": {"type": "integer"},
            "category": {"type": "string", "enum": categories},
            "severity": {"type": "string", "enum": SEVERITIES},
            "problem": {"type": "string"},
            "suggested_fix": {"type": "string"},
            "detected_pattern": {"type": "string", "description": "Nombre corto en snake_case del patrón de código que provoca el hallazgo."},
        },
        "required": ["file", "line", "category", "severity", "problem", "suggested_fix", "detected_pattern"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"findings": {"type": "array", "items": item}},
        "required": ["findings"],
        "additionalProperties": False,
    }


def tests_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "tests": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "function": {"type": "string"},
                        "args": {"type": "object", "description": "Argumentos de la llamada: nombre del parámetro y valor."},
                        "expected": {"type": "string"},
                    },
                    "required": ["function", "args", "expected"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tests"],
        "additionalProperties": False,
    }


def build_review_prompt(diff: str, *, message: str, anti: str | None = None, disabled: tuple[str, ...] = (), task: str = REVIEW_TASK) -> str:
    """Prompt de la revisión. Cada variante cambia una sola cosa de la correcta.

    `conservador`: los criterios y las severidades se sustituyen por «sé conservador». `sin_ejemplos`: sin el bloque *few-shot*.
    `disabled`: una categoría fuera (su línea de los criterios y su valor del schema).
    """
    if anti not in (None, "conservador", "sin_ejemplos"):
        raise ValueError(f"variante desconocida: {anti}")
    review_schema(disabled)  # valida las categorías
    criteria = CRITERIA
    for category in disabled:
        criteria = criteria.replace(criteria_line(category) + "\n", "")
    if anti == "conservador":
        criteria = CONSERVATIVE
    few_shot = "" if anti == "sin_ejemplos" else FEW_SHOT
    return f"{task}\n{criteria}\n{few_shot}\nMensaje del commit: {message}\n\nDiff:\n{diff}"


# --- Repositorio temporal con el cambio (3.6) ---------------------------------------------------------------------------------------


@dataclass
class ReviewRepo:
    path: Path
    base: str
    commit_1: str
    commit_2: str


def _git(path: Path, *args: str) -> str:
    # Identidad y opciones por orden: el repositorio temporal no depende de la configuración de git de la persona.
    cmd = ["git", "-c", "user.name=ci", "-c", "user.email=ci@mesa-ejemplo.test", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args]
    done = subprocess.run(cmd, cwd=path, capture_output=True, text=True, encoding="utf-8", check=True)
    return done.stdout


def _write(path: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))  # sin traducir saltos de línea: el diff solo tiene el cambio


def build_review_repo(*, standards: bool = True) -> ReviewRepo:
    """Copia temporal de `repo_mesa` con su `CLAUDE.md` de CI y dos commits de cambio. `datos/sinteticos/` no se toca."""
    change = load("cambio_revision.json")
    path = copy_to_temp("repo_mesa")
    _write(path, {"CLAUDE.md": ci_claude_md(standards=standards)})
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "base")
    base = _git(path, "rev-parse", "HEAD").strip()
    _write(path, change["commit_1"])
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", change["message_1"])
    commit_1 = _git(path, "rev-parse", "HEAD").strip()
    _write(path, change["commit_2"])
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", change["message_2"])
    commit_2 = _git(path, "rev-parse", "HEAD").strip()
    return ReviewRepo(path, base, commit_1, commit_2)


def diff_of(repo: ReviewRepo, start: str, end: str, context: int = 3) -> str:
    return _git(repo.path, "diff", "--no-color", f"-U{context}", start, end)


def review_command(
    cwd: Path, *, model: str, budget: float, schema: dict[str, Any], tools: tuple[str, ...] = headless.READ_ONLY_TOOLS, resume: str | None = None, persist: bool = False
) -> list[str]:
    """La orden de `claude -p` de este módulo: aislada, con tope, con schema y de solo lectura (o sin tools)."""
    return headless.build_command(cwd=cwd, model=model, max_budget_usd=budget, schema=schema, tools=tools, resume=resume, persist=persist)


# --- Puntuación contra lo sembrado (4.1: señal) ------------------------------------------------------------------------------------


def normalize_pattern(value: Any) -> str:
    """`detected_pattern` en una forma comparable: minúsculas, `_` entre palabras; vacío es `sin_patron`."""
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or "sin_patron"


def _matches(f: dict, item: dict) -> bool:
    """Un hallazgo cuenta como el de un elemento etiquetado si cae en su archivo y en su ventana de líneas, o nombra su símbolo.

    Un fallo entre archivos también se encuentra en un llamador, en cualquier línea, si el hallazgo habla de la clave o la unidad
    que cambió: sin eso, cualquier comentario sobre un archivo que casualmente lo llama contaría como acierto.
    """
    file, line = f.get("file"), f.get("line")
    if not isinstance(file, str) or isinstance(line, bool) or not isinstance(line, int):
        return False
    if file == item["file"]:
        # El modelo cita las líneas de forma aproximada: en el mismo archivo basta la línea cercana o nombrar el símbolo del fallo.
        text = f"{f.get('problem', '')} {f.get('suggested_fix', '')}"
        return abs(line - item["line"]) <= LINE_WINDOW or any(symbol in text for symbol in item.get("symbols", []))
    if file in item.get("callers", []):
        text = f"{f.get('problem', '')} {f.get('suggested_fix', '')}".casefold()
        return any(word in text for word in item.get("keywords", []))
    return False


def _find_flaw(f: dict, flaws: list[dict]) -> dict | None:
    """Primero por ubicación exacta; el fallo entre archivos, por sus llamadores, solo si nada más lo reclama."""
    return next((x for x in flaws if x["file"] == f.get("file") and _matches(f, x)), None) or next((x for x in flaws if _matches(f, x)), None)


@dataclass
class Score:
    found: set[str] = field(default_factory=set)
    missed: set[str] = field(default_factory=set)
    false_positives: list[dict] = field(default_factory=list)
    flagged_ok: list[dict] = field(default_factory=list)  # marcó el cambio correcto o el patrón aceptable
    discarded: list[dict] = field(default_factory=list)  # falsos positivos y marcas de lo correcto, en orden de llegada
    duplicates: int = 0
    true_findings: int = 0
    total: int = 0
    by_category: dict[str, list[int]] = field(default_factory=dict)  # categoría → [hallazgos que acertaron, hallazgos]


def relevant_flaws(labels: dict, scope: int) -> list[dict]:
    """Fallos que existen en el estado que se revisa: `scope` 1, tras el primer commit; 2, tras el segundo."""
    return [f for f in labels["seeded"] if (f["commit"] == 1 and f.get("resolved_in") != 2) or (scope == 1 and f["commit"] == 1) or (scope == 2 and f["commit"] == 2)]


def score_findings(findings: list[dict], labels: dict, *, scope: int) -> Score:
    flaws = relevant_flaws(labels, scope)
    decoys = [*labels["correct_changes"], *labels["acceptable_patterns"]]
    result = Score(missed={f["id"] for f in flaws})
    for f in findings:
        result.total += 1
        category = str(f.get("category"))
        tally = result.by_category.setdefault(category, [0, 0])
        tally[1] += 1
        claimed = any(_matches(f, d) for d in decoys)
        flaw = _find_flaw(f, flaws)
        if flaw and not (claimed and flaw["file"] != f.get("file")):
            tally[0] += 1
            result.true_findings += 1
            if flaw["id"] in result.found:
                result.duplicates += 1
            result.found.add(flaw["id"])
            result.missed.discard(flaw["id"])
        elif claimed:
            result.flagged_ok.append(f)
            result.discarded.append(f)
        else:
            result.false_positives.append(f)
            result.discarded.append(f)
    return result


def precision(result: Score) -> float | None:
    return result.true_findings / result.total if result.total else None


def recall(result: Score) -> float:
    total = len(result.found) + len(result.missed)
    return len(result.found) / total if total else 0.0


def precision_by_category(result: Score) -> dict[str, float]:
    return {category: ok / n for category, (ok, n) in result.by_category.items()}


def discard_log(result: Score) -> dict[str, int]:
    """Los hallazgos descartados (no coinciden con lo sembrado) agrupados por `detected_pattern`, de más a menos frecuentes (4.4-S3)."""
    counts: Counter[str] = Counter()
    order: dict[str, int] = {}
    for f in result.discarded:
        pattern = normalize_pattern(f.get("detected_pattern"))
        counts[pattern] += 1
        order.setdefault(pattern, len(order))
    return dict(sorted(counts.items(), key=lambda item: (-item[1], order[item[0]])))


# --- 3.6-S3: segunda revisión con los hallazgos previos -------------------------------------------------------------------------------

SEVERITY_BY_CATEGORY = {"security": "critical", "bug": "major", "cross_file": "major", "comment": "minor"}


def prior_findings(labels: dict) -> list[dict]:
    """La primera revisión tal como se publicó: lo sembrado en el primer commit, con un id cada uno."""
    prior = []
    for index, flaw in enumerate((f for f in labels["seeded"] if f["commit"] == 1), start=1):
        prior.append({
            "id": f"P{index}", "file": flaw["file"], "line": flaw["line"],
            "category": "bug" if flaw["category"] == "cross_file" else flaw["category"],
            "severity": SEVERITY_BY_CATEGORY[flaw["category"]], "problem": flaw["summary"], "suggested_fix": "", "detected_pattern": "",
        })
    return prior


def prior_block(prior: list[dict]) -> str:
    lines = [f"- {p['id']} ({p['file']}:{p['line']}, {p['category']}): {p['problem']}" for p in prior]
    return (
        "Hallazgos de la revisión anterior, ya publicados como comentarios del PR:\n" + "\n".join(lines) + "\n"
        "Informa solo de lo nuevo o de lo que siga sin resolverse y no figure ya en esta lista; no dupliques los hallazgos previos.\n"
    )


def build_rereview_prompt(diff: str, *, message: str, prior: list[dict] | None) -> str:
    """Segunda revisión. Con `prior`, solo añade la lista de hallazgos previos y la orden de no duplicarlos."""
    prompt = build_review_prompt(diff, message=message, task=REREVIEW_TASK)
    if prior:
        prompt = prompt.replace(REREVIEW_TASK, REREVIEW_TASK + prior_block(prior), 1)
    return prompt


def classify_rereview(findings: list[dict], labels: dict, prior: list[dict]) -> dict[str, Any]:
    """Qué es cada hallazgo de la segunda revisión: nuevo, repetido (ya publicado), de un fallo ya resuelto u otro."""
    scored = score_findings(findings, labels, scope=2)
    new_ids = {f["id"] for f in labels["seeded"] if f["commit"] == 2}
    resolved = [f for f in labels["seeded"] if f.get("resolved_in") == 2]
    resolved_repeated = sum(1 for f in findings if any(_matches(f, r) for r in resolved))
    other = sum(1 for f in scored.false_positives if not any(_matches(f, r) for r in resolved))
    return {
        "nuevos": scored.found & new_ids,
        "repetidos": scored.found - new_ids,
        "resueltos_repetidos": resolved_repeated,
        "otros": other,
        "total": scored.total,
    }


# --- 3.6-S4, S5: generación de tests -------------------------------------------------------------------------------------------------------


def _norm_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return str(value).strip().casefold()


def scenario_key(function: Any, args: Any) -> tuple:
    """Un escenario de test: la función y sus argumentos, sin distinguir mayúsculas, orden ni 3 de 3.0."""
    items = tuple(sorted((str(k).casefold(), _norm_value(v)) for k, v in args.items())) if isinstance(args, dict) else ()
    return (str(function).casefold(), items)


@dataclass
class TestsScore:
    total: int = 0
    duplicates: int = 0
    new: int = 0
    on_changed_code: int = 0
    duplicated: list = field(default_factory=list)  # (función, argumentos) de cada escenario repetido


def score_tests(tests: list, labels: dict) -> TestsScore:
    """Escenarios propuestos que ya cubren los tests del repositorio y los nuevos que tocan lo que cambió."""
    existing = {scenario_key(s["function"], s["args"]) for s in labels["existing_scenarios"]}
    result = TestsScore(total=len(tests))
    for t in tests:
        if not isinstance(t, dict) or not isinstance(t.get("function"), str) or not isinstance(t.get("args"), dict):
            continue
        if scenario_key(t["function"], t["args"]) in existing:
            result.duplicates += 1
            result.duplicated.append((t["function"], t["args"]))
            continue
        result.new += 1
        function = t["function"].casefold()
        touches_sla = function == "calcular_sla" and ("critica" in str(t["args"]).casefold() or "minut" in str(t.get("expected", "")).casefold())
        if function in CHANGED_FUNCTIONS or touches_sla:
            result.on_changed_code += 1
    return result


def existing_tests_text(path: Path) -> str:
    """El código de todos los tests del repositorio, con su ruta, para ponerlo en contexto."""
    parts = []
    for test_file in sorted(Path(path).rglob("test_*.py")):
        parts.append(f"# {test_file.relative_to(path).as_posix()}\n{test_file.read_text(encoding='utf-8')}")
    return "\n".join(parts)


def tests_arm(anti: str | None) -> dict[str, bool]:
    """Qué lleva cada rama de la generación de tests; cada variante quita una sola cosa."""
    if anti not in (None, "sin_tests_existentes", "sin_estandares"):
        raise ValueError(f"variante desconocida: {anti}")
    return {"existing": anti != "sin_tests_existentes", "standards": anti != "sin_estandares"}


def build_tests_prompt(diff: str, *, existing: str | None) -> str:
    block = f"Tests que ya existen en el repositorio:\n{existing}\n" if existing is not None else ""
    return f"{TESTS_TASK}\n{block}\nDiff:\n{diff}"


# --- Ejecución ---------------------------------------------------------------------------------------------------------------------------------


def print_context(repo: ReviewRepo, model: str, budget: float) -> None:
    """`[contexto]` de la orden (§11.6): qué ve el proceso y que no hay capa meta, skills ni servidores MCP."""
    cmd = headless.build_command(cwd=repo.path, model=model, max_budget_usd=min(budget, 0.05), stream=True)
    init = headless.probe_context(cmd, cwd=repo.path)
    if not init:
        print("[contexto] no se pudo leer la línea init")
        return
    print(headless.context_line(init))
    problems = headless.isolation_problems(init)
    print(f"[aislamiento] {'sin skills, comandos ni servidores MCP' if not problems else '; '.join(problems)}")


def show_review(label: str, result: headless.HeadlessResult, score: Score, ledger: headless.Ledger) -> None:
    if not result.ok:
        print(f"{label} estado={result.status} {result.detail}")
        return
    by = {k: f"{v:.0%}" for k, v in sorted(precision_by_category(score).items())}
    print(
        f"{label} hallazgos={score.total} · encontrados={sorted(score.found)} · faltan={sorted(score.missed)} · falsos positivos={len(score.false_positives)} "
        f"· marcó lo correcto={len(score.flagged_ok)} · duplicados={score.duplicates} · precisión={'—' if precision(score) is None else f'{precision(score):.0%}'} {by} · coste acumulado={ledger.spent:.4f} $"
    )
    log = discard_log(score)
    if log:
        print(f"    [descartados por patrón] {log}")
    for f in score.discarded:
        # Cada descartado con su ubicación: así se ve si es un falso positivo de verdad o el mismo fallo con la línea desplazada.
        print(f"    descartado: {f.get('file')}:{f.get('line')} [{f.get('category')}] {str(f.get('problem'))[:100]}")


def run_orden(repo: ReviewRepo, args: Any, model: str, budget: float) -> None:
    diff = diff_of(repo, repo.base, repo.commit_1)
    prompt = build_review_prompt(diff, message=load("cambio_revision.json")["message_1"])
    print(f"\n=== la orden · diff del primer commit: {len(diff.splitlines())} líneas, prompt {len(prompt)} caracteres ===")
    cmd = review_command(repo.path, model=model, budget=budget, schema=review_schema())
    headless.print_command(cmd, stdin_chars=len(prompt))
    print(f"[cwd] {repo.path} · CLAUDE.md de CI: {len((repo.path / 'CLAUDE.md').read_text(encoding='utf-8'))} caracteres")
    print("[no se ejecuta nada: `--parte revision` la lanza con el prompt por stdin]")


def run_revision(repo: ReviewRepo, args: Any, model: str, budget: float) -> None:
    labels = load("cambio_revision_etiquetas.json")
    change = load("cambio_revision.json")
    disabled = (args.sin_categoria,) if args.sin_categoria else ()
    schema = review_schema(disabled)
    diff = diff_of(repo, repo.base, repo.commit_1)
    prompt = build_review_prompt(diff, message=change["message_1"], anti=args.anti, disabled=disabled)
    ledger = headless.Ledger(budget)
    print(f"\n=== revisión del primer commit · variante {args.anti or 'correcta'}{' · sin ' + args.sin_categoria if disabled else ''} · {args.repeat} ejecuciones ===")
    print("[esperado] encuentra los fallos sembrados, no marca el cambio correcto ni el patrón aceptable, y cada hallazgo trae `detected_pattern`")
    pooled = Score()
    for run in range(1, args.repeat + 1):
        cmd = review_command(repo.path, model=model, budget=min(ledger.remaining(), budget / args.repeat), schema=schema)
        result = headless.run(cmd, prompt, cwd=repo.path, schema=schema)
        ledger.add(result)
        findings = result.structured["findings"] if result.ok else []
        score = score_findings(findings, labels, scope=1)
        show_review(f"[{run}/{args.repeat}]", result, score, ledger)
        pooled.discarded += score.discarded
        pooled.found |= score.found
    if args.repeat > 1:
        print(f"[registro de descartados, {args.repeat} ejecuciones] {discard_log(pooled)}")
    print(f"\n[fin] coste=${ledger.spent:.4f} de ${budget}")


def run_rerevision(repo: ReviewRepo, args: Any, model: str, budget: float) -> None:
    labels = load("cambio_revision_etiquetas.json")
    change = load("cambio_revision.json")
    diff = diff_of(repo, repo.base, repo.commit_2)
    prior = prior_findings(labels)
    prompt = build_rereview_prompt(diff, message=change["message_2"], prior=None if args.anti == "sin_previos" else prior)
    schema = review_schema()
    ledger = headless.Ledger(budget)
    print(f"\n=== segunda revisión (diff completo de la rama) · {'sin hallazgos previos' if args.anti else 'con hallazgos previos'} · {args.repeat} ejecuciones ===")
    for run in range(1, args.repeat + 1):
        cmd = review_command(repo.path, model=model, budget=min(ledger.remaining(), budget / args.repeat), schema=schema)
        result = headless.run(cmd, prompt, cwd=repo.path, schema=schema)
        ledger.add(result)
        if not result.ok:
            print(f"[{run}/{args.repeat}] estado={result.status} {result.detail}")
            continue
        c = classify_rereview(result.structured["findings"], labels, prior)
        print(
            f"[{run}/{args.repeat}] hallazgos={c['total']} · nuevos={sorted(c['nuevos'])} · repetidos de la primera revisión={sorted(c['repetidos'])} "
            f"· de un fallo ya resuelto={c['resueltos_repetidos']} · otros={c['otros']} · coste acumulado={ledger.spent:.4f} $"
        )
    print(f"\n[fin] coste=${ledger.spent:.4f} de ${budget}")


def run_tests(repo: ReviewRepo, args: Any, model: str, budget: float) -> None:
    labels = load("cambio_revision_etiquetas.json")
    arm = tests_arm(args.anti)
    # El CLAUDE.md de la rama sin estándares es otro repositorio temporal: solo cambia esa sección.
    work = repo if arm["standards"] else build_review_repo(standards=False)
    diff = diff_of(work, work.base, work.commit_1)
    prompt = build_tests_prompt(diff, existing=existing_tests_text(work.path / "") if arm["existing"] else None)
    schema = tests_schema()
    ledger = headless.Ledger(budget)
    print(f"\n=== generación de tests · {'con' if arm['existing'] else 'sin'} tests existentes · {'con' if arm['standards'] else 'sin'} estándares en CLAUDE.md · {args.repeat} ejecuciones ===")
    for run in range(1, args.repeat + 1):
        # Sin tools: así el modelo no puede descubrir por su cuenta los tests que se le quitan del contexto.
        cmd = review_command(work.path, model=model, budget=min(ledger.remaining(), budget / args.repeat), schema=schema, tools=())
        result = headless.run(cmd, prompt, cwd=work.path, schema=schema)
        ledger.add(result)
        if not result.ok:
            print(f"[{run}/{args.repeat}] estado={result.status} {result.detail}")
            continue
        s = score_tests(result.structured["tests"], labels)
        print(f"[{run}/{args.repeat}] tests propuestos={s.total} · escenarios que ya cubren los existentes={s.duplicates} · nuevos={s.new} (sobre lo que cambió: {s.on_changed_code}) · coste acumulado={ledger.spent:.4f} $")
        for function, call_args in s.duplicated:
            print(f"    repetido: {function}({call_args})")
    print(f"\n[fin] coste=${ledger.spent:.4f} de ${budget}")


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTS, default="orden", help="`orden` solo construye y muestra la orden; el resto ejecuta `claude -p`")
    parser.add_argument("--sin-categoria", choices=CATEGORIES, help="desactiva una categoría de los criterios y del schema (4.1-S2)")
    args = parser.parse_args()
    if args.anti and args.anti not in ANTI_BY_PART.get(args.parte, []):
        parser.error(f"--anti {args.anti} no es de la parte {args.parte}: " + "; ".join(f"{p}: {', '.join(v)}" for p, v in ANTI_BY_PART.items()))
    if args.sin_categoria and args.parte != "revision":
        parser.error("--sin-categoria es de la parte revision")
    print(credentials.describe())
    model = report_model("reviewer")
    budget = report_budget(args.budget, "multiagent")
    repo = build_review_repo()
    if args.parte == "orden":
        run_orden(repo, args, model, budget)
        return 0
    print_context(repo, model, budget)
    try:
        {"revision": run_revision, "rerevision": run_rerevision, "tests": run_tests}[args.parte](repo, args, model, budget)
    except headless.BudgetExhausted as exc:
        print(f"[corte] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
