"""Tests de estructura de los README de módulo (roadmap §13, regla 5). Sin modelo.

PROPÓSITO: comprobar que cada sección `## NN · …` de `app*/README.md` contiene
los bloques «Antes de empezar» y «Pregunta tipo examen», y que sigue la forma de
la plantilla en lo que es determinista: «Predice antes de ejecutar» antes de
«Ejecutar» (el ciclo de §13), el resultado medido plegado en «Resultado de
referencia» y la indicación de ejecución obligatoria o ligera, la ficha del
principio y los pasos 3–5 con nombre (prueba de usabilidad del Hito T).

POR QUÉ EXISTE: la incorporación de quien llega de cero se quedó sin dueño y solo
`app1/01` la cumplía. Un test barato impide que un módulo nuevo nazca sin ella.

QUÉ NO HACE: no juzga la calidad ni decide qué módulos son obligatorios. Que el contexto no adelante el resultado o que
la predicción pida patrones y no valores lo comprueba la revisión independiente.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("Antes de empezar", "Pregunta tipo examen")

# Módulos entregados antes de la regla 5 que aún no tienen «Antes de empezar».
# Se vacía según avanza la retroadaptación; al quedar vacía, el hito T está cerrado.
# `test_pending_really_fail` obliga a borrar una entrada en cuanto el módulo cumple.
PENDING_ONBOARDING: set[str] = set()


def split_sections(text: str) -> dict[str, str]:
    """Devuelve {número de módulo: texto de su sección `## NN · …`} (hasta el siguiente `## `)."""
    sections: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"## (\d{2}) ·", line)
        if match:
            current = match.group(1)
            sections[current] = ""
        elif line.startswith("## "):
            current = None  # otra sección de nivel 2: ya no es del módulo
        elif current is not None:
            sections[current] += line + "\n"
    return sections


def missing_blocks(section: str) -> list[str]:
    return [block for block in REQUIRED if block not in section]


PREDICT = "### Predice antes de ejecutar"
RUN = "### Ejecutar"
BEFORE = "### Antes de empezar"
FICHA = ("> **Qué vas a hacer:**", "> **Necesitas antes:**", "> **Modo:**")
FOLDED = "<summary>Paso 3 · Contrastar"
ANSWER = "<summary>Paso 4 · Respuesta"
STEP5 = "**Paso 5 ·**"
RUN_MODE = re.compile(r"> \*\*Modo:\*\* [Ee]jecución (obligatoria|ligera)")


def shape_problems(section: str) -> list[str]:
    """Desvíos deterministas de la plantilla: ficha, orden del ciclo, bloques plegados y paso 5."""
    problems = []
    start = section.find(BEFORE)
    head = section if start < 0 else section[:start]
    if not all(line in head for line in FICHA):
        problems.append("falta la ficha (Qué vas a hacer · Necesitas antes · Modo) antes de «Antes de empezar»")
    elif not RUN_MODE.search(head):
        problems.append("la ficha no dice si la ejecución es obligatoria o ligera")
    if PREDICT not in section or RUN not in section:
        problems.append("faltan «Predice antes de ejecutar» o «Ejecutar» como `###`")
    elif section.index(PREDICT) > section.index(RUN):
        problems.append("«Predice antes de ejecutar» va después de «Ejecutar»")
    if FOLDED not in section:
        problems.append("sin «Paso 3 · Contrastar» plegado")
    if ANSWER not in section or STEP5 not in section:
        problems.append("falta «Paso 4 · Respuesta» o la línea «Paso 5»")
    return problems


def all_sections() -> dict[str, str]:
    found = {}
    for readme in sorted(ROOT.glob("app*/README.md")):
        for number, body in split_sections(readme.read_text(encoding="utf-8")).items():
            found[f"{readme.parent.name} {number}"] = body
    return found


# --- Lógica del analizador, con texto sintético -------------------------------

def test_split_sections_stops_at_next_level_two():
    text = "## 01 · A\nuno\n### Sub\ndos\n## Otra cosa\nfuera\n## 02 · B\ntres\n"
    sections = split_sections(text)
    assert set(sections) == {"01", "02"}
    assert "dos" in sections["01"] and "fuera" not in sections["01"]


def test_missing_blocks_reports_each_absent_block():
    assert missing_blocks("### Antes de empezar\n### Pregunta tipo examen") == []
    assert missing_blocks("### Pregunta tipo examen") == ["Antes de empezar"]
    assert missing_blocks("nada") == list(REQUIRED)


def test_shape_problems_detects_each_deviation():
    ficha = "> **Qué vas a hacer:** x.\n> **Necesitas antes:** nada.\n> **Modo:** ejecución ligera (y).\n"
    body = f"{PREDICT}\n1. ?\n{RUN}\n{FOLDED}: z</summary>\n{ANSWER}</summary>\n{STEP5} anota\n"
    good = f"{ficha}{BEFORE}\n{body}"
    assert shape_problems(good) == []
    late = f"{BEFORE}\n{ficha}{body}"
    assert shape_problems(late) == ["falta la ficha (Qué vas a hacer · Necesitas antes · Modo) antes de «Antes de empezar»"]
    no_mode = good.replace("ejecución ligera", "a tu gusto")
    assert shape_problems(no_mode) == ["la ficha no dice si la ejecución es obligatoria o ligera"]
    swapped = good.replace(f"{PREDICT}\n1. ?\n{RUN}", f"{RUN}\n{PREDICT}\n1. ?")
    assert shape_problems(swapped) == ["«Predice antes de ejecutar» va después de «Ejecutar»"]
    no_steps = good.replace(FOLDED, "<summary>Resultado").replace(STEP5, "")
    assert len(shape_problems(no_steps)) == 2


# --- Comprobación sobre los README reales -------------------------------------

def test_readmes_have_module_sections():
    assert all_sections(), "no se encontró ninguna sección `## NN ·` en app*/README.md"


def test_every_module_has_required_blocks():
    failing = {
        name: missing_blocks(body)
        for name, body in all_sections().items()
        if missing_blocks(body) and name not in PENDING_ONBOARDING
    }
    assert not failing, f"módulos sin los bloques exigidos (roadmap §13, regla 5): {failing}"


def test_every_module_follows_template_shape():
    failing = {
        name: shape_problems(body)
        for name, body in all_sections().items()
        if shape_problems(body)
    }
    assert not failing, f"módulos que se desvían de plantillas/modulo/README.md: {failing}"


@pytest.mark.parametrize("name", sorted(PENDING_ONBOARDING))
def test_pending_really_fail(name):
    """Una entrada pendiente que ya cumple debe borrarse de la lista."""
    sections = all_sections()
    assert name in sections, f"{name} ya no existe: bórralo de PENDING_ONBOARDING"
    assert missing_blocks(sections[name]), f"{name} ya cumple: bórralo de PENDING_ONBOARDING"
