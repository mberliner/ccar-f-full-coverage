"""Tests de estructura de los README de módulo (roadmap §13, regla 5). Sin modelo.

PROPÓSITO: comprobar que cada sección `## NN · …` de `app*/README.md` contiene
los bloques «Antes de empezar» y «Pregunta tipo examen».

POR QUÉ EXISTE: la incorporación de quien llega de cero se quedó sin dueño y solo
`app1/01` la cumplía. Un test barato impide que un módulo nuevo nazca sin ella.

QUÉ NO HACE: no juzga la calidad. Que el contexto no adelante el resultado o que
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
PENDING_ONBOARDING = {
    "app1_agente_unico 02", "app1_agente_unico 03", "app1_agente_unico 04",
    "app1_agente_unico 05", "app1_agente_unico 06",
    "app2_agente_con_control 01", "app2_agente_con_control 02", "app2_agente_con_control 03",
    "app2_agente_con_control 05", "app2_agente_con_control 06", "app2_agente_con_control 07",
    "app3_sistema_multiagente 01", "app3_sistema_multiagente 02", "app3_sistema_multiagente 03",
}


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


@pytest.mark.parametrize("name", sorted(PENDING_ONBOARDING))
def test_pending_really_fail(name):
    """Una entrada pendiente que ya cumple debe borrarse de la lista."""
    sections = all_sections()
    assert name in sections, f"{name} ya no existe: bórralo de PENDING_ONBOARDING"
    assert missing_blocks(sections[name]), f"{name} ya cumple: bórralo de PENDING_ONBOARDING"
