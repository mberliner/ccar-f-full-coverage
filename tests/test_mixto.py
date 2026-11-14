"""Tests de la práctica mezclada (`harness.items.mixed_selection` y `narrador mixto`): preguntas de módulos distintos, con semilla. Sin modelo.

PROPÓSITO: fijar el contrato de la práctica mezclada (plan de mejoras, fase 3): N ítems elegidos al
azar entre las preguntas y las comprobaciones cortas de todos los módulos y de D3, opcionalmente de un
solo dominio, sin dos seguidos del mismo módulo y repetibles con una semilla.

POR QUÉ EXISTE: la práctica del curso va módulo a módulo, y el examen salta de un tema a otro. Mezclar
obliga a reconocer de qué trata cada pregunta sin la pista del módulo que se acaba de leer.

QUÉ NO HACE: no decide qué preguntas son buenas ni pondera por peso de dominio: el sorteo es uniforme
entre los ítems disponibles. No guarda qué se ha practicado.
"""

import pytest

from tests.contrato import require

require("3.2")  # se salta entero mientras falte `harness.items.mixed_selection`

from harness.items import all_items, mixed_selection  # noqa: E402
from harness.narrador import main  # noqa: E402


def ids(items) -> list[str]:
    return [item.id for item in items]


# --- Selección ---------------------------------------------------------------------

def test_default_selection_has_ten_distinct_items():
    selection = mixed_selection(seed=1)
    assert len(selection) == 10
    assert len(set(ids(selection))) == 10
    assert set(ids(selection)) <= set(ids(all_items()))


@pytest.mark.parametrize("seed", range(20))
def test_never_two_in_a_row_from_the_same_module(seed):
    sources = [item.source for item in mixed_selection(n=15, seed=seed)]
    assert all(a != b for a, b in zip(sources, sources[1:])), sources


def test_items_without_vignettes_never_enter_the_mix():
    # La pregunta de `app2/03` (apoyo, sin viñeta) no practica la guía: no sale ni sin filtro de dominio.
    with_vignettes = [item for item in all_items() if item.vignettes]
    selection = mixed_selection(n=10_000, seed=5)
    assert sorted(ids(selection)) == sorted(ids(with_vignettes))


def test_the_same_seed_gives_the_same_selection():
    assert ids(mixed_selection(n=8, seed=7)) == ids(mixed_selection(n=8, seed=7))


def test_different_seeds_give_different_selections():
    assert len({tuple(ids(mixed_selection(n=8, seed=seed))) for seed in range(10)}) > 1


@pytest.mark.parametrize("domain", ["D1", "D2", "D3", "D4", "D5"])
def test_a_domain_filter_keeps_only_items_of_that_domain(domain):
    selection = mixed_selection(n=6, domain=domain, seed=3)
    assert selection, f"no hay ítems de {domain}"
    assert all(domain in item.domains for item in selection)


def test_the_domain_is_read_in_any_case():
    assert ids(mixed_selection(n=5, domain="d2", seed=3)) == ids(mixed_selection(n=5, domain="D2", seed=3))


def test_asking_for_more_than_there_is_gives_everything_once():
    available = [item for item in all_items() if "D2" in item.domains]
    selection = mixed_selection(n=10_000, domain="D2", seed=3)
    assert sorted(ids(selection)) == sorted(ids(available))


def test_a_single_module_left_may_repeat_rather_than_drop_items():
    # Con un dominio que casi solo vive en un origen (D3), separar siempre es imposible: se prefiere
    # entregar los N pedidos a quedarse corto. Solo se repite origen cuando no queda otro.
    selection = mixed_selection(n=8, domain="D3", seed=3)
    assert len(selection) == 8 and len(set(ids(selection))) == 8


@pytest.mark.parametrize("bad", [{"n": 0}, {"n": -1}, {"domain": "D9"}, {"domain": "app1"}])
def test_bad_arguments_are_rejected(bad):
    with pytest.raises(ValueError):
        mixed_selection(seed=1, **bad)


# --- Línea de comandos ---------------------------------------------------------------

def test_cli_lists_item_ids_without_statements_or_answers(capsys):
    assert main(["mixto", "-n", "5", "--semilla", "7"]) == 0
    out = capsys.readouterr().out
    for item_id in ids(mixed_selection(n=5, seed=7)):
        assert item_id in out
    assert "- A. " not in out and "<details>" not in out, "la lista no trae enunciados: se piden con `item`"
    assert "narrador item" in out, "dice cómo pedir cada pregunta"


def test_cli_keeps_the_order_of_the_selection(capsys):
    main(["mixto", "-n", "6", "--semilla", "11"])
    out = capsys.readouterr().out
    positions = [out.index(item_id) for item_id in ids(mixed_selection(n=6, seed=11))]
    assert positions == sorted(positions)


def test_cli_prints_the_seed_so_the_session_can_be_repeated(capsys):
    # Sin `--semilla` se sortea una y se muestra: con ella se repite la misma tanda.
    assert main(["mixto", "-n", "4"]) == 0
    first = capsys.readouterr().out
    seed = next(line for line in first.splitlines() if "semilla" in line.lower()).split()[-1]
    assert main(["mixto", "-n", "4", "--semilla", seed]) == 0
    second = capsys.readouterr().out
    assert [line for line in first.splitlines() if ":" in line and "semilla" not in line.lower()] == [
        line for line in second.splitlines() if ":" in line and "semilla" not in line.lower()
    ]


def test_cli_filters_by_domain(capsys):
    assert main(["mixto", "--dominio", "D4", "-n", "3", "--semilla", "2"]) == 0
    out = capsys.readouterr().out
    for item_id in ids(mixed_selection(n=3, domain="D4", seed=2)):
        assert item_id in out


def test_cli_reports_a_bad_domain_without_a_traceback(capsys):
    assert main(["mixto", "--dominio", "D9"]) == 2
    assert "[narrador]" in capsys.readouterr().err
