"""Tests de `harness/repaso.py` y de `narrador repaso`: lectura tolerante de `FALLOS.md`, intervalos crecientes y cola de repaso. Sin modelo.

PROPÓSITO: fijar el contrato del repaso de fallos (plan de mejoras, fase 3). La tabla de `FALLOS.md`
gana las columnas «Fecha» (día del fallo) y «Repasos» (fechas de los repasos acertados), y de ellas
sale cuándo vence cada fila: 1, 3, 7 y 14 días después del fallo o del último repaso.

POR QUÉ EXISTE: hasta ahora nada leía `FALLOS.md`. El repaso espaciado necesita saber qué filas ☐
tocan hoy y con qué pregunta se repasa cada una, sin que la persona tenga que calcularlo.

QUÉ NO HACE: no escribe en `FALLOS.md`: el narrador solo lee, y quien anota el repaso es la persona
(o la skill, en su nombre). No migra una tabla antigua: la lee tal cual, con las columnas que tenga.
"""

from datetime import date

import pytest

from tests.contrato import require

require("3.1")  # se salta entero mientras falte `harness/repaso.py`

from harness.estado import TEMPLATES, init_state  # noqa: E402
from harness.narrador import main  # noqa: E402
from harness.repaso import INTERVALS, Failure, is_due, next_due, parse_failures, review_queue  # noqa: E402

HEADER = "| Viñeta | Módulo | Qué predije o respondí | Qué ocurrió o cuál era la correcta | Por qué me equivoqué | Fecha | Repasos | Estado |"
RULE = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |"
OLD_HEADER = "| Viñeta | Módulo | Qué predije o respondí | Qué ocurrió o cuál era la correcta | Por qué me equivoqué | Estado |"
OLD_RULE = "| :--- | :--- | :--- | :--- | :--- | :---: |"
INTRO = "# FALLOS\n\nUna fila por predicción o respuesta fallida.\n\nEstado: ☐ pendiente · ☑ superado al repetirlo\n\n"


def table(*rows: str, header: str = HEADER, rule: str = RULE) -> str:
    return INTRO + "\n".join([header, rule, *rows]) + "\n"


def row(vignette="TS 1.1-K1", module="app1/01", day="2026-11-01", reviews="", state="☐") -> str:
    return f"| {vignette} | {module} | dije A | era B | confundí | {day} | {reviews} | {state} |"


def old_row(vignette="TS 1.1-K1", module="app1/01", state="☐") -> str:
    return f"| {vignette} | {module} | dije A | era B | confundí | {state} |"


def failure(day="2026-11-01", reviews=(), done=False) -> Failure:
    return Failure(
        vignette="TS 1.1-K1",
        module="app1/01",
        date=date.fromisoformat(day) if day else None,
        reviews=tuple(date.fromisoformat(value) for value in reviews),
        done=done,
    )


# --- Lectura de la tabla --------------------------------------------------------

def test_intervals_are_one_three_seven_and_fourteen_days():
    assert INTERVALS == (1, 3, 7, 14)


def test_parse_reads_the_new_columns():
    text = table(row(reviews="2026-11-02, 2026-11-05"), row("TS 2.5-K3", "app1/02", "2026-11-03", state="☑"))
    first, second = parse_failures(text)
    assert first == Failure("TS 1.1-K1", "app1/01", date(2026, 11, 1), (date(2026, 11, 2), date(2026, 11, 5)), False)
    assert (second.vignette, second.module, second.reviews, second.done) == ("TS 2.5-K3", "app1/02", (), True)


def test_parse_ignores_everything_that_is_not_a_row():
    # El título, la leyenda «Estado: ☐ pendiente…», la cabecera y la línea de alineación no son fallos.
    assert parse_failures(table()) == []
    assert parse_failures("") == []


def test_parse_tolerates_an_old_table_without_date_or_reviews():
    failures = parse_failures(table(old_row(), old_row("TS 2.5-K3", "app1/02", "☑"), header=OLD_HEADER, rule=OLD_RULE))
    assert [(f.vignette, f.date, f.reviews, f.done) for f in failures] == [
        ("TS 1.1-K1", None, (), False),
        ("TS 2.5-K3", None, (), True),
    ]


def test_parse_finds_the_columns_by_name_not_by_position():
    header = "| Estado | Viñeta | Fecha | Módulo |"
    text = "\n".join([header, "| :---: | :--- | :--- | :--- |", "| ☐ | TS 1.1-K1 | 2026-11-01 | app1/01 |"])
    assert parse_failures(text) == [Failure("TS 1.1-K1", "app1/01", date(2026, 11, 1), (), False)]


