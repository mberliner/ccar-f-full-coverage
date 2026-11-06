"""Tests de que los README de módulo no comparan modelos en una misma fila de tabla. Sin modelo.

PROPÓSITO: la guía deja fuera de alcance las métricas de comparación entre modelos. Un README puede usar un modelo
como banco de pruebas de un mecanismo (una fila por modelo y por variante, con el modelo de la medida), pero no
enfrentar dos modelos en la misma fila o cabecera de tabla. Las comparaciones y la calibración van a `docs/hallazgos.md`.

POR QUÉ EXISTE: auditoría G-04. Las tablas con una columna por modelo convertían la diferencia entre modelos en la
evidencia principal del módulo, en vez del mecanismo que enseña.

QUÉ NO HACE: no prohíbe nombrar un modelo (cada medida dice con cuál se hizo) ni revisa la prosa de las notas, y
no juzga si una fila enseña bien: solo detecta dos modelos distintos en una misma fila de tabla.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = re.compile(r"\b(?:Haiku|Sonnet|Opus|Fable) \d(?:\.\d)?\b")
# Una fila que nombra un coordinador y un subagente describe un sistema, no compara modelos.
SYSTEM_ROLES = re.compile(r"coordinador|subagentes?", re.IGNORECASE)


def comparison_rows(text: str) -> list[str]:
    """Filas de tabla (`| … |`) que nombran dos o más modelos distintos sin ser la descripción de un sistema."""
    found = []
    for line in text.splitlines():
        if line.startswith("|") and len(set(MODEL.findall(line))) >= 2 and not SYSTEM_ROLES.search(line):
            found.append(line.strip()[:90])
    return found


def test_a_row_naming_two_models_is_a_comparison():
    assert comparison_rows("| a | Haiku 5.5 | Haiku 4.5 |") == ["| a | Haiku 5.5 | Haiku 4.5 |"]
    assert comparison_rows("| x | con Haiku 5.5 y con Haiku 4.5 igual |")


def test_one_model_per_row_is_allowed():
    assert comparison_rows("| `few_shot` con Haiku 4.5 | 5 fechas incorrectas | los ejemplos arreglan el formato |") == []
    assert comparison_rows("| a | Haiku 5.5 |\n| b | Haiku 4.5 |") == []
    assert comparison_rows("Prosa: Haiku 5.5 frente a Haiku 4.5, fuera de tabla.") == []


def test_a_system_with_coordinator_and_subagent_models_is_not_a_comparison():
    assert comparison_rows("| p | coordinador Sonnet 5.5 y subagentes Haiku 5.5 | 3 repeticiones |") == []


def test_no_readme_table_row_compares_two_models():
    offenders = {}
    for readme in sorted(ROOT.glob("app*/README.md")):
        rows = comparison_rows(readme.read_text(encoding="utf-8"))
        if rows:
            offenders[readme.parent.name] = rows
    assert not offenders, f"filas de tabla que enfrentan dos modelos (mueve la comparación a docs/hallazgos.md): {offenders}"
