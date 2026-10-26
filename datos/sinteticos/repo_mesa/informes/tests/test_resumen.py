from repo_mesa.informes.resumen import horas_restantes


def test_horas_restantes():
    assert horas_restantes([{"ticket_id": "T1", "prioridad": "normal", "horas": 4}]) == {"T1": 20}