@pytest.mark.parametrize("cell", ["", "ayer", "01/11/2026", "2026-13-40"])
def test_a_missing_or_unreadable_date_is_no_date(cell):
    assert parse_failures(table(row(day=cell)))[0].date is None


def test_reviews_keep_only_what_reads_as_a_date():
    reviews = parse_failures(table(row(reviews="2026-11-02 bien; 2026-11-05 (dudé)")))[0].reviews
    assert reviews == (date(2026, 11, 2), date(2026, 11, 5))


# --- Cuándo vence una fila --------------------------------------------------------

@pytest.mark.parametrize(
    "reviews, due",
    [
        ((), "2026-11-02"),  # un día después del fallo
        (("2026-11-02",), "2026-11-05"),  # tres días después del primer repaso
        (("2026-11-02", "2026-11-05"), "2026-11-12"),
        (("2026-11-02", "2026-11-05", "2026-11-12"), "2026-11-26"),
        # Agotados los intervalos, se queda en el último: la fila sigue ☐ hasta que la persona la cierre.
        (("2026-11-02", "2026-11-05", "2026-11-12", "2026-11-26"), "2026-12-10"),
    ],
)
def test_next_due_grows_with_each_review(reviews, due):
    assert next_due(failure(reviews=reviews)) == date.fromisoformat(due)


def test_the_interval_counts_from_the_last_review_not_from_the_plan():
    # Repasó tarde (el 10 en vez del 2): el siguiente intervalo cuenta desde el día en que repasó.
    assert next_due(failure(reviews=("2026-11-10",))) == date(2026, 11, 13)


def test_a_row_without_date_is_due_now():
    undated = failure(day="")
    assert next_due(undated) is None
    assert is_due(undated, date(2020, 1, 1))


def test_is_due_from_its_day_on_and_never_once_done():
    pending = failure()
    assert not is_due(pending, date(2026, 11, 1))
    assert is_due(pending, date(2026, 11, 2)) and is_due(pending, date(2026, 12, 1))
    assert not is_due(failure(done=True), date(2026, 12, 1))


# --- Cola de repaso ----------------------------------------------------------------

def test_queue_brings_only_pending_rows_that_are_due():
    failures = parse_failures(
        table(
            row("TS 1.1-K1", day="2026-11-01"),  # vence el 2
            row("TS 1.1-K2", day="2026-11-09"),  # vence el 10: aún no
            row("TS 1.1-K3", day="2026-11-01", state="☑"),  # superada
        )
    )
    assert [entry.vignette for entry in review_queue(failures, date(2026, 11, 5))] == ["TS 1.1-K1"]
    everything = review_queue(failures, date(2026, 11, 5), include_future=True)
    assert [entry.vignette for entry in everything] == ["TS 1.1-K1", "TS 1.1-K2"]


def test_queue_groups_the_rows_of_a_vignette_and_keeps_the_most_urgent():
    failures = parse_failures(
        table(
            row("TS 1.1-K1", day="2026-11-04", reviews="2026-11-05"),  # vence el 8
            row("TS 1.1-K1", day="2026-11-01"),  # vence el 2
        )
    )
    (entry,) = review_queue(failures, date(2026, 11, 20))
    assert (entry.vignette, entry.rows, entry.due, entry.reviews) == ("TS 1.1-K1", 2, date(2026, 11, 2), 0)


def test_queue_goes_from_the_most_overdue_and_undated_rows_first():
    failures = parse_failures(
        table(
            row("TS 1.1-K2", day="2026-11-05"),
            row("TS 1.1-K1", day="2026-11-01"),
            row("TS 1.1-K3", day=""),
        )
    )
    queue = review_queue(failures, date(2026, 11, 20))
    assert [entry.vignette for entry in queue] == ["TS 1.1-K3", "TS 1.1-K1", "TS 1.1-K2"]
    assert queue[0].due is None


def test_each_entry_names_the_item_to_review_it_with():
    failures = parse_failures(
        table(
            row("TS 2.5-K3", "app1/02"),
            row("TS 1.1-K1", "app1/01_bucle_manual"),  # el módulo, escrito con su nombre de archivo
            row("TS 1.1-K2", "el primero"),  # módulo ilegible: se usa el destino de `CONCEPTOS.md`
            row("TS 3.1-K3", "D3"),
        )
    )
    items = {entry.vignette: entry.item.id for entry in review_queue(failures, date(2026, 12, 1))}
    assert items["TS 2.5-K3"] == "app1/02:C1"
    assert items["TS 1.1-K1"].startswith("app1/01:")
    assert items["TS 1.1-K2"].startswith("app1/01:")
    assert items["TS 3.1-K3"].startswith("d3:")


