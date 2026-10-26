from repo_mesa.tickets.escalado import debe_escalar


def test_escala_cuando_vence():
    assert debe_escalar("urgente", 5)
    assert not debe_escalar("urgente", 1)
