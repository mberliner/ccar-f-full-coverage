"""Tests de `harness/data.py`: lectura y `copy_to_temp`. Sin modelo.

PROPÓSITO: comprobar la lectura de los datos sintéticos y que `copy_to_temp` copia un conjunto a un directorio temporal.

POR QUÉ EXISTE: los módulos y los tests leen los datos por aquí y trabajan sobre copias; si la copia tocara el original, se editaría `datos/sinteticos/` sin pasar por el generador.

QUÉ NO HACE: no valida el contenido de los datos (eso es `tests/test_datos_sinteticos.py`) ni llama al modelo.
"""

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
