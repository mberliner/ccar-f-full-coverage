"""Tests de la terminología `Task` (guía) / `Agent` (CLI) en la documentación. Sin modelo.

PROPÓSITO: la guía llama `Task` a la tool que lanza subagentes (TS 1.3-K1: `allowedTools` debe incluirla) y la CLI
de este proyecto la expone como `Agent`. Comprueba que la documentación lleve una etiqueta estable con las dos
formas donde se usa `Agent`, y que las preguntas tipo examen usen el término de la guía.

POR QUÉ EXISTE: auditoría G-08. La mayoría de tablas operativas mostraban solo `Agent`, así que el nombre más
repetido durante la práctica no era el que hay que reconocer en el examen.

QUÉ NO HACE: no toca los nombres literales de los registros (`llamadas Agent`, `tools=["Agent"]`), que son los que
emite la CLI, ni comprueba cada mención suelta: exige la etiqueta en cada sección o archivo que use `Agent`.
"""

import re
from pathlib import Path

from tests.test_readme_modulos import split_sections

ROOT = Path(__file__).resolve().parent.parent
LABEL = "`Task` (guía) / `Agent` (CLI)"
AGENT = "`Agent`"
# Archivos completos que explican o usan la tool.
WHOLE_FILES = [
    "docs/glosario.md",
    "app2_agente_con_control/CLAUDE.md",
    "app3_sistema_multiagente/CLAUDE.md",
]
README_DIRS = ["app1_agente_unico", "app2_agente_con_control", "app3_sistema_multiagente"]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def readme_sections() -> dict[str, str]:
    found = {}
    for folder in README_DIRS:
        for number, body in split_sections(read(f"{folder}/README.md")).items():
            found[f"{folder} {number}"] = body
    return found


def test_the_label_is_where_the_tool_is_explained():
    for path in WHOLE_FILES:
        assert LABEL in read(path), f"{path}: falta la etiqueta {LABEL}"


def test_every_section_that_uses_agent_carries_the_label():
    """Una sección de módulo (o archivo) que nombra la tool `Agent` dice también cómo la llama la guía."""
    missing = [name for name, body in readme_sections().items() if AGENT in body and LABEL not in body]
    assert not missing, f"secciones que usan {AGENT} sin la etiqueta {LABEL}: {missing}"


def test_exam_questions_use_the_guide_term():
    """La pregunta y su respuesta usan `Task`: en el examen es el nombre que aparece."""
    offenders = []
    for name, body in readme_sections().items():
        if "### Pregunta tipo examen" in body:
            exam = body.split("### Pregunta tipo examen", 1)[1]
            if re.search(r"`Agent`", exam):
                offenders.append(name)
    assert not offenders, f"preguntas tipo examen con `Agent` en vez de `Task`: {offenders}"
