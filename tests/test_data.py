"""Tests de `harness/data.py`: lectura y `copy_to_temp`. Sin modelo."""

from harness.data import DATA_DIR, copy_to_temp, load


def test_load_reads_json():
    assert load("usuarios.json")


def test_copy_to_temp_copies_a_directory():
    path = copy_to_temp("repo_mesa")
    assert (path / "core" / "sla.py").is_file()
    assert path != DATA_DIR / "repo_mesa"


def test_copy_to_temp_does_not_touch_the_original():
    original = (DATA_DIR / "repo_mesa" / "config.py").read_text(encoding="utf-8")
    path = copy_to_temp("repo_mesa")
    (path / "config.py").write_text("TIMEOUT = 60\n", encoding="utf-8")
    assert (DATA_DIR / "repo_mesa" / "config.py").read_text(encoding="utf-8") == original


def test_each_call_gets_its_own_directory():
    assert copy_to_temp("repo_mesa") != copy_to_temp("repo_mesa")


def test_copy_to_temp_with_a_single_file(tmp_path):
    path = copy_to_temp("articulos_kb.json")
    assert path.is_dir() and (path / "articulos_kb.json").is_file()
