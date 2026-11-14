"""Tests de la lectura de la celda «Viñeta» de `FALLOS.md` (`harness.repaso.vignette_of`): varias viñetas, solo la TS y texto libre. Sin modelo.

PROPÓSITO: fijar cómo se lee una celda «Viñeta» escrita a mano. De la celda sale una sola viñeta para
repasar: la primera completa (`TS 3.5-K4 / S5` → `TS 3.5-K4`) o, si solo nombra la task statement
(`TS 5.5 (afín: …)` → `TS 5.5`), la TS, que se repasa con un ítem de esa TS.

POR QUÉ EXISTE: el contrato de 3.1 exigía la viñeta exacta, y con un `FALLOS.md` real el repaso
descartó todas las filas: quien anota un fallo escribe varias viñetas en la celda, añade un comentario
o solo conoce la TS. Un repaso que no lee lo que la persona escribe no sirve.

QUÉ NO HACE: no corrige ni reescribe la celda (el repaso solo lee `FALLOS.md`) y no reparte una fila
entre varias viñetas: se repasa con la primera. Una celda sin ninguna TS sigue contándose como ilegible.
"""

import re
from datetime import date
from pathlib import Path

import pytest

from tests.contrato import require

require("3.7-codigo")  # se salta entero mientras falte `harness.repaso.vignette_of`

from harness.items import UnknownItem, item_for  # noqa: E402
from harness.narrador import main  # noqa: E402
from harness.repaso import parse_failures, review_queue, unreadable_rows, vignette_of  # noqa: E402
from tests.test_repaso import old_row, row, table  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONCEPT_ROW = re.compile(r"^\| (TS \d\.\d-[KS]\d) \| (\S+) \| ☑ \|", re.MULTILINE)


def first_vignette_of(ts: str) -> str:
    """La primera viñeta introducida de una TS, en el orden de `CONCEPTOS.md`."""
    text = (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8")
    return next(vignette for vignette, _ in CONCEPT_ROW.findall(text) if vignette.startswith(ts + "-"))


# --- La celda ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "cell, vignette",
    [
        ("TS 1.1-K1", "TS 1.1-K1"),
        ("TS 3.5-K4 / S5", "TS 3.5-K4"),
        ("TS 4.3-K1 / K3 / K4", "TS 4.3-K1"),
        ("TS 2.5-K3, K4, S3", "TS 2.5-K3"),
        ("TS 4.6-K1/K2 y 4.6-K3/S2 (afín: la correspondencia es inferencia)", "TS 4.6-K1"),
        ("  TS 5.6-K3 / S3  ", "TS 5.6-K3"),
        # Solo la task statement: se repasa con un ítem de esa TS.
        ("TS 5.5 (afín: el patrón no está en la guía)", "TS 5.5"),
        ("TS 4.3 (campos obligatorios; la K/S exacta no la confirma la ficha)", "TS 4.3"),
        ("TS 1.2 / 1.3 (cobertura del tema al delegar)", "TS 1.2"),
        # Una viñeta completa manda sobre una TS suelta que vaya antes.
        ("de TS 4.1, en concreto TS 4.1-S2", "TS 4.1-S2"),
    ],
)
def test_the_cell_gives_its_first_vignette_or_its_task_statement(cell, vignette):
    assert vignette_of(cell) == vignette


@pytest.mark.parametrize("cell", ["la del bucle", "Delimitar con etiquetas XML (afín: no hay viñeta)", ""])
def test_a_cell_without_a_task_statement_is_left_as_written(cell):
    assert vignette_of(cell) == cell.strip()


def test_parse_keeps_the_vignette_read_from_the_cell():
    failures = parse_failures(table(row("TS 3.5-K4 / S5", "d3"), row("TS 5.5 (afín: no está en la guía)", "sin módulo")))
    assert [failure.vignette for failure in failures] == ["TS 3.5-K4", "TS 5.5"]


# --- El ítem de una TS -----------------------------------------------------------------

@pytest.mark.parametrize("ts", ["TS 5.5", "TS 4.3", "TS 1.2", "TS 3.4"])
def test_a_task_statement_is_reviewed_with_the_item_of_its_first_vignette(ts):
    item = item_for(ts)
    assert item == item_for(first_vignette_of(ts))
    assert item.source == "d3" or any(vignette.startswith(ts + "-") for vignette in item.vignettes)


def test_a_task_statement_keeps_the_module_the_person_noted():
    # Con módulo legible, la TS se repasa en ese módulo, igual que una viñeta completa.
    assert item_for("TS 4.3", "app3/07").source == "app3/07"


def test_an_unknown_task_statement_is_rejected():
    with pytest.raises(UnknownItem):
        item_for("TS 9.9")


# --- La cola -----------------------------------------------------------------------------

def test_rows_written_by_hand_enter_the_queue():
    failures = parse_failures(
        table(
            old_row("TS 3.5-K4 / S5", "d3 (práctica improvisada, sin módulo narrado)"),
            old_row("TS 4.1-K2 / S1", "app3/11 (y simulacro externo)"),
            old_row("TS 5.5 (afín: el patrón no está en la guía)", "ejercicio de un deck externo, sin módulo"),
            old_row("Delimitar con etiquetas XML (afín: no hay viñeta)", "simulacro externo"),
            header="| Viñeta | Módulo | Qué predije o respondí | Qué ocurrió o cuál era la correcta | Por qué me equivoqué | Estado |",
            rule="| :--- | :--- | :--- | :--- | :--- | :---: |",
        )
    )
    queue = review_queue(failures, date(2026, 11, 14))
    assert [(entry.vignette, entry.item.source) for entry in queue] == [
        ("TS 3.5-K4", "d3"),
        ("TS 4.1-K2", "app3/11"),
        ("TS 5.5", item_for("TS 5.5").source),
    ]
    assert unreadable_rows(failures) == 1


def test_rows_that_name_the_same_first_vignette_are_one_entry():
    failures = parse_failures(table(row("TS 5.5-K1 / K2", "sin módulo"), row("TS 5.5-K1", "app3/10")))
    queue = review_queue(failures, date(2026, 12, 1))
    assert [(entry.vignette, entry.rows) for entry in queue] == [("TS 5.5-K1", 2)]


def test_a_task_statement_and_one_of_its_vignettes_are_two_entries():
    # «TS 5.5» a secas no dice qué viñeta falló: no se funde con las filas de «TS 5.5-K1».
    failures = parse_failures(table(row("TS 5.5 (afín)", "sin módulo"), row("TS 5.5-K1", "app3/10")))
    assert sorted(entry.vignette for entry in review_queue(failures, date(2026, 12, 1))) == ["TS 5.5", "TS 5.5-K1"]


# --- Línea de comandos -------------------------------------------------------------------

def test_cli_lists_the_rows_written_by_hand(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("CCARF_PERFIL", raising=False)
    monkeypatch.setenv("CCARF_ESTADO_DIR", str(tmp_path))
    (tmp_path / "default").mkdir()
    (tmp_path / "default" / "FALLOS.md").write_text(
        table(row("TS 3.5-K4 / S5", "d3 (práctica improvisada)"), row("TS 5.5 (afín: no está en la guía)", "deck externo")),
        encoding="utf-8",
    )
    assert main(["repaso", "--hoy", "2026-11-14"]) == 0
    out = capsys.readouterr().out
    assert "TS 3.5-K4" in out and "TS 5.5" in out
    assert "sin viñeta reconocible" not in out and "Nada que repasar" not in out
