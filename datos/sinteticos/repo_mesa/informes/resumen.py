"""Resumen de plazos para el informe semanal."""

from ..api import sla_ticket


def horas_restantes(tickets):
    return {t["ticket_id"]: sla_ticket(t["prioridad"], t["horas"])["restante_horas"] for t in tickets}
