"""Avisos de plazo a la persona responsable."""

from ..api import sla_ticket as plazo


def texto_aviso(ticket_id, prioridad, horas):
    restante = plazo(prioridad, horas)["restante_horas"]
    return f"{ticket_id}: quedan {restante} h"
