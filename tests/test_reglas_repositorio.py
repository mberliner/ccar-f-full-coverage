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
# Tests que hoy abren con su línea «Sin modelo» y una explicación libre, sin las tres piezas.
INFRA_HEADER_KNOWN: set[str] = {
    f"tests/test_{name}.py"
    for name in """
    app1_01_bucle_manual app1_02_tools_integradas app1_03_servidor_mcp app1_04_errores_estructurados
    app1_05_scoping_y_tool_choice app1_06_mcp_config app1_07_recorte_de_contexto app1_servers_catalogo
    app1_servers_mesa app2_01_prompt_vs_enforcement app2_02_hooks_pre_post app2_03_permisos
    app2_04_few_shot_y_escalamiento app2_05_multi_concern_y_handoff app2_06_sesiones app2_07_hook_reescritura
    app2_servers_helpdesk app3_01_coordinador app3_02_paralelo_y_descomposicion app3_03_tools_entre_roles
    app3_04_errores_entre_agentes app3_05_procedencia app3_06_contexto_largo app3_07_extraccion_schema
    app3_08_validacion_reintento app3_09_batches app3_10_confianza_y_revision app3_11_criterios_y_ci
    app3_11_grupo1 app3_12_grupo4 app3_12_revision_independiente app3_servers_investigacion budget cli
    config credentials data datos_entrega2 datos_entrega3 datos_entrega3c datos_entrega3d datos_sinteticos
    estado hooks_proyecto narrador offline options recorder
    """.split()
}


@pytest.mark.parametrize("path", cases(INFRA, INFRA_HEADER_KNOWN, "cabecera de infraestructura incompleta"))
def test_infrastructure_header_has_the_three_parts(path):
    text = docstring(path)
    assert [m for m in INFRA_MARKERS if m not in text] == []


# --- 3 · Aislamiento: opciones del SDK solo con `isolated_options` o `headless.build_command` -----------

# Un módulo «del SDK» es el que usa el Agent SDK para lanzar un agente o el que lanza `claude -p`.
SDK_USE = re.compile(r"\bClaudeSDKClient\b|\bClaudeAgentOptions\(|from claude_agent_sdk import[^\n]*\bquery\b|claude -p")
SDK_MODULES = sorted(p for app in APPS for p in app.glob("[0-9][0-9]_*.py") if SDK_USE.search(p.read_text(encoding="utf-8")))
SDK_KNOWN: set[str] = set()


def test_there_are_sdk_modules_to_check():
    # Si el patrón dejara de encontrar módulos, la regla pasaría en vacío.
    assert len(SDK_MODULES) >= 10


def sdk_problems(text: str) -> list[str]:
    """Qué incumple un módulo del SDK: no pasa por el arnés o construye `ClaudeAgentOptions(` a mano."""
    problems = []
    if "isolated_options(" not in text and "build_command(" not in text:
        problems.append("sin isolated_options ni build_command")
    # Nunca `ClaudeAgentOptions(` directamente: saltaría el aislamiento y el tope de coste.
    if "ClaudeAgentOptions(" in text:
        problems.append("ClaudeAgentOptions a mano")
    return problems


@pytest.mark.parametrize("path", cases(SDK_MODULES, SDK_KNOWN, "construye sus opciones a mano"))
def test_sdk_module_builds_options_through_the_harness(path):
    assert sdk_problems(path.read_text(encoding="utf-8")) == []


# --- 4 · Primera línea de cada test (`.claude/rules/tests.md`) -------------------------------------------

# Los tests bajo `datos/` quedan fuera: son datos del repositorio de juguete que analizan los módulos.
TEST_FILES = sorted(p for p in ROOT.rglob("test_*.py") if not {".venv", "node_modules"} & set(p.parts) and rel(p).split("/")[0] != "datos")
TEST_LINE_KNOWN: set[str] = {"tests/test_consola.py", "tests/test_headless.py", "tests/test_perimetro.py", "tests/test_una_vez.py"}


@pytest.mark.parametrize("path", cases(TEST_FILES, TEST_LINE_KNOWN, "primera línea sin «Sin modelo»"))
def test_first_line_says_what_it_tests_and_that_it_has_no_model(path):
    first = docstring(path).splitlines()[0] if docstring(path) else ""
    assert "Sin modelo" in first, first


# --- 5 · Errores de los servidores con `errorCategory` e `isRetryable` -------------------------------------

SERVERS = sorted(p for app in APPS for p in app.glob("servers/*.py"))
# Anti-patrones deliberados: devuelven un error genérico para que el módulo muestre su efecto.
DELIBERATE_GENERIC = {("app1_agente_unico/servers/mesa.py", "generic_error")}


def error_builders(path: Path) -> list[tuple[str, str]]:
    """[(función, código)] de cada función que construye un resultado con `is_error` verdadero."""
    source = path.read_text(encoding="utf-8")
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        marks = False
        for inner in ast.walk(node):
            if isinstance(inner, ast.Dict):
                marks |= any(isinstance(k, ast.Constant) and k.value == "is_error" and isinstance(v, ast.Constant) and v.value is True for k, v in zip(inner.keys, inner.values))
            elif isinstance(inner, ast.keyword):
                marks |= inner.arg in ("is_error", "isError") and isinstance(inner.value, ast.Constant) and inner.value.value is True
        # Solo la función más interna que lo construye: la que lo envuelve se juzga por sus propias líneas.
        if marks and not any(isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)) and c is not node for c in ast.walk(node)):
            found.append((node.name, ast.get_source_segment(source, node) or ""))
    return found


def test_servers_build_error_results():
    assert sum(len(error_builders(p)) for p in SERVERS) >= 4


@pytest.mark.parametrize("path", SERVERS, ids=rel)
def test_server_errors_carry_category_and_retryable(path):
    wrong = [
        name
        for name, code in error_builders(path)
        if (rel(path), name) not in DELIBERATE_GENERIC and not ("errorCategory" in code and "isRetryable" in code)
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


def test_server_check_detects_an_error_without_category(tmp_path):
    server = tmp_path / "malo.py"
    server.write_text(
        "def bad_err():\n    return {'content': [{'type': 'text', 'text': 'fallo'}], 'is_error': True}\n"
        "def good_err():\n    return {'content': [{'type': 'text', 'text': '{\"errorCategory\": 1, \"isRetryable\": 0}'}], 'is_error': True}\n",
        encoding="utf-8",
    )
    wrong = [name for name, code in error_builders(server) if not ("errorCategory" in code and "isRetryable" in code)]
    assert wrong == ["bad_err"]


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
