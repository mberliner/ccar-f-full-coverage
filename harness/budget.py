"""Tope de coste para los módulos de la Messages API (roadmap §3, regla 7).

PROPÓSITO: sumar el coste de cada respuesta a partir de su `usage` y del
precio del modelo, y cortar con `BudgetExceeded` en cuanto se supera el tope.

POR QUÉ EXISTE: `max_budget_usd` es una opción del Agent SDK; un bucle escrito a
mano con `anthropic.messages.create` (app1/01) no la tiene. Sin este tope, la
regla de coste quedaría en prosa justo en el módulo que enseña a no depender de
la prosa.

QUÉ NO HACE: no estima antes de llamar (corta después de la respuesta que lo
supera, igual que el SDK) ni conoce precios de otros modelos: uno sin precio
corta con error en vez de suponer un coste cero. Precios de la documentación
de la API a 2026-10-06; si cambian, se actualiza esta tabla.
"""

from dataclasses import dataclass
from typing import Any

# USD por millón de tokens: (entrada, salida).
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}
# Haiku 5.5 tiene un tramo más caro para peticiones de más de 100K tokens de entrada.
LONG_PROMPT = {"claude-haiku-5-5": (100_000, (0.50, 2.50))}
CACHE_WRITE_FACTOR = 1.25
CACHE_READ_FACTOR = 0.10


class BudgetExceeded(RuntimeError):
    """El coste acumulado superó el tope de la ejecución."""


def cost_of(model: str, usage: Any) -> float:
    """Coste en USD de una respuesta, a partir de su `usage`."""
    price_in, price_out = PRICES[model]
    fresh = usage.input_tokens or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", None) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", None) or 0
    if model in LONG_PROMPT:
        limit, long_prices = LONG_PROMPT[model]
        # El tramo depende de toda la entrada de la petición, cacheada o no.
        if fresh + cache_write + cache_read > limit:
            price_in, price_out = long_prices
    input_cost = (fresh + cache_write * CACHE_WRITE_FACTOR + cache_read * CACHE_READ_FACTOR) * price_in
    return (input_cost + (usage.output_tokens or 0) * price_out) / 1_000_000


@dataclass
class CostGuard:
    model: str
    max_usd: float
    spent: float = 0.0

    def __post_init__(self) -> None:
        if not self.max_usd or self.max_usd <= 0:
            raise ValueError("max_usd debe ser un importe positivo (roadmap §3, regla 7)")
        PRICES[self.model]  # un modelo sin precio corta aquí, antes de la primera llamada

    def add(self, usage: Any) -> float:
        """Suma una respuesta y corta si el acumulado supera el tope."""
        self.spent += cost_of(self.model, usage)
        if self.spent > self.max_usd:
            raise BudgetExceeded(f"coste acumulado ${self.spent:.4f} supera el tope ${self.max_usd}")
        return self.spent
