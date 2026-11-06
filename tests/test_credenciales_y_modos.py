"""Tests de `docs/credenciales-y-modos.md`: la tabla de credencial y modo por módulo coincide con el código y los README. Sin modelo.

PROPÓSITO: la tabla dice, por módulo entregado, con qué llama al modelo, qué credencial necesita como mínimo y su
modo (ligera u obligatoria). El test clasifica cada módulo leyendo su código (AST) y compara con la tabla y con la
línea «Modo» de su README; falla si un módulo nuevo no tiene fila o si algo no coincide.

POR QUÉ EXISTE: la portada decía «hace falta una API key» y «sin ella, modo ligero», y no era cierto: el Agent SDK
funciona con suscripción y cuatro módulos son de ejecución obligatoria (auditoría C-04). Sin un test, la tabla se
desfasaría con cada módulo nuevo de las tandas C y D.

QUÉ NO HACE: no comprueba que la suscripción funcione de verdad con cada módulo del Agent SDK (eso lo dice el arnés,
`harness/credentials.py`, y no está verificado módulo a módulo), ni los costes de la tabla. Clasifica por módulo
entero: `app3/09` lleva una parte (`--ventanas`) que no usa modelo y la tabla lo anota aparte.
"""

import ast
import re
from pathlib import Path

import pytest

from harness.narrador import MODE, route

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "credenciales-y-modos.md"
# Qué dice la columna «Credencial mínima» de cada clase de módulo.
LABEL = {"api_key": "API key", "sdk": "API key o suscripción", "ninguna": "Ninguna"}
SDK_NAMES = {"isolated_options", "query", "ClaudeSDKClient"}


def classify(source: str) -> str:
    """`api_key` (Messages API o Batches), `sdk` (Agent SDK) o `ninguna` (no llama al modelo), por el AST."""
    tree = ast.parse(source)
    names: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
            names.update(alias.name for alias in node.names)
    if "anthropic" in modules or "require_api_key" in names:
        return "api_key"
    if names & SDK_NAMES:
        return "sdk"
    return "ninguna"


def table_rows() -> dict[str, list[str]]:
    """{id de módulo: celdas} de las filas `| appN/NN | … |` de la tabla."""
    rows = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if line.startswith("| app") and re.fullmatch(r"app\d/\d{2}", cells[0]):
            rows[cells[0]] = cells
    return rows


def delivered():
    return [module for module in route() if module.delivered]


# --- El clasificador, con código sintético ----------------------------------------------------------

def test_classify_tells_the_three_kinds_apart():
    assert classify("import anthropic\nclient = anthropic.Anthropic()") == "api_key"
    assert classify("def main():\n    import anthropic\n") == "api_key"
    assert classify("from harness import credentials\ncredentials.require_api_key()") == "api_key"
    assert classify("opts = isolated_options(model='m')\nasync for m in query(prompt='x', options=opts): pass") == "sdk"
    assert classify("from claude_agent_sdk import HookMatcher\nHOOK = HookMatcher(matcher='x')") == "ninguna"


def test_classify_ignores_words_in_comments_and_docstrings():
    assert classify('"""usa isolated_options y anthropic en la doc"""\n# query require_api_key\nx = 1') == "ninguna"


def test_api_key_wins_over_sdk_when_a_module_uses_both():
    assert classify("import anthropic\nopts = isolated_options()") == "api_key"


# --- La tabla, contra el código y los README reales ----------------------------------------------------

def test_the_table_has_exactly_one_row_per_delivered_module():
    assert DOC.is_file(), "falta docs/credenciales-y-modos.md"
    assert sorted(table_rows()) == sorted(module.id for module in delivered())


@pytest.mark.parametrize("module", delivered(), ids=lambda module: module.id)
def test_credential_column_matches_the_code(module):
    kind = classify(module.script.read_text(encoding="utf-8"))
    cells = table_rows()[module.id]
    assert cells[2] == LABEL[kind], f"{module.id}: el código es «{kind}» y la tabla dice «{cells[2]}»"


@pytest.mark.parametrize("module", delivered(), ids=lambda module: module.id)
def test_mode_column_matches_the_module_readme(module):
    mode = MODE.search(module.section()).group(1)
    cells = table_rows()[module.id]
    assert cells[3].startswith(mode), f"{module.id}: el README dice «{mode}» y la tabla «{cells[3]}»"


def test_the_front_page_points_to_the_table():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/credenciales-y-modos.md" in readme
