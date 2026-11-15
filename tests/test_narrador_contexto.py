"""Tests del «Contexto común de la app» como fase propia del narrador (`fase appN contexto`), fuera de la ficha de cada módulo. Sin modelo.

PROPÓSITO: fijar el contrato del paquete 4.3 del plan de mejoras (fase 4). El texto común de una app
(lo que su README pone antes de «Ruta de lectura»: introducción, equivalencias, servidor y tools) se
entrega una vez por app con `uv run python -m harness.narrador fase app2 contexto`, y la `ficha` de
cada módulo deja de repetirlo: solo dice cómo pedirlo.

POR QUÉ EXISTE: la ficha traía el contexto entero en cada módulo, así que en una sesión que recorre
varios módulos de la misma app se repetía, y la skill tenía que filtrar «solo lo que este módulo usa».

QUÉ NO HACE: no decide cuándo pide la skill el contexto (eso lo dice `practica-guiada`) ni cambia las
demás fases. La no revelación de las fases del ciclo la sigue comprobando `tests/test_narrador.py`.
"""

import pytest

from tests.contrato import require

require("4.3")  # se salta entero mientras falte `harness.narrador.app_phase`

from harness.narrador import (  # noqa: E402
    APP_PHASES,
    EXTRA_PHASES,
    PHASES,
    ROOT,
    app_context,
    app_phase,
    main,
    phase,
    readme_text,
    resolve,
    route,
)

APPS = ("app1", "app2", "app3")
CONTEXT_HEADING = "## Contexto común de la app"


def test_app_phases_are_only_contexto():
    assert APP_PHASES == ("contexto",)
    # No es una fase de módulo: el ciclo y las opcionales no cambian.
    assert "contexto" not in PHASES + EXTRA_PHASES


@pytest.mark.parametrize("app", APPS)
def test_contexto_brings_the_whole_app_context(app):
    text = app_phase(app, "contexto")
    app_dir = next(ROOT.glob(f"{app}_*"))
    assert text.startswith(CONTEXT_HEADING)
    assert app_context(readme_text(app_dir)).strip() in text


def test_contexto_of_app2_names_its_server():
    assert "El servidor `helpdesk` y sus tools" in app_phase("app2", "contexto")


@pytest.mark.parametrize("app", ["App2", "APP2"])
def test_app_id_is_case_insensitive(app):
    assert app_phase(app, "contexto") == app_phase("app2", "contexto")


@pytest.mark.parametrize("app", ["app9", "app", "d3", "app2/03"])
def test_unknown_app_is_rejected(app):
    with pytest.raises(ValueError):
        app_phase(app, "contexto")


@pytest.mark.parametrize("name", ["ficha", "respuesta", "comprobaciones"])
def test_module_phases_are_not_app_phases(name):
    with pytest.raises(ValueError, match="contexto"):
        app_phase("app2", name)


def test_contexto_is_not_a_module_phase():
    with pytest.raises(ValueError):
        phase(resolve("app2/02"), "contexto")


def test_every_ficha_drops_the_context_and_says_how_to_ask_for_it():
    for module in route():
        if not module.delivered:
            continue
        text = phase(module, "ficha")
        app = module.id.split("/")[0]
        context = app_context(readme_text(module.app_dir)).strip()
        assert CONTEXT_HEADING not in text, f"{module.id}: la ficha sigue trayendo el contexto"
        # Ninguna línea larga del contexto se cuela en la ficha (salvo que la sección del módulo la repita).
        section = module.section()
        leaked = [line for line in context.splitlines() if len(line) > 40 and line in text and line not in section]
        assert not leaked, f"{module.id}: la ficha repite el contexto: {leaked[0][:60]}"
        assert f"fase {app} contexto" in text, f"{module.id}: la ficha no dice cómo pedir el contexto"


def test_ficha_keeps_vignettes_and_stops_before_the_exercise():
    text = phase(resolve("app2/02"), "ficha")
    assert "TS 1.5-K1" in text
    assert "### El ejercicio" not in text


def test_cli_contexto(capsys):
    assert main(["fase", "app2", "contexto"]) == 0
    assert "El servidor `helpdesk` y sus tools" in capsys.readouterr().out


def test_cli_unknown_app_is_a_usage_error(capsys):
    assert main(["fase", "app9", "contexto"]) == 2
    assert capsys.readouterr().err.startswith("[narrador]")


def test_cli_d3_is_unchanged(capsys):
    # `fase d3 <fase>` sigue yendo a D3, no a las fases de app.
    assert main(["fase", "d3", "pregunta"]) == 0
    assert capsys.readouterr().out
