"""Tests de `harness/estado.py`: ruta del estado personal, perfiles y copia de plantillas sin pisar nada. Sin modelo."""

import pytest

from harness.estado import BASE_VAR, PROFILE_VAR, TEMPLATES, init_state, state_dir


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # Ningún test depende de lo que haya exportado quien ejecuta pytest.
    for name in (PROFILE_VAR, BASE_VAR):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def templates(tmp_path):
    """Plantillas propias del test: no dependen del contenido real de `plantillas/estado/`."""
    folder = tmp_path / "plantillas"
    folder.mkdir()
    (folder / "FALLOS.md").write_text("plantilla fallos\n", encoding="utf-8")
    (folder / "NOTAS_PERSONALES.md").write_text("plantilla notas\n", encoding="utf-8")
    return folder


def test_defaults_without_env_or_dotenv(tmp_path):
    path, origin = state_dir(root=tmp_path)
    assert path == tmp_path / "estado" / "default"
    assert origin == "perfil=defecto base=defecto"


def test_dotenv_wins_over_process_env(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("CCARF_PERFIL=del-repo\n", encoding="utf-8")
    monkeypatch.setenv(PROFILE_VAR, "de-la-shell")
    path, origin = state_dir(root=tmp_path)
    assert path == tmp_path / "estado" / "del-repo"
    assert origin == "perfil=.env base=defecto"


def test_argument_wins_over_everything(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("CCARF_PERFIL=del-repo\n", encoding="utf-8")
    monkeypatch.setenv(PROFILE_VAR, "de-la-shell")
    path, origin = state_dir("argumento", root=tmp_path)
    assert path == tmp_path / "estado" / "argumento"
    assert origin == "perfil=argumento base=defecto"


def test_base_can_live_outside_the_clone(tmp_path, monkeypatch):
    outside = tmp_path / "fuera"
    monkeypatch.setenv(BASE_VAR, str(outside))
    path, origin = state_dir("ana", root=tmp_path / "clon")
    assert path == outside / "ana"
    assert origin == "perfil=argumento base=entorno"


def test_default_relative_base_is_the_ignored_folder(tmp_path, monkeypatch):
    monkeypatch.setenv(BASE_VAR, "estado")
    path, _ = state_dir("ana", root=tmp_path)
    assert path == tmp_path / "estado" / "ana"


@pytest.mark.parametrize("bad", ["mis_estados", "../fuera", "sub/estado"])
def test_other_relative_base_is_rejected(tmp_path, monkeypatch, bad):
    # Otra carpeta relativa quedaría dentro del clon sin que `.gitignore` la cubra.
    monkeypatch.setenv(BASE_VAR, bad)
    with pytest.raises(ValueError, match=BASE_VAR):
        state_dir("ana", root=tmp_path)


def test_init_without_templates_folder_explains_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="plantillas"):
        init_state("ana", root=tmp_path, templates=tmp_path / "no_existe")


def test_main_reports_usage_errors_without_traceback(capsys):
    from harness.estado import main

    with pytest.raises(SystemExit) as exit_info:
        main(["where", "--perfil", "../fuera"])
    assert exit_info.value.code == 2
    assert "perfil" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["..", "../otro", "a/b", "a\\b", "", " ", "con espacio", ".oculto"])
def test_invalid_profile_is_rejected(tmp_path, bad):
    # Un perfil no puede salir del directorio base ni apuntar a una ruta.
    with pytest.raises(ValueError, match="perfil"):
        state_dir(bad, root=tmp_path)


def test_invalid_profile_from_env_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv(PROFILE_VAR, "../fuera")
    with pytest.raises(ValueError, match=PROFILE_VAR):
        state_dir(root=tmp_path)


def test_init_creates_every_template(tmp_path, templates):
    created, kept = init_state("ana", root=tmp_path, templates=templates)
    target = tmp_path / "estado" / "ana"
    assert sorted(p.name for p in created) == ["FALLOS.md", "NOTAS_PERSONALES.md"]
    assert kept == []
    assert (target / "FALLOS.md").read_text(encoding="utf-8") == "plantilla fallos\n"


def test_init_never_overwrites_edited_files(tmp_path, templates):
    init_state("ana", root=tmp_path, templates=templates)
    mine = tmp_path / "estado" / "ana" / "FALLOS.md"
    mine.write_text("mis fallos\n", encoding="utf-8")
    created, kept = init_state("ana", root=tmp_path, templates=templates)
    assert created == []
    assert sorted(p.name for p in kept) == ["FALLOS.md", "NOTAS_PERSONALES.md"]
    assert mine.read_text(encoding="utf-8") == "mis fallos\n"


def test_init_fills_only_what_is_missing(tmp_path, templates):
    init_state("ana", root=tmp_path, templates=templates)
    (tmp_path / "estado" / "ana" / "NOTAS_PERSONALES.md").unlink()
    created, kept = init_state("ana", root=tmp_path, templates=templates)
    assert [p.name for p in created] == ["NOTAS_PERSONALES.md"]
    assert [p.name for p in kept] == ["FALLOS.md"]


def test_profiles_are_independent(tmp_path, templates):
    init_state("ana", root=tmp_path, templates=templates)
    init_state("luis", root=tmp_path, templates=templates)
    (tmp_path / "estado" / "ana" / "FALLOS.md").write_text("solo de ana\n", encoding="utf-8")
    assert (tmp_path / "estado" / "luis" / "FALLOS.md").read_text(encoding="utf-8") == "plantilla fallos\n"


def test_clone_without_state_dir_is_fine(tmp_path):
    # Un clon recién hecho no tiene `estado/`: resolver la ruta no debe crear nada ni fallar.
    path, _ = state_dir(root=tmp_path)
    assert not path.exists()
    assert not (tmp_path / "estado").exists()


def test_real_templates_exist():
    # Las plantillas versionadas son las que `init` copia en un clon nuevo.
    assert TEMPLATES.is_dir()
    assert {p.name for p in TEMPLATES.iterdir()} >= {"FALLOS.md", "NOTAS_PERSONALES.md"}
