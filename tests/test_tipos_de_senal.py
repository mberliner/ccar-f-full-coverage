"""Tests de `docs/tipos-de-senal.md`: cada parte de cada módulo clasificada por tipo de señal. Sin modelo.

PROPÓSITO: no todas las ejecuciones con modelo muestran el mecanismo. El documento clasifica cada parte como
`Determinista`, `Probabilística con control positivo`, `Sin señal estable` o `Sin medir`, para que quien practica sepa
qué parte le enseña el mecanismo y cuál solo se explica. El test comprueba que cada módulo entregado tiene filas, que
los tipos son estos cuatro y que cada «Sin señal estable» está respaldado por lo que dice el README de ese módulo.

POR QUÉ EXISTE: auditoría D-02. Había ejecuciones que dejaban a la persona con una tabla histórica o una explicación
de por qué el efecto no apareció, sin avisarle antes de gastar la ejecución.

QUÉ NO HACE: no comprueba que cada clasificación sea la correcta (lo hace la revisión), ni que las cifras de la
evidencia sigan siendo las del README. Solo ata «Sin señal estable» a la presencia de «sin señal», «inestable» o
«sin diferencia» en el módulo, y exige que un módulo de ejecución obligatoria tenga al menos una parte que enseñe algo.
"""

import re
from pathlib import Path

import pytest

from harness.narrador import MODE, route

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "tipos-de-senal.md"
DETERMINISTIC = "Determinista"
POSITIVE = "Probabilística con control positivo"
NO_SIGNAL = "Sin señal estable"
UNMEASURED = "Sin medir"
TYPES = {DETERMINISTIC, POSITIVE, NO_SIGNAL, UNMEASURED}
# Cómo dice un módulo que una parte no mostró el efecto o que su resultado varía.
NO_SIGNAL_WORDS = re.compile(
    r"sin señal|inestable|sin diferencia|casi iguales|variabilidad|no se vio en el acierto|sin efecto visible|no llegó a actuar",
    re.IGNORECASE,
)


def parse_rows(text: str) -> list[list[str]]:
    """Filas `| appN/NN | parte | tipo | evidencia |` de la tabla, con las celdas limpias."""
    rows = []
    for line in text.splitlines():
        if line.startswith("| app"):
            cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            if re.fullmatch(r"app\d/\d{2}", cells[0]) and len(cells) >= 4:
                rows.append(cells)
    return rows


def delivered():
    return [module for module in route() if module.delivered]


def rows_by_module() -> dict[str, list[list[str]]]:
    grouped: dict[str, list[list[str]]] = {}
    for cells in parse_rows(DOC.read_text(encoding="utf-8")):
        grouped.setdefault(cells[0], []).append(cells)
    return grouped


# --- El analizador, con texto sintético ----------------------------------------------------------

def test_parse_rows_reads_the_table_and_skips_everything_else():
    text = f"| Módulo | Parte |\n| :--- | :--- |\n| app1/03 | `minimas` | {POSITIVE} | 14/24 |\n| nota | x | y | z |\n"
    assert parse_rows(text) == [["app1/03", "minimas", POSITIVE, "14/24"]]


def test_no_signal_words_are_recognized():
    for text in ("**sin señal**: 0 de 3", "resultado inestable", "sin diferencia con Haiku 5.5", "pueden salir casi iguales",
                 "La variabilidad entre ejecuciones es parte de la lección", "aquí no se vio en el acierto",
                 "sin efecto visible sobre el coordinador", "el bucle no llegó a actuar"):
        assert NO_SIGNAL_WORDS.search(text), text
    assert not NO_SIGNAL_WORDS.search("la tasa de cumplimiento fue del 100 %")


# --- El documento, contra los módulos reales ------------------------------------------------------

def test_the_document_defines_the_four_types():
    assert DOC.is_file(), "falta docs/tipos-de-senal.md"
    text = DOC.read_text(encoding="utf-8")
    assert all(name in text for name in TYPES)


def test_an_unmeasured_part_is_not_passed_off_as_no_signal():
    """Una parte sin medida con modelo no se marca «Sin señal estable»: eso afirmaría algo que ningún README dice."""
    rows = [cells for cells in parse_rows(DOC.read_text(encoding="utf-8")) if cells[2] == UNMEASURED]
    assert rows, "debe haber al menos una parte «Sin medir» (app3/01 `pipeline_completo`, `procedimental`; app2/02 `--anti`)"


def test_every_delivered_module_has_rows_and_no_other_module_does():
    assert sorted(rows_by_module()) == sorted(module.id for module in delivered())


def test_every_row_has_one_of_the_three_types_and_some_evidence():
    for cells in parse_rows(DOC.read_text(encoding="utf-8")):
        assert cells[2] in TYPES, f"{cells[0]} · {cells[1]}: tipo «{cells[2]}» no es uno de {sorted(TYPES)}"
        assert cells[3], f"{cells[0]} · {cells[1]}: falta la evidencia"


@pytest.mark.parametrize("module", delivered(), ids=lambda module: module.id)
def test_no_signal_rows_are_backed_by_the_module_readme(module):
    section = module.section()
    for cells in rows_by_module().get(module.id, []):
        if cells[2] == NO_SIGNAL:
            assert NO_SIGNAL_WORDS.search(section), (
                f"{module.id} · {cells[1]}: marcada «{NO_SIGNAL}» pero su README no dice «sin señal», «inestable» ni «sin diferencia»"
            )


def mandatory():
    return [module for module in delivered() if "obligatoria" in MODE.search(module.section()).group(0).lower()]


def test_the_four_mandatory_modules_are_found():
    assert [module.id for module in mandatory()] == ["app2/01", "app3/02", "app3/04", "app3/08"]


@pytest.mark.parametrize("module", mandatory(), ids=lambda module: module.id)
def test_a_mandatory_module_has_at_least_one_part_that_teaches(module):
    """Si un módulo exige ejecutar, alguna de sus partes tiene que ser determinista o mostrar una señal."""
    kinds = {cells[2] for cells in rows_by_module().get(module.id, [])}
    assert kinds & {DETERMINISTIC, POSITIVE}, f"{module.id}: es de ejecución obligatoria y ninguna parte enseña el mecanismo"
