"""Tests de `harness/narrador.py`: ruta de módulos, fases sin revelar antes de tiempo, menú y puesta en marcha. Sin modelo."""

import pytest

from harness.narrador import (
    PHASES,
    PendingModule,
    UnknownModule,
    details_body,
    menu,
    phase,
    resolve,
    route,
    setup_report,
    strip_details,
    subsections,
)

FOLDED_STEP3 = "Paso 3 · Contrastar"
FOLDED_STEP4 = "Paso 4 · Respuesta"
# Las líneas cortas («```bash», «---») se repiten legítimamente fuera de los bloques.
MIN_LEAK_LINE = 25


# --- Análisis, con texto sintético --------------------------------------------

SECTION = """
> **Qué vas a hacer:** algo.
>
> **Necesitas antes:** Nada.
>
> **Modo:** Ejecución ligera (y).

### Antes de empezar

contexto

### El ejercicio

la tarea

### Predice antes de ejecutar

1. ¿pregunta?

### Ejecutar

```bash
uv run python x.py
```

### Qué observar

mira esto

<details>
<summary>Paso 3 · Contrastar: lo que se observó</summary>

SECRETO DEL CONTRASTE
</details>

### Pregunta tipo examen

¿Cuál?

<details>
<summary>Paso 4 · Respuesta</summary>

**B.** SECRETO DE LA RESPUESTA
</details>

**Paso 5 ·** anota.
"""


def test_subsections_keep_preface_and_order():
    parts = subsections(SECTION)
    assert parts[0][0] == "" and "Qué vas a hacer" in parts[0][1]
    assert [heading for heading, _ in parts[1:]] == [
        "Antes de empezar", "El ejercicio", "Predice antes de ejecutar", "Ejecutar", "Qué observar", "Pregunta tipo examen",
    ]


def test_strip_details_removes_every_folded_block():
    stripped = strip_details(SECTION)
    assert "SECRETO" not in stripped
    assert "mira esto" in stripped and "¿Cuál?" in stripped


def test_details_body_returns_only_the_named_block():
    assert details_body(SECTION, FOLDED_STEP3).strip() == "SECRETO DEL CONTRASTE"
    assert "SECRETO DE LA RESPUESTA" in details_body(SECTION, FOLDED_STEP4)
    assert details_body(SECTION, "Paso 9") == ""


# --- Ruta y resolución de ids, sobre los README reales -------------------------

def delivered():
    return [module for module in route() if module.delivered]


def test_route_lists_the_delivered_modules():
    ids = [module.id for module in delivered()]
    assert len(ids) == 17
    assert ids[0] == "app1/01" and "app2/07" in ids and "app3/03" in ids and "app3/07" in ids
    assert all(module.script.is_file() for module in delivered())


def test_route_marks_pending_modules():
    pending = {module.id for module in route() if not module.delivered}
    assert {"app1/07", "app2/04", "app3/04"} <= pending


@pytest.mark.parametrize("text", ["app1/05", "app1/05_scoping_y_tool_choice", "app1 05", "APP1/05", "app1/5"])
def test_resolve_accepts_common_spellings(text):
    assert resolve(text).id == "app1/05"


def test_resolve_rejects_unknown_and_pending():
    with pytest.raises(UnknownModule):
        resolve("app9/01")
    with pytest.raises(UnknownModule):
        resolve("bucle")
    with pytest.raises(PendingModule):
        resolve("app2/04")


# --- Fases: nada se revela antes de tiempo, en todos los módulos ----------------

def leak_lines(block: str) -> list[str]:
    return [line.strip() for line in block.splitlines() if len(line.strip()) >= MIN_LEAK_LINE]


@pytest.mark.parametrize("module", delivered(), ids=lambda module: module.id)
def test_phases_never_reveal_ahead(module):
    texts = {name: phase(module, name) for name in PHASES}
    assert all(text.strip() for text in texts.values()), "alguna fase sale vacía"
    section = module.section()
    step3, step4 = details_body(section, FOLDED_STEP3), details_body(section, FOLDED_STEP4)
    assert step3.strip() and step4.strip(), "el módulo no tiene sus dos bloques plegados"
    before = [name for name in PHASES if PHASES.index(name) < PHASES.index("contraste")]
    for name in before + ["pregunta"]:
        for line in leak_lines(step3) + leak_lines(step4):
            assert line not in texts[name], f"{name} adelanta: {line[:60]}"
    for line in leak_lines(step4):
        assert line not in texts["contraste"], f"contraste adelanta la respuesta: {line[:60]}"
    for line in leak_lines(step3):
        assert line in texts["contraste"]
    for line in leak_lines(step4):
        assert line in texts["respuesta"]