def test_queue_skips_rows_whose_vignette_cannot_be_read():
    # Una fila con texto libre o con una viñeta que no existe no rompe el repaso de las demás.
    failures = parse_failures(table(row("la del bucle"), row("TS 9.9-K9"), row("TS 1.1-K1")))
    assert [entry.vignette for entry in review_queue(failures, date(2026, 12, 1))] == ["TS 1.1-K1"]


# --- Plantilla y estado ------------------------------------------------------------

def test_template_has_the_new_columns_and_parses_empty():
    text = (TEMPLATES / "FALLOS.md").read_text(encoding="utf-8")
    header = next(line for line in text.splitlines() if line.startswith("| Viñeta"))
    cells = [cell.strip() for cell in header.strip("|").split("|")]
    assert cells[:2] == ["Viñeta", "Módulo"] and cells[-3:] == ["Fecha", "Repasos", "Estado"]
    assert parse_failures(text) == []
    # La plantilla dice cómo se rellenan las columnas nuevas: quien anota a mano no tiene otra referencia.
    assert "AAAA-MM-DD" in text


def test_init_never_rewrites_an_old_table(tmp_path, monkeypatch):
    for name in ("CCARF_PERFIL", "CCARF_ESTADO_DIR"):
        monkeypatch.delenv(name, raising=False)
    mine = tmp_path / "estado" / "default" / "FALLOS.md"
    mine.parent.mkdir(parents=True)
    old = table(old_row(), header=OLD_HEADER, rule=OLD_RULE)
    mine.write_text(old, encoding="utf-8")
    init_state(root=tmp_path)
    assert mine.read_text(encoding="utf-8") == old


# --- Línea de comandos -------------------------------------------------------------

@pytest.fixture
def state(tmp_path, monkeypatch):
    """Un perfil temporal: `CCARF_ESTADO_DIR` absoluto y el perfil por defecto."""
    monkeypatch.delenv("CCARF_PERFIL", raising=False)
    monkeypatch.setenv("CCARF_ESTADO_DIR", str(tmp_path))
    folder = tmp_path / "default"
    folder.mkdir()
    return folder


def test_cli_lists_what_is_due_without_showing_questions_or_answers(state, capsys):
    (state / "FALLOS.md").write_text(
        table(row("TS 2.5-K3", "app1/02", "2026-11-01"), row("TS 1.1-K2", day="2026-11-19")), encoding="utf-8"
    )
    assert main(["repaso", "--hoy", "2026-11-10"]) == 0
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if "app1/02:C1" in line)
    assert "TS 2.5-K3" in line and "2026-11-02" in line
    assert "TS 1.1-K2" not in out, "aún no vence"
    assert "- A. " not in out and "<details>" not in out, "la cola no trae enunciados: se piden con `item`"
    assert "narrador item" in out, "dice cómo pedir cada pregunta"


def test_cli_can_list_the_rows_that_are_not_due_yet(state, capsys):
    (state / "FALLOS.md").write_text(table(row("TS 1.1-K2", day="2026-11-19")), encoding="utf-8")
    assert main(["repaso", "--hoy", "2026-11-10", "--todas"]) == 0
    assert "TS 1.1-K2" in capsys.readouterr().out


def test_cli_says_so_when_nothing_is_due(state, capsys):
    (state / "FALLOS.md").write_text(table(row(state="☑")), encoding="utf-8")
    assert main(["repaso", "--hoy", "2026-11-10"]) == 0
    assert "Nada que repasar" in capsys.readouterr().out


def test_cli_reads_an_old_table_and_treats_its_rows_as_due(state, capsys):
    (state / "FALLOS.md").write_text(table(old_row(), header=OLD_HEADER, rule=OLD_RULE), encoding="utf-8")
    assert main(["repaso", "--hoy", "2026-11-10"]) == 0
    out = capsys.readouterr().out
    assert "TS 1.1-K1" in out and "sin fecha" in out


def test_cli_counts_the_rows_it_could_not_read(state, capsys):
    (state / "FALLOS.md").write_text(table(row("la del bucle"), row("TS 1.1-K1")), encoding="utf-8")
    assert main(["repaso", "--hoy", "2026-11-10"]) == 0
    out = capsys.readouterr().out
    assert "TS 1.1-K1" in out and "1 fila" in out


def test_cli_without_a_failures_file_points_to_init(state, capsys):
    assert main(["repaso"]) == 0
    assert "harness.estado init" in capsys.readouterr().out


def test_cli_rejects_a_date_that_is_not_iso(state, capsys):
    (state / "FALLOS.md").write_text(table(row()), encoding="utf-8")
    assert main(["repaso", "--hoy", "mañana"]) == 2
    assert "[narrador]" in capsys.readouterr().err
