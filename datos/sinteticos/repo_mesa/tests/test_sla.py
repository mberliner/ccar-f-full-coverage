import pytest

from repo_mesa.core.sla import calcular_sla


def test_dentro_de_plazo():
    assert calcular_sla("alta", 3)["restante_horas"] == 5


def test_vencido():
    with pytest.raises(ValueError):
        calcular_sla("alta", 9)
