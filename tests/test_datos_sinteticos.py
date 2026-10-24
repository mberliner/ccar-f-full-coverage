"""Tests de `datos/generar_sinteticos.py`: determinismo, sincronía con disco e invariantes. Sin modelo."""

import json

from datos.generar_sinteticos import REIMBURSEMENT_THRESHOLD_EUR, build_all, check, write


def load(name: str):
    return json.loads(build_all()[name])


def test_generation_is_deterministic():
    assert build_all() == build_all()


def test_committed_files_match_generator():
    # Si falla, alguien editó datos/sinteticos/ a mano o cambió el script sin regenerar.
    assert check() == []


def test_check_detects_manual_edit(tmp_path):
    write(tmp_path)
    assert check(tmp_path) == []
    (tmp_path / "tickets.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "extra.json").write_text("{}\n", encoding="utf-8")
    assert check(tmp_path) == ["difiere tickets.json", "sobra extra.json"]


def test_every_ticket_has_label_and_valid_user():
    tickets = load("tickets.json")
    labels = load("tickets_etiquetas.json")
    user_ids = {u["user_id"] for u in load("usuarios.json")}
    assert {t["ticket_id"] for t in tickets} == set(labels)
    assert all(t["user_id"] in user_ids or labels[t["ticket_id"]]["expected_action"] == "ask_identifier" for t in tickets)


def test_homonyms_exist_in_different_departments():
    lauras = [u for u in load("usuarios.json") if u["name"] == "Laura Gómez"]
    assert len(lauras) == 2 and lauras[0]["department"] != lauras[1]["department"]


def test_reimbursements_cover_the_threshold_boundary():
    amounts = {t["amount_eur"] for t in load("tickets.json") if t["amount_eur"] is not None}
    assert REIMBURSEMENT_THRESHOLD_EUR in amounts
    assert any(a < REIMBURSEMENT_THRESHOLD_EUR for a in amounts)
    assert any(a > REIMBURSEMENT_THRESHOLD_EUR for a in amounts)


def test_statuses_and_dates_come_in_mixed_formats():
    tickets = load("tickets.json")
    assert len({t["status"] for t in tickets}) > 3
    assert {type(t["created_at"]) for t in tickets} == {str, int}


def test_superseded_article_points_to_newer_one():
    articles = {a["article_id"]: a for a in load("articulos_kb.json")}
    old = [a for a in articles.values() if a["superseded_by"]]
    assert len(old) == 1
    assert old[0]["updated_at"] < articles[old[0]["superseded_by"]]["updated_at"]


def test_only_synthetic_email_domain():
    assert all(u["email"].endswith(".test") for u in load("usuarios.json"))


def legacy_files():
    return {name: text for name, text in build_all().items() if name.startswith("legacy_inventario/")}


def test_legacy_package_is_valid_python_without_tests():
    files = legacy_files()
    assert 5 <= len(files) - 1 <= 7  # módulos, sin contar __init__.py
    assert not any("test" in name.split("/")[-1] for name in files)
    for name, text in files.items():
        compile(text, name, "exec")


def test_legacy_hidden_dependency_only_inside_function():
    # depreciacion depende de almacen, pero no en sus imports de cabecera:
    # solo se ve leyendo el cuerpo de valor_actual.
    text = legacy_files()["legacy_inventario/depreciacion.py"]
    header = text.split("def ")[0]
    assert "almacen" not in header
    assert "from . import almacen" in text and "_CACHE_ASIGNADOS" in text


def test_legacy_package_runs(tmp_path):
    import importlib
    import sys
    from datetime import date

    write(tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        almacen = importlib.import_module("legacy_inventario.almacen")
        asignaciones = importlib.import_module("legacy_inventario.asignaciones")
        informes = importlib.import_module("legacy_inventario.informes")
        almacen.reset()
        almacen.alta("SN-1", "portatil", 1000.0, "01/01/2020")
        hoy = date(2026, 1, 1)
        assert informes.valor_total(hoy) == 0.0
        # La dependencia escondida cambia el resultado: asignado conserva un 10 %.
        asignaciones.asignar("SN-1", "EMP-1001", "02/01/2020")
        assert informes.valor_total(hoy) == 100.0
    finally:
        sys.path.remove(str(tmp_path))
        for name in [m for m in sys.modules if m.startswith("legacy_inventario")]:
            del sys.modules[name]
