"""Test de perímetro (roadmap §3, regla 5, y §11.2).

PROPÓSITO: marcar en el código de las apps y del arnés cualquier uso de los
mecanismos de `perimetro_excluido.yaml`.

POR QUÉ EXISTE: practicar con funcionalidades que la guía v1.0 no reconoce
entrena respuestas que en el examen son distractores. Una revisión a ojo no
escala a 25 módulos.

QUÉ NO HACE: no revisa comentarios ni docstrings, porque ahí se permite citar lo
nuevo como `EN PRODUCCIÓN (no evaluable)`. Por eso analiza el AST y no el
texto. No llama al modelo.
"""

import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED = yaml.safe_load((Path(__file__).parent / "perimetro_excluido.yaml").read_text(encoding="utf-8"))
SCANNED = ["app1_agente_unico", "app2_agente_con_control", "app3_sistema_multiagente", "harness"]
# Valores con los que una variable de entorno queda apagada (neutralizar, regla 4).
DISABLED_VALUES = {"0", "false"}


def docstring_nodes(tree: ast.AST) -> set[int]:
    """Ids de los nodos que son docstrings, para no tratarlos como código."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ids.add(id(first.value))
    return ids


def violations(source: str, filename: str = "<src>") -> list[str]:
    """Lista «archivo:línea patrón» de cada uso excluido en el código fuente."""
    tree = ast.parse(source, filename)
    docs = docstring_nodes(tree)
    by_kind: dict[str, set[str]] = {}
    for entry in EXCLUDED:
        by_kind.setdefault(entry["kind"], set()).add(entry["pattern"])
    found = []

    def hit(node: ast.AST, pattern: str) -> None:
        found.append(f"{filename}:{node.lineno} {pattern}")

    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Name):
            names = [node.id]
        elif isinstance(node, ast.Attribute):
            names = [node.attr]
        elif isinstance(node, ast.keyword) and node.arg:
            names = [node.arg]
        elif isinstance(node, ast.alias):
            names = [node.name.split(".")[-1], node.asname or ""]
        for name in names:
            if name in by_kind.get("identifier", ()):
                hit(node, name)

        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            if node.value in by_kind.get("string", ()):
                hit(node, node.value)

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in by_kind.get("env_enabled", ()):
                    off = isinstance(value, ast.Constant) and str(value.value).lower() in DISABLED_VALUES
                    if not off:
                        hit(key, key.value)
    return found


def test_exclusion_list_is_well_formed():
    assert EXCLUDED
    for entry in EXCLUDED:
        assert set(entry) == {"pattern", "kind", "motivo"}, entry
        assert entry["kind"] in {"identifier", "string", "env_enabled"}, entry


def test_repository_stays_inside_perimeter():
    found = []
    for folder in SCANNED:
        for path in sorted((ROOT / folder).rglob("*.py")):
            found += violations(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())
    assert found == []


# --- Autotests del detector --------------------------------------------------


def test_detects_excluded_usage():
    source = (
        "options = ClaudeAgentOptions(output_format={'type': 'json_schema'},\n"
        "    allowed_tools=['Read', 'Workflow'],\n"
        "    env={'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': '1'})\n"
    )
    # ast.walk no garantiza el orden de recorrido: se compara como conjunto.
    assert sorted(v.split(" ")[1] for v in violations(source)) == sorted(
        ["output_format", "Workflow", "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"]
    )


def test_ignores_comments_docstrings_and_disabled_env():
    source = (
        '"""EN PRODUCCIÓN (no evaluable): output_format y la tool Workflow."""\n'
        "# EN PRODUCCIÓN (no evaluable): output_format sustituiría a tool_use.\n"
        "env = {'CLAUDE_CODE_FORK_SUBAGENT': '0'}\n"
        "text = 'el Workflow de la empresa'\n"
    )
    assert violations(source) == []
