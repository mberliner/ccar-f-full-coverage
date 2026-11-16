"""Tests de las reglas del repositorio que nadie vigilaba (cabeceras, aislamiento del SDK, primera línea de los tests y errores de los servidores). Sin modelo.

PROPÓSITO: fijar el contrato de reglas del paquete 5.4 (fase 5). Cada regla recorre los archivos a los
que aplica y da un caso por archivo. Lo que hoy no cumple va en una lista explícita con
`xfail(strict=True)`: al arreglar un archivo, su marca sobra, el caso falla y obliga a sacarlo de la
lista en el mismo cambio.

POR QUÉ EXISTE: las reglas viven en `docs/estandares-codigo.md` y en `.claude/rules/`, pero solo
algunas tenían test. Sin uno, un módulo nuevo sin cabecera completa o con `ClaudeAgentOptions` a mano
pasaba la suite.

QUÉ NO HACE: no juzga si la cabecera dice algo útil ni si el aislamiento está bien configurado (eso es
`tests/test_options.py`): solo comprueba que las piezas están. No importa ningún módulo de app:
lee su texto y su AST.
"""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APPS = sorted(ROOT.glob("app[0-9]_*"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def docstring(path: Path) -> str:
    """El docstring del módulo o, si no tiene, su bloque inicial de comentarios (`harness/__init__.py`)."""
    source = path.read_text(encoding="utf-8")
    found = ast.get_docstring(ast.parse(source))
    if found:
        return found
    lines = []
    for line in source.splitlines():
        if not line.startswith("#"):
            break
        lines.append(line.lstrip("# "))
    return "\n".join(lines)


def cases(paths: list[Path], known: set[str], reason: str) -> list:
    """Un caso por archivo; los de `known` con `xfail(strict=True)`."""
    marks = [pytest.mark.xfail(strict=True, reason=reason)]
    return [pytest.param(p, id=rel(p), marks=marks if rel(p) in known else []) for p in paths]


def test_known_lists_only_name_existing_files():
    # Una entrada que ya no existe sería una marca que nunca salta.
    for known in (APP_HEADER_KNOWN, INFRA_HEADER_KNOWN, SDK_KNOWN, TEST_LINE_KNOWN):
        assert all((ROOT / name).is_file() for name in known), sorted(n for n in known if not (ROOT / n).is_file())


# --- 1 · Cabecera de módulo de app ---------------------------------------------------------------------

APP_MODULES = sorted(p for app in APPS for p in app.glob("[0-9][0-9]_*.py"))
# Los módulos de apoyo sin viñeta propia escriben `CONCEPTO (apoyo, …)`: vale igual.
APP_MARKERS = ["CONCEPTO","QUÉ DICE LA GUÍA", "POR QUÉ IMPORTA", "ANTI-PATRÓN / TRAMPA DEL EXAMEN"]
# Módulos que hoy no traen las cuatro piezas (5.4 los completa sin tocar el texto de las que ya hay).
APP_HEADER_KNOWN: set[str] = set()


@pytest.mark.parametrize("path", cases(APP_MODULES, APP_HEADER_KNOWN, "cabecera de módulo incompleta"))
def test_app_module_header_has_the_four_parts(path):
    text = docstring(path)
    assert [m for m in APP_MARKERS if m not in text] == []


# --- 2 · Cabecera de infraestructura -------------------------------------------------------------------

INFRA = sorted(
    p
    for p in [
        *ROOT.glob("harness/*.py"),
        *ROOT.glob("datos/*.py"),
        *ROOT.glob(".claude/hooks/*.py"),
        *ROOT.glob("tests/*.py"),
        *(p for app in APPS for p in app.glob("servers/*.py")),
        *(p for app in APPS for p in app.glob("*.py") if not re.match(r"\d\d_", p.name)),
    ]
    # Un `__init__.py` vacío no tiene nada que explicar.
    if p.read_text(encoding="utf-8").strip()
)
INFRA_MARKERS = ["PROPÓSITO", "POR QUÉ EXISTE", "QUÉ NO HACE"]
# Archivos que hoy no traen las tres piezas (5.4a los completó: la lista queda vacía).
INFRA_HEADER_KNOWN: set[str] = set()


@pytest.mark.parametrize("path", cases(INFRA, INFRA_HEADER_KNOWN, "cabecera de infraestructura incompleta"))
def test_infrastructure_header_has_the_three_parts(path):
    text = docstring(path)
    assert [m for m in INFRA_MARKERS if m not in text] == []


# --- 3 · Aislamiento: opciones del SDK solo con `isolated_options` o `headless.build_command` -----------

def called_names(tree: ast.AST) -> set[str]:
    """Nombres de las funciones que el AST llama de verdad (`f(...)` o `x.f(...)`): un comentario o un docstring no cuentan."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            names.add(func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else "")
    return names


SDK_IMPORTS = {"harness.recorder", "harness.headless", "headless"}
# Nombres de `claude_agent_sdk` que lanzan un agente. Importar solo `HookMatcher` (app2/07, sin modelo) no es
# usar el SDK para lanzar nada: sería un incumplimiento falso.
SDK_LAUNCHERS = {"ClaudeSDKClient", "ClaudeAgentOptions", "query"}


def is_sdk_module(text: str) -> bool:
    """Un módulo «del SDK» lanza un agente (importa `ClaudeSDKClient`, `query`…, o `harness.recorder`) o `claude -p` (`harness.headless`)."""
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            # `import claude_agent_sdk` (o `import harness.recorder`).
            modules = {alias.name for alias in node.names}
            if "claude_agent_sdk" in modules or SDK_IMPORTS & modules:
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = {alias.name for alias in node.names}
            # `from harness import recorder` nombra el módulo en `names`, no en `module`.
            qualified = {module} | {f"{module}.{n}" for n in names}
            if SDK_IMPORTS & qualified:
                return True
            if module.split(".")[0] == "claude_agent_sdk" and SDK_LAUNCHERS & names:
                return True
    return False
SDK_MODULES = sorted(p for app in APPS for p in app.glob("[0-9][0-9]_*.py") if is_sdk_module(p.read_text(encoding="utf-8")))
SDK_KNOWN: set[str] = set()


def test_there_are_sdk_modules_to_check():
    # Si la detección dejara de encontrar módulos, la regla pasaría en vacío.
    assert len(SDK_MODULES) >= 10


def sdk_problems(text: str) -> list[str]:
    """Qué incumple un módulo del SDK: no pasa por el arnés o construye `ClaudeAgentOptions(` a mano."""
    calls = called_names(ast.parse(text))
    problems = []
    if not {"isolated_options", "build_command"} & calls:
        problems.append("sin isolated_options ni build_command")
    # Nunca `ClaudeAgentOptions(` directamente: saltaría el aislamiento y el tope de coste.
    if "ClaudeAgentOptions" in calls:
        problems.append("ClaudeAgentOptions a mano")
    return problems


@pytest.mark.parametrize("path", cases(SDK_MODULES, SDK_KNOWN, "construye sus opciones a mano"))
def test_sdk_module_builds_options_through_the_harness(path):
    assert sdk_problems(path.read_text(encoding="utf-8")) == []


# --- 4 · Primera línea de cada test (`.claude/rules/tests.md`) -------------------------------------------

# Los tests bajo `datos/` quedan fuera: son datos del repositorio de juguete que analizan los módulos.
TEST_FILES = sorted(p for p in ROOT.rglob("test_*.py") if not {".venv", "node_modules"} & set(p.parts) and rel(p).split("/")[0] != "datos")
TEST_LINE_KNOWN: set[str] = set()


@pytest.mark.parametrize("path", cases(TEST_FILES, TEST_LINE_KNOWN, "primera línea sin «Sin modelo»"))
def test_first_line_says_what_it_tests_and_that_it_has_no_model(path):
    first = docstring(path).splitlines()[0] if docstring(path) else ""
    assert "Sin modelo" in first, first


# --- 5 · Errores de los servidores con `errorCategory` e `isRetryable` -------------------------------------

SERVERS = sorted(p for app in APPS for p in app.glob("servers/*.py"))
# Anti-patrones deliberados: devuelven un error genérico para que el módulo muestre su efecto.
DELIBERATE_GENERIC = {("app1_agente_unico/servers/mesa.py", "generic_error")}


ERROR_KEYS = ("errorCategory", "isRetryable")
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)


def own_nodes(function: ast.AST):
    """Los nodos de la función sin bajar a sus funciones anidadas (cada una se juzga por separado)."""
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, FUNCTIONS):
            stack.extend(ast.iter_child_nodes(node))


def error_builders(text: str) -> list[tuple[str, set[str]]]:
    """[(función, claves de ERROR_KEYS presentes)] de cada función que construye un resultado con `is_error` verdadero.

    Las claves se buscan en el AST de la propia función (claves de dict, argumentos con nombre y cadenas,
    sin su docstring): un comentario que las nombre no cuenta.
    """
    found = []
    for function in ast.walk(ast.parse(text)):
        if not isinstance(function, FUNCTIONS):
            continue
        nodes = list(own_nodes(function))
        marks = any(
            (isinstance(n, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == "is_error" and isinstance(v, ast.Constant) and v.value is True for k, v in zip(n.keys, n.values)))
            or (isinstance(n, ast.keyword) and n.arg in ("is_error", "isError") and isinstance(n.value, ast.Constant) and n.value.value is True)
            for n in nodes
        )
        if not marks:
            continue
        # El docstring es la primera expresión-cadena del cuerpo: se excluye para que no valga como metadato.
        doc = function.body[0].value if function.body and isinstance(function.body[0], ast.Expr) else None
        present = set()
        for n in nodes:
            strings = [n.value] if isinstance(n, ast.Constant) and isinstance(n.value, str) and n is not doc else []
            names = [n.arg] if isinstance(n, ast.keyword) and n.arg else []
            present |= {key for key in ERROR_KEYS if key in names or any(key in s for s in strings)}
        found.append((function.name, present))
    return found


def test_servers_build_error_results():
    assert sum(len(error_builders(p.read_text(encoding="utf-8"))) for p in SERVERS) >= 4


@pytest.mark.parametrize("path", SERVERS, ids=rel)
def test_server_errors_carry_category_and_retryable(path):
    wrong = [
        name
        for name, present in error_builders(path.read_text(encoding="utf-8"))
        if (rel(path), name) not in DELIBERATE_GENERIC and present != set(ERROR_KEYS)
    ]
    assert wrong == []


# --- Control positivo: cada comprobación detecta el incumplimiento en archivos sintéticos ------------------
# Sin esto, una comprobación mal escrita pasaría en verde sobre todo el repositorio sin vigilar nada.


def test_header_checks_detect_missing_parts(tmp_path):
    app = tmp_path / "01_demo.py"
    app.write_text('"""Resumen.\n\nCONCEPTO [TS 1.1-K1]: solo una parte.\n"""\n', encoding="utf-8")
    infra = tmp_path / "helper.py"
    infra.write_text('"""Helper.\n\nPROPÓSITO: algo.\n"""\n', encoding="utf-8")
    assert [m for m in APP_MARKERS if m not in docstring(app)] == ["QUÉ DICE LA GUÍA", "POR QUÉ IMPORTA", "ANTI-PATRÓN / TRAMPA DEL EXAMEN"]
    assert [m for m in INFRA_MARKERS if m not in docstring(infra)] == ["POR QUÉ EXISTE", "QUÉ NO HACE"]


def test_header_check_reads_a_comment_header(tmp_path):
    commented = tmp_path / "__init__.py"
    commented.write_text("# PROPÓSITO: a\n# POR QUÉ EXISTE: b\n# QUÉ NO HACE: c\nimport os\n", encoding="utf-8")
    assert [m for m in INFRA_MARKERS if m not in docstring(commented)] == []


def test_first_line_check_detects_a_missing_sin_modelo(tmp_path):
    bad = tmp_path / "test_algo.py"
    bad.write_text('"""Tests de algo.\n\nPROPÓSITO: a.\n"""\n', encoding="utf-8")
    assert "Sin modelo" not in docstring(bad).splitlines()[0]


def test_sdk_check_detects_options_built_by_hand():
    assert sdk_problems("from claude_agent_sdk import ClaudeAgentOptions, query\nopts = ClaudeAgentOptions()\n") == [
        "sin isolated_options ni build_command",
        "ClaudeAgentOptions a mano",
    ]
    assert sdk_problems("options = isolated_options(max_budget_usd=0.1)\n") == []


def wrong_builders(text: str) -> list[str]:
    return [name for name, present in error_builders(text) if present != set(ERROR_KEYS)]


def test_sdk_check_ignores_a_comment_that_quotes_the_constructor():
    # Un comentario o un docstring con `ClaudeAgentOptions(` no es una llamada.
    quoted = '"""Nunca ClaudeAgentOptions( a mano."""\n# ClaudeAgentOptions( está prohibido\noptions = isolated_options()\n'
    assert sdk_problems(quoted) == []


def test_sdk_detection_reads_multiline_imports_and_headless():
    multiline = "from claude_agent_sdk import (\n    ClaudeSDKClient,\n    HookMatcher,\n)\n"
    assert is_sdk_module(multiline)
    assert is_sdk_module("from harness.recorder import record\n")
    assert is_sdk_module("from harness import headless\n")
    # Importar solo `HookMatcher` no lanza ningún agente, y nombrar el SDK en un comentario tampoco.
    assert not is_sdk_module("from claude_agent_sdk import HookMatcher\n")
    assert not is_sdk_module("# usa claude_agent_sdk y claude -p\nimport json\n")


def test_server_check_detects_an_error_without_category():
    server = (
        "def bad_err():\n    return {'content': [{'type': 'text', 'text': 'fallo'}], 'is_error': True}\n"
        "def good_err():\n    return {'content': [{'type': 'text', 'text': '{\"errorCategory\": 1, \"isRetryable\": 0}'}], 'is_error': True}\n"
    )
    assert wrong_builders(server) == ["bad_err"]


def test_server_check_detects_a_nested_function_that_returns_is_error_without_metadata():
    # La función envolvente tiene los metadatos, la anidada no: antes la envolvente se descartaba y la anidada pasaba.
    server = (
        "def outer():\n    meta = {'errorCategory': 'x', 'isRetryable': False}\n"
        "    def inner():\n        return {'is_error': True}\n    return inner, meta\n"
    )
    assert wrong_builders(server) == ["inner"]


def test_server_check_does_not_accept_a_comment_with_both_names():
    server = "def bad_err():\n    # errorCategory e isRetryable van aquí\n    return {'is_error': True}\n"
    assert wrong_builders(server) == ["bad_err"]
    docstring_only = 'def bad_err():\n    """errorCategory, isRetryable."""\n    return {\'is_error\': True}\n'
    assert wrong_builders(docstring_only) == ["bad_err"]


# --- Comprobación en vivo, sin modelo: los constructores de error de cada servidor dan las dos claves ---------


def assert_structured(payload_text: str) -> None:
    data = json.loads(payload_text)
    assert isinstance(data.get("errorCategory"), str) and data["errorCategory"].strip()
    assert isinstance(data.get("isRetryable"), bool)
    assert isinstance(data.get("message"), str) and data["message"].strip()


def test_server_error_builders_return_category_and_retryable_at_runtime(tmp_path):
    from app1_agente_unico.servers import catalogo_stdio, mesa
    from app2_agente_con_control.servers import helpdesk
    from app3_sistema_multiagente.servers import investigacion
    from harness.offline import call_tool
    from tests.cargar import load

    for raw in (
        mesa.error("not_found", "No existe TCK-999", retryable=False),
        helpdesk.error("business_rule", "Reembolso denegado", retryable=False),
        investigacion.transient_error({"source_id": "SRC-1", "name": "Monitor"}),
        investigacion.structured_error("Fuente desconocida", errorCategory="not_found"),
        investigacion.validation_error(""),
    ):
        assert raw["is_error"] is True
        assert_structured(raw["content"][0]["text"])

    stdio_err = catalogo_stdio.error_result("SKU desconocido", errorCategory="not_found", isRetryable=False)
    assert stdio_err.is_error is True
    assert_structured(stdio_err.content[0].text)

    # El scratchpad MCP de `app3/06` se construye en el módulo: guardar un hallazgo vacío también da error estructurado.
    scratch = {t.name: t for t in load("app3_sistema_multiagente/06_contexto_largo.py").make_scratchpad_tools(tmp_path)}
    miss = call_tool(scratch["save_finding"], {"source_id": "SRC-1", "claim": ""})
    assert miss.is_error is True
    assert_structured(miss.text)
