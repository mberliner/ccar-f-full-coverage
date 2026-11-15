"""Tests de la salida estándar para quien estudia y de `--repeat` (paquete 5.3): `[mecanismo]`, `[esperado]`, `[clave]`, `[medida]`, el recorte de `[respuesta completa]` y los módulos que rechazan `--repeat`. Sin modelo.

PROPÓSITO: fijar el contrato del paquete 5.3. Toda ejecución abre con `[mecanismo]` (viñeta y una
frase) y `[esperado]`, marca la medida principal como `[clave]` antes de las demás `[medida]`, recorta
`[respuesta completa]` salvo con `--verbose` y nombra la variante correcta siempre igual
(`correcta`). Los formatos de partida son el `[escenario]`/`[esperado]` de app2/07 y los bloques
numerados de app3/10; el primer módulo migrado es app1/01. De los cinco módulos en que `--repeat` se
aceptaba sin efecto, `app2/05` y la parte `paralelo` de `app3/02` pasan a repetir (tope repartido y una
línea `[clave]` con la tasa o la aceleración de cada pasada) y los demás lo rechazan con un error
claro; app2/07 pasa a `build_parser`.

POR QUÉ EXISTE: cada módulo imprimía su resultado a su manera, y quien estudia tenía que buscar cuál de
las líneas era la medida que contesta la predicción. Un `--repeat 5` que no repite nada engaña: parece
una tasa y es una sola ejecución.

QUÉ NO HACE: no migra los módulos que no nombra (eso sigue en 5.3 módulo a módulo) ni cambia qué
miden. El parser de cada módulo sale de su `make_parser()`; el bucle de repeticiones de `app2/05` y
`app3/02` se prueba con `main_async(argv)` y dobles de `preamble`, `run_once` y `part_parallel`.
"""

import asyncio
import re
from pathlib import Path

import pytest

from tests.contrato import require

require("5.3")  # se salta entero mientras falte `harness.salida`

from harness import salida  # noqa: E402
from harness.cli import build_parser  # noqa: E402
from tests.cargar import load  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


# --- harness.salida --------------------------------------------------------------------------------------


def test_the_correct_variant_has_one_name():
    assert salida.CORRECT_VARIANT == "correcta"
    assert salida.variant_label(None) == "correcta"
    assert salida.variant_label("") == "correcta"
    assert salida.variant_label("tope") == "tope"


def test_mechanism_line_names_the_vignette_and_one_sentence():
    assert salida.mechanism_line("TS 1.1-K1", "el bucle sigue mientras haya tool_use") == "[mecanismo] TS 1.1-K1 · el bucle sigue mientras haya tool_use"
    assert salida.mechanism_line("TS 5.5-K1, K3", "frase").startswith("[mecanismo] TS 5.5-K1, K3 · ")


@pytest.mark.parametrize("vignette, sentence", [("1.1-K1", "frase"), ("TS 1.1", "frase"), ("TS 1.1-K1", ""), ("TS 1.1-K1", "dos\nlíneas")])
def test_mechanism_line_rejects_a_bad_vignette_or_sentence(vignette, sentence):
    with pytest.raises(ValueError):
        salida.mechanism_line(vignette, sentence)


def test_simple_lines():
    assert salida.expected_line("para con end_turn") == "[esperado] para con end_turn"
    assert salida.key_line("parada=end_turn") == "[clave] parada=end_turn"
    assert salida.measure_line("iteraciones=2") == "[medida] iteraciones=2"
    with pytest.raises(ValueError):
        salida.key_line("")


def test_full_response_is_cut_unless_verbose():
    limit = salida.RESPONSE_LIMIT
    assert isinstance(limit, int) and limit > 0
    long = "x" * (limit + 37)
    cut = salida.full_response(long, verbose=False)
    assert cut.startswith("[respuesta completa] " + "x" * limit)
    assert "x" * (limit + 1) not in cut
    assert "37 caracteres más" in cut and "--verbose" in cut
    assert salida.full_response(long, verbose=True) == "[respuesta completa] " + long


def test_full_response_at_the_limit_is_not_cut():
    exact = "y" * salida.RESPONSE_LIMIT
    assert salida.full_response(exact, verbose=False) == "[respuesta completa] " + exact


@pytest.mark.parametrize("empty", [None, ""])
def test_full_response_without_text(empty):
    assert salida.full_response(empty, verbose=False) == "[respuesta completa] (sin respuesta)"


def test_render_puts_the_lines_in_the_standard_order():
    text = salida.render(
        mechanism=("TS 1.1-K1", "frase"), expected="esperado", key="parada=end_turn", measures=["a=1", "b=2"], response="r", verbose=False
    )
    assert text.splitlines() == [
        "[mecanismo] TS 1.1-K1 · frase",
        "[esperado] esperado",
        "[clave] parada=end_turn",
        "[medida] a=1",
        "[medida] b=2",
        "[respuesta completa] r",
    ]


