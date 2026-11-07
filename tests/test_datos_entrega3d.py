"""Tests de los conjuntos de la tanda D de la entrega 3 (`escalamiento_*.json` e `inventario_equipos*.json`). Sin modelo.

PROPÓSITO: `app2/04` evalúa al agente contra casos de escalamiento con etiqueta y le da ejemplos *few-shot* que no
pueden ser esos mismos casos (TS 4.2-K3: generalizar, no memorizar); `app1/07` necesita un inventario con 40 campos
por equipo, de los que solo 5 hacen falta (TS 5.1-K3). Si el generador cambia y esto deja de cumplirse, el módulo
deja de enseñar su lección y ningún otro test lo notaría.
"""

import json

from datos.generar_sinteticos import build_all

KINDS = {"explicit_human", "frustration", "policy_gap", "no_progress", "ambiguous_user"}
ACTIONS = {"escalate_now", "offer_resolution", "escalate_policy_gap", "escalate_no_progress", "ask_identifier"}
# 4.2-S1: de 2 a 4 ejemplos. El de «no se puede avanzar» falta a propósito: es un patrón sin ejemplo (4.2-K3).
EXAMPLE_ACTIONS = ACTIONS - {"escalate_no_progress"}


def cases() -> list[dict]:
    return json.loads(build_all()["escalamiento_casos.json"])


def case_labels() -> dict:
    return json.loads(build_all()["escalamiento_casos_etiquetas.json"])


def examples() -> list[dict]:
    return json.loads(build_all()["escalamiento_ejemplos.json"])


def inventory() -> dict:
    return json.loads(build_all()["inventario_equipos.json"])


def inventory_labels() -> dict:
    return json.loads(build_all()["inventario_equipos_etiquetas.json"])


def test_every_case_has_a_label_and_the_case_never_carries_it():
    assert {c["case_id"] for c in cases()} == set(case_labels())
    for case in cases():
        assert "expected_action" not in case and "kind" not in case
        assert case["text"].strip()
    for label in case_labels().values():
        assert label["kind"] in KINDS and label["expected_action"] in ACTIONS


def test_every_kind_is_covered_and_policy_gap_includes_price_matching():
    labels = case_labels()
    by_kind = {k: [c for c in cases() if labels[c["case_id"]]["kind"] == k] for k in KINDS}
    assert all(len(v) >= 2 for v in by_kind.values())
    # El ejemplo de la guía: igualar el precio de la competencia cuando la política solo contempla el propio sitio.
    assert any("compet" in c["text"].lower() for c in by_kind["policy_gap"])


def test_the_action_follows_the_kind():
    expected = {
        "explicit_human": "escalate_now",
        "frustration": "offer_resolution",
        "policy_gap": "escalate_policy_gap",
        "no_progress": "escalate_no_progress",
        "ambiguous_user": "ask_identifier",
    }
    for label in case_labels().values():
        assert label["expected_action"] == expected[label["kind"]]


def test_frustration_cases_have_a_followup_that_insists_on_a_person():
    """5.2-K2/S3: se ofrece resolver y solo se escala si el cliente reitera su preferencia por un humano."""
    for case in cases():
        label = case_labels()[case["case_id"]]
        if label["kind"] == "frustration":
            assert case["followup"].strip()
            assert label["after_followup"] == "escalate_now"
        else:
            assert "followup" not in case


def test_ambiguous_cases_list_every_matching_employee():
    users = json.loads(build_all()["usuarios.json"])
    for case in cases():
        label = case_labels()[case["case_id"]]
        if label["kind"] != "ambiguous_user":
            continue
        name = label["name"]
        matches = sorted(u["user_id"] for u in users if u["name"] == name)
        assert len(matches) >= 2
        assert label["candidates"] == matches
        assert name in case["text"]


def test_few_shot_examples_are_disjoint_from_the_evaluation_cases():
    """4.2-K3: si un ejemplo es un caso evaluado, la medida premia la memoria y no el juicio."""
    evaluated = {c["text"] for c in cases()}
    all_tickets = {t["body"] if "body" in t else t.get("text", "") for t in json.loads(build_all()["tickets.json"])}
    for example in examples():
        assert example["text"] not in evaluated
        assert example["text"] not in all_tickets
    assert 2 <= len(examples()) <= 4  # 4.2-S1: de 2 a 4 ejemplos


def test_examples_show_the_reasoning_and_cover_four_of_the_five_actions():
    for example in examples():
        assert example["action"] in ACTIONS
        assert len(example["reasoning"].split()) >= 12, "el razonamiento es lo que se enseña (4.2-S1)"
        assert example["rejected_alternative"].strip()
    assert {e["action"] for e in examples()} == EXAMPLE_ACTIONS


def test_inventory_has_forty_fields_per_team_and_five_relevant():
    data = inventory()
    assert len(data["teams"]) >= 6
    relevant = inventory_labels()["relevant_fields"]
    assert len(relevant) == 5
    for team in data["teams"]:
        assert len(team) == 40
        assert set(relevant) <= set(team)


def test_inventory_answer_is_computable_from_the_relevant_fields_alone():
    """Recortar a 5 campos no puede cambiar la respuesta: es la condición de 5.1-S3."""
    labels = inventory_labels()
    teams = inventory()["teams"]
    unassigned = {t["team_id"]: t["laptops_total"] - t["laptops_assigned"] for t in teams}
    best = max(unassigned, key=unassigned.get)
    assert labels["expected"]["team_with_most_unassigned_laptops"] == best
    assert sorted(unassigned.values())[-1] > sorted(unassigned.values())[-2], "sin empate"


def test_inventory_noise_is_bulky():
    """Los 35 campos que sobran pesan de verdad: si fueran cortos, el recorte apenas se notaría en los tokens."""
    relevant = set(inventory_labels()["relevant_fields"])
    team = inventory()["teams"][0]
    noise = len(json.dumps({k: v for k, v in team.items() if k not in relevant}, ensure_ascii=False))
    signal = len(json.dumps({k: v for k, v in team.items() if k in relevant}, ensure_ascii=False))
    assert noise >= 6 * signal


def test_is_deterministic():
    for name in ("escalamiento_casos.json", "escalamiento_ejemplos.json", "inventario_equipos.json"):
        assert build_all()[name] == build_all()[name]


def test_no_progress_cases_say_the_user_already_tried_what_the_knowledge_base_offers():
    """5.2-K1, tercer disparador: la imposibilidad de avanzar. El caso lo hace evidente sin tono de enfado."""
    labels = case_labels()
    stuck = [c for c in cases() if labels[c["case_id"]]["kind"] == "no_progress"]
    assert len(stuck) >= 2
    kb_titles = " ".join(a["title"].lower() for a in json.loads(build_all()["articulos_kb.json"]))
    for case in stuck:
        text = case["text"].lower()
        assert any(w in text for w in ("ya ", "seguí", "probé")), "el cliente ya intentó lo que ofrece la base"
        assert "followup" not in case
    assert "sincronización" in kb_titles and "batería" in kb_titles, "los dos casos se apoyan en artículos que existen"