@pytest.mark.parametrize("module", delivered(), ids=lambda module: module.id)
def test_script_header_only_in_answer_phase(module):
    header = leak_lines(module.script_docstring())
    assert header, "el script no tiene docstring de cabecera"
    section = module.section()
    for name in PHASES:
        text = phase(module, name)
        if name == "respuesta":
            assert [line for line in header if line in text] == header
        else:
            # Una frase que el README de la sección ya dice igual no es fuga de la cabecera (app1/06).
            found = [line for line in header if line in text and line not in section]
            assert not found, f"{name} trae la cabecera del script: {found[0][:60]}"


def test_phase_order_follows_the_cycle():
    assert PHASES == ("ficha", "ejercicio", "ejecutar", "contraste", "pregunta", "respuesta")


def test_ficha_brings_vignettes_and_app_context():
    module = resolve("app2/02")
    text = phase(module, "ficha")
    assert "TS 1.5-K1" in text
    assert "El servidor `helpdesk` y sus tools" in text
    assert "### El ejercicio" not in text


def test_commands_come_after_predictions():
    module = resolve("app2/02")
    assert "uv run python" not in phase(module, "ejercicio")
    assert "Predice antes de ejecutar" in phase(module, "ejercicio")
    assert "uv run python app2_agente_con_control/02_hooks_pre_post.py" in phase(module, "ejecutar")


def test_step5_line_goes_with_the_answer():
    module = resolve("app1/01")
    assert "Paso 5" not in phase(module, "pregunta")
    assert "Paso 5" in phase(module, "respuesta")


def test_unknown_phase_is_rejected():
    with pytest.raises(ValueError):
        phase(resolve("app1/01"), "todo")


# --- Menú ----------------------------------------------------------------------

def test_menu_lists_modules_recommends_first_and_offers_setup():
    text = menu()
    for module in delivered():
        assert module.id in text
    star_lines = [line for line in text.splitlines() if "★" in line]
    assert len(star_lines) == 1 and "app1/01" in star_lines[0]
    assert "próximamente" in text and "app2/04" in text
    assert "Puesta en marcha" in text and "d3_claude_code" in text


def test_menu_explains_how_module_names_are_read():
    # `app1/05` no se entiende sin saber que es «app 1, módulo 05»; la leyenda va antes de la lista.
    text = menu()
    legend = [line for line in text.splitlines() if "appN/NN" in line]
    assert len(legend) == 1
    assert text.index(legend[0]) < text.index("## app1")


def test_menu_does_not_reveal_module_content():
    text = menu()
    for module in delivered():
        for line in leak_lines(details_body(module.section(), FOLDED_STEP4)):
            assert line not in text


# --- Puesta en marcha ----------------------------------------------------------

@pytest.fixture
def clean_env(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "CCARF_PERFIL", "CCARF_ESTADO_DIR"):
        monkeypatch.delenv(name, raising=False)


def test_setup_without_env_or_state(tmp_path, clean_env):
    report = setup_report(root=tmp_path, environ={})
    assert "✗" in report
    assert "cp .env.example .env" in report
    assert "harness.estado init" in report


def test_setup_with_env_and_state_never_shows_secrets(tmp_path, clean_env):
    sentinel = "sk-ant-CENTINELA-NO-DEBE-SALIR"
    (tmp_path / ".env").write_text(f"ANTHROPIC_API_KEY={sentinel}\n", encoding="utf-8")
    state = tmp_path / "estado" / "default"
    state.mkdir(parents=True)
    (state / "FALLOS.md").write_text("# FALLOS\n", encoding="utf-8")
    report = setup_report(root=tmp_path, environ={})
    assert sentinel not in report
    assert "✗" not in report
    assert str(state / "FALLOS.md") in report


def test_setup_accepts_key_from_environment_without_showing_it(tmp_path, clean_env):
    sentinel = "sk-ant-OTRO-CENTINELA"
    report = setup_report(root=tmp_path, environ={"ANTHROPIC_API_KEY": sentinel})
    assert sentinel not in report
    credential_line = next(line for line in report.splitlines() if "credencial" in line.lower())
    assert "✓" in credential_line
