"""Cálculo de plazos de SLA."""

# Horas máximas de resolución por prioridad.
LIMITE_HORAS = {"urgente": 4, "alta": 8, "normal": 24, "baja": 72}


def calcular_sla(prioridad, horas_abiertas):
    limite = LIMITE_HORAS[prioridad]
    if horas_abiertas > limite:
        raise ValueError(f"SLA vencido para prioridad {prioridad}: {horas_abiertas} h de {limite} h")
    return {"limite_horas": limite, "restante_horas": limite - horas_abiertas}