def test_render_without_measures_or_response():
    text = salida.render(mechanism=("TS 1.1-K1", "frase"), expected="e", key="k")
    assert text.splitlines() == ["[mecanismo] TS 1.1-K1 · frase", "[esperado] e", "[clave] k"]


# --- build_parser: --verbose y --repeat sin efecto ------------------------------------------------------


def test_verbose_is_opt_in(capsys):
    # Decidido en la revisión (2026-11-15): solo lo lleva el módulo que recorta su respuesta; en los demás
    # sería una opción aceptada sin efecto, como lo era `--repeat`.
    with_verbose = build_parser("d", anti_variants=[], verbose=True)
    assert with_verbose.parse_args([]).verbose is False
    assert with_verbose.parse_args(["--verbose"]).verbose is True
    with pytest.raises(SystemExit):
        build_parser("d", anti_variants=[]).parse_args(["--verbose"])
    capsys.readouterr()


def test_app1_01_is_the_only_module_with_verbose_for_now():
    # La salida estándar se aplica en 5.3 solo a app1/01; si se extiende, esta lista crece con ella.
    with_flag = [p.relative_to(ROOT).as_posix() for p in APP_MODULES if "verbose=True" in p.read_text(encoding="utf-8")]
    assert with_flag == ["app1_agente_unico/01_bucle_manual.py"]


def test_no_repeat_rejects_more_than_one_run_with_the_reason(capsys):
    parser = build_parser("d", anti_variants=[], no_repeat="la demostración es determinista")
    assert parser.parse_args(["--repeat", "1"]).repeat == 1
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--repeat", "3"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--repeat" in err and "la demostración es determinista" in err


# Módulo → argumentos obligatorios. Decisión de 5.0 (detalle en `NOTAS.md`): en estos, una repetición
# no da una tasa con sentido, así que `--repeat N>1` se rechaza en lugar de ignorarse. `app2/05` y la
# parte `paralelo` de `app3/02` sí repiten (abajo); las demás partes de `app3/02` lo rechazan.
NO_REPEAT = {
    "app2_agente_con_control/03_permisos.py": [],
    "app2_agente_con_control/06_sesiones.py": [],
    "app2_agente_con_control/07_hook_reescritura.py": [],
    "app3_sistema_multiagente/09_batches.py": [],
}


@pytest.mark.parametrize("module", sorted(NO_REPEAT))
def test_modules_without_repeat_reject_it(module, capsys):
    parser = load(module).make_parser()
    assert parser.parse_args(["--repeat", "1", *NO_REPEAT[module]]).repeat == 1
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--repeat", "2", *NO_REPEAT[module]])
    assert exc.value.code == 2
    assert "--repeat" in capsys.readouterr().err


@pytest.mark.parametrize("part", ["refinamiento", "descomposicion", "legacy"])
def test_app3_02_rejects_repeat_outside_the_parallel_part(part, capsys):
    # Las partes narrativas se leen una vez; solo `paralelo` mide una latencia que varía entre pasadas.
    # Depende de la parte, así que no es `no_repeat` del parser: `check_repeat(args)` sale con 2 y el motivo.
    mod = load("app3_sistema_multiagente/02_paralelo_y_descomposicion.py")
    mod.check_repeat(mod.make_parser().parse_args(["--parte", part, "--repeat", "1"]))  # 1 sigue valiendo
    with pytest.raises(SystemExit) as exc:
        mod.check_repeat(mod.make_parser().parse_args(["--parte", part, "--repeat", "2"]))
    assert exc.value.code == 2
    assert "--repeat" in capsys.readouterr().err


def fake_preamble(models: list[str], budget: float):
    """Sustituto de `harness.cli.preamble` con la firma de 5.1: no imprime ni lee credenciales."""
    return lambda _requested, *_roles, **_kw: (models, budget)


def test_app2_05_repeats_the_conversation_splitting_the_cap_and_reports_the_rate(monkeypatch, capsys):
    # `app2/05` mide si el handoff llega completo; con N ejecuciones da una tasa (se pidió en la revisión de 5.0).
    mod = load("app2_agente_con_control/05_multi_concern_y_handoff.py")
    assert mod.make_parser().parse_args(["--repeat", "3"]).repeat == 3
    outcomes = iter([[], ["falta la fecha"], []])  # problemas del handoff por ejecución: 2 de 3 completos
    budgets = []

    async def run_once(args, budget, model):
        assert (args.anti, model) == ("resumen", "modelo-agent")
        budgets.append(budget)
        return next(outcomes)

    monkeypatch.setattr(mod, "preamble", fake_preamble(["modelo-agent"], 0.30))
    monkeypatch.setattr(mod, "run_once", run_once)
    assert asyncio.run(mod.main_async(["--anti", "resumen", "--repeat", "3"])) == 0
    out = capsys.readouterr().out
    assert budgets == pytest.approx([0.10, 0.10, 0.10])
    assert [line for line in out.splitlines() if line.startswith("=== ejecución")] == [
        "=== ejecución 1/3 · variante resumen ===",
        "=== ejecución 2/3 · variante resumen ===",
        "=== ejecución 3/3 · variante resumen ===",
    ]
    assert "[clave] handoff completo 2/3 (67 %)" in out.splitlines()


