"""Tests de los conjuntos de la entrega 2 de `datos/generar_sinteticos.py` (`repo_mesa/` y `documentos.json`). Sin modelo."""

import ast
import importlib
import json
import sys

import pytest

from datos.generar_sinteticos import build_all, write


def repo_files() -> dict[str, str]:
    return {name: text for name, text in build_all().items() if name.startswith("repo_mesa/")}


def test_repo_mesa_is_valid_python():
    files = repo_files()
    assert files
    for name, text in files.items():
        ast.parse(text, name)


def test_repo_mesa_has_tests_spread_over_several_directories():
    # Para que `Glob` tenga algo que listar: varios directorios, no uno solo.
    test_dirs = {name.rsplit("/", 1)[0] for name in repo_files() if name.rsplit("/", 1)[-1].startswith("test_")}
    assert len(test_dirs) >= 3


def test_wrapper_reexports_with_alias():
    api = repo_files()["repo_mesa/api.py"]
    assert "calcular_sla as sla_ticket" in api


def test_callers_by_direct_name_and_by_alias():
    # El reto de 2.5-S5: hay llamadores que nunca escriben `calcular_sla`.
    files = repo_files()
    direct = {n for n, t in files.items() if "calcular_sla(" in t and not n.endswith(("core/sla.py", "api.py")) and "/test" not in n and not n.rsplit("/", 1)[-1].startswith("test_")}
    alias_only = {n for n, t in files.items() if "sla_ticket" in t or " as plazo" in t} - direct - {"repo_mesa/api.py"}
    assert direct and len(alias_only) >= 2


def test_sla_error_message_is_unique_to_one_file():
    # Mensaje único para buscar con `Grep`: solo aparece donde se lanza.
    matches = [n for n, t in repo_files().items() if "SLA vencido para" in t]
    assert matches == ["repo_mesa/core/sla.py"]


def test_timeout_anchor_appears_exactly_twice_in_config():
    # Precondición de 2.5-K3: `Edit` falla porque el ancla no es única.
    config = repo_files()["repo_mesa/config.py"]
    assert config.count("TIMEOUT = 30\n") == 2
    first, second = config.split("TIMEOUT = 30\n", 1)[0], config.rsplit("TIMEOUT = 30\n", 1)[0]
    assert first != second  # los dos bloques son distintos


@pytest.fixture
def repo_mesa(tmp_path):
    write(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        yield importlib.import_module("repo_mesa.api"), importlib.import_module("repo_mesa.core.sla")
    finally:
        sys.path.remove(str(tmp_path))
        for name in [m for m in sys.modules if m.startswith("repo_mesa")]:
            del sys.modules[name]


def test_alias_is_the_same_function(repo_mesa):
    api, sla = repo_mesa
    assert api.sla_ticket is sla.calcular_sla


def test_sla_within_and_over_limit(repo_mesa):
    _, sla = repo_mesa
    assert sla.calcular_sla("alta", 3)["restante_horas"] == 5
    with pytest.raises(ValueError, match="SLA vencido para"):
        sla.calcular_sla("alta", 9)


def docs() -> dict:
    return json.loads(build_all()["documentos.json"])


def test_documents_catalog_mixes_documents_and_non_documents():
    urls = docs()["urls"]
    documents = [u for u in urls if u["is_document"]]
    others = [u for u in urls if not u["is_document"]]
    assert documents and len(others) >= 3
    assert all("/docs/" in u["url"] and u["content"] for u in documents)
    assert all("/docs/" not in u["url"] and u["content"] is None for u in others)
    assert all(u["url"].startswith("https://") and ".test/" in u["url"] for u in urls)


def test_claims_have_simple_and_complex_ones_tied_to_real_articles():
    claims = docs()["afirmaciones"]
    assert {c["verifiable"] for c in claims} == {"simple", "compleja"}
    article_ids = {a["article_id"] for a in json.loads(build_all()["articulos_kb.json"])}
    for claim in claims:
        assert set(claim["article_ids"]) <= article_ids
    # Una afirmación compleja necesita más de un artículo; una simple, uno.
    assert all(len(c["article_ids"]) == 1 for c in claims if c["verifiable"] == "simple")
    assert all(len(c["article_ids"]) > 1 for c in claims if c["verifiable"] == "compleja")
