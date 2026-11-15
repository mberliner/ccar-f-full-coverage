"""Pequeñas medidas comunes: texto de una tasa, aciertos y dólares.

PROPÓSITO: `rate_text` formatea una tasa (aciertos, total), `accuracy` cuenta aciertos de pares
(elegido, esperado) y `fmt_usd` escribe un importe con cuatro decimales.

POR QUÉ EXISTE: `rate_text` y `accuracy` estaban copiadas en varios módulos con formatos distintos.

QUÉ NO HACE: no calcula tasas con modelo ni unifica `app3/10.accuracy`, que es otra función (celdas).
"""

import operator
from typing import Any, Callable, Iterable


def rate_text(rate: tuple[int, int], *, percent: bool = True) -> str:
    """`3/4 (75 %)` (o `3/4` con `percent=False`); `sin datos` si el total es cero."""
    hits, total = rate
    if not total:
        return "sin datos"
    return f"{hits}/{total} ({round(100 * hits / total)} %)" if percent else f"{hits}/{total}"


def accuracy(results: Iterable[tuple[Any, Any]], *, match: Callable[[Any, Any], bool] = operator.eq) -> tuple[int, int]:
    """(aciertos, total) de pares (elegido, esperado); una llamada ausente (`None`) cuenta como fallo."""
    pairs = list(results)
    return sum(1 for chosen, expected in pairs if chosen is not None and match(chosen, expected)), len(pairs)


def fmt_usd(value: float) -> str:
    """Importe en dólares con cuatro decimales: `$0.0123`."""
    return f"${value:.4f}"