def test_app2_05_counts_a_run_without_escalation_as_incomplete(monkeypatch, capsys):
    # `run_once` devuelve `None` si no hubo escalamiento: no hay handoff que dar por completo.
    mod = load("app2_agente_con_control/05_multi_concern_y_handoff.py")
    outcomes = iter([None, []])

    async def run_once(args, budget, model):
        return next(outcomes)

    monkeypatch.setattr(mod, "preamble", fake_preamble(["modelo-agent"], 0.20))
    monkeypatch.setattr(mod, "run_once", run_once)
    asyncio.run(mod.main_async(["--repeat", "2"]))
    assert "[clave] handoff completo 1/2 (50 %)" in capsys.readouterr().out.splitlines()


def test_app3_02_repeats_the_parallel_part_and_reports_each_speedup(monkeypatch, capsys):
    # `paralelo` es de ejecución obligatoria y su aceleración varía entre pasadas: N ejecuciones la muestran.
    mod = load("app3_sistema_multiagente/02_paralelo_y_descomposicion.py")
    ratios = iter([2.1, None, 1.8])  # `None`: una pasada sin las dos medidas (p. ej. con `--anti`)
    budgets = []

    async def part_parallel(args, budget, model, subagent_model):
        assert (args.parte, model, subagent_model) == ("paralelo", "modelo-coordinator", "modelo-subagent")
        budgets.append(budget)
        return next(ratios)

    monkeypatch.setattr(mod, "preamble", fake_preamble(["modelo-coordinator", "modelo-subagent"], 0.90))
    monkeypatch.setattr(mod, "part_parallel", part_parallel)
    assert asyncio.run(mod.main_async(["--parte", "paralelo", "--repeat", "3"])) == 0
    out = capsys.readouterr().out
    assert budgets == pytest.approx([0.30, 0.30, 0.30])
    assert sum(line.startswith("=== ejecución") for line in out.splitlines()) == 3
    assert "[clave] aceleración por ejecución: ×2.10, —, ×1.80" in out.splitlines()


def test_app2_07_uses_build_parser_and_keeps_its_anti():
    args = load("app2_agente_con_control/07_hook_reescritura.py").make_parser().parse_args(["--anti"])
    assert args.anti == "deny"


# --- La variante correcta se llama igual en todos los módulos ---------------------------------------------

APP_MODULES = sorted(p for p in ROOT.glob("app[0-9]_*/[0-9][0-9]_*.py"))


@pytest.mark.parametrize("path", APP_MODULES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_correct_variant_is_never_named_otherwise(path):
    # Hoy hay `case facts`, `hooks`, `puerta`, `updatedInput`… en lugar de `correcta`.
    names = re.findall(r"anti or ['\"]([^'\"]+)['\"]", path.read_text(encoding="utf-8"))
    assert [n for n in names if n != "correcta"] == []


# --- app1/01, el primer módulo con la salida estándar -----------------------------------------------------


@pytest.fixture(scope="module")
def bucle():
    return load("app1_agente_unico/01_bucle_manual.py")


def test_app1_01_declares_its_mechanism_and_what_each_variant_expects(bucle):
    vignette, sentence = bucle.MECHANISM
    assert vignette.startswith("TS 1.1-") and sentence
    salida.mechanism_line(vignette, sentence)  # no lanza: viñeta y frase válidas
    assert set(bucle.EXPECTED) == {"correcta", *bucle.ANTI_VARIANTS}
    assert all(bucle.EXPECTED.values())


@pytest.mark.parametrize("anti", [None, "tope"])
def test_app1_01_summary_follows_the_standard_format(bucle, anti):
    result = bucle.LoopResult(stop="end_turn", iterations=2, history=[], final_text="z" * (salida.RESPONSE_LIMIT + 10))
    lines = bucle.summary(result, anti=anti, verbose=False).splitlines()
    assert lines[0] == salida.mechanism_line(*bucle.MECHANISM)
    assert lines[1] == salida.expected_line(bucle.EXPECTED[salida.variant_label(anti)])
    assert [line for line in lines if line.startswith("[clave]")] == [lines[2]]
    assert "parada=end_turn" in lines[2]
    assert all(line.startswith("[medida]") for line in lines[3:-1])
    assert lines[-1] == salida.full_response(result.final_text, verbose=False)


def test_app1_01_summary_shows_the_whole_answer_with_verbose(bucle):
    result = bucle.LoopResult(stop="end_turn", iterations=1, history=[], final_text="z" * (salida.RESPONSE_LIMIT + 10))
    assert bucle.summary(result, anti=None, verbose=True).splitlines()[-1] == "[respuesta completa] " + result.final_text
