"""Repaso de fallos: lee la tabla de `FALLOS.md`, calcula cuándo vence cada fila y arma la cola de repaso.

PROPÓSITO: leer las filas de `FALLOS.md` (con las columnas «Fecha» y «Repasos» si las tiene), decidir
qué filas ☐ tocan hoy con intervalos crecientes (1, 3, 7 y 14 días) y asociar cada viñeta con el ítem
de `harness/items.py` con el que se repasa.

POR QUÉ EXISTE: hasta ahora nada leía `FALLOS.md`. El repaso espaciado necesita saber qué toca hoy
sin que la persona lo calcule. Se guardan fechas y no un contador para contar cada intervalo desde el
último repaso real.

QUÉ NO HACE: no escribe en `FALLOS.md` (quien anota es la persona o la skill), no migra una tabla
antigua (la lee tal cual, con las columnas que tenga: sin «Fecha» la fila vence ya) y no muestra
enunciados ni respuestas: de eso se encarga `narrador item`.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from harness.items import Item, UnknownItem, item_for

# Días hasta el siguiente repaso tras el fallo (primer valor) y tras cada repaso acertado.
INTERVALS = (1, 3, 7, 14)
DONE_MARK = "☑"
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
RULE_CELL = re.compile(r":?-{3,}:?")


@dataclass(frozen=True)
class Failure:
    vignette: str
    module: str
    date: date | None
    reviews: tuple[date, ...]
    done: bool


@dataclass(frozen=True)
class Entry:
    """Una viñeta pendiente de repaso, con las filas ☐ que la nombran agrupadas."""

    vignette: str
    item: Item
    due: date | None  # None: alguna fila sin fecha (vence ya)
    reviews: int  # menor número de repasos entre sus filas
    rows: int


def _read_date(text: str) -> date | None:
    if not ISO_DATE.fullmatch(text.strip()):
        return None
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_failures(text: str) -> list[Failure]:
    """Las filas de la tabla de fallos. Las columnas se buscan por nombre; las que falten se toman vacías."""
    failures: list[Failure] = []
    columns: dict[str, int] | None = None
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if "Viñeta" in cells:
            columns = {name: position for position, name in enumerate(cells)}
            continue
        if columns is None or all(RULE_CELL.fullmatch(cell) for cell in cells if cell):
            continue

        def cell(name: str) -> str:
            position = columns.get(name)
            return cells[position] if position is not None and position < len(cells) else ""

        reviews = tuple(
            parsed for parsed in (_read_date(value) for value in ISO_DATE.findall(cell("Repasos"))) if parsed
        )
        failures.append(
            Failure(cell("Viñeta"), cell("Módulo"), _read_date(cell("Fecha")), reviews, DONE_MARK in cell("Estado"))
        )
    return failures


def next_due(failure: Failure) -> date | None:
    """El día en que vence la fila: None si no se puede calcular (sin fecha ni repasos)."""
    last = max(failure.reviews) if failure.reviews else failure.date
    if last is None:
        return None
    # Agotados los intervalos, se queda en el último: la fila sigue ☐ hasta que la persona la cierre.
    interval = INTERVALS[min(len(failure.reviews), len(INTERVALS) - 1)]
    return last + timedelta(days=interval)


def is_due(failure: Failure, today: date) -> bool:
    if failure.done:
        return False
    due = next_due(failure)
    return due is None or due <= today


def _entry_item(failure: Failure) -> Item | None:
    try:
        return item_for(failure.vignette, failure.module)
    except UnknownItem:
        return None


def unreadable_rows(failures: list[Failure]) -> int:
    """Filas ☐ cuya viñeta no se reconoce: el repaso las salta, pero se cuentan."""
    return sum(1 for failure in failures if not failure.done and _entry_item(failure) is None)


def review_queue(failures: list[Failure], today: date, include_future: bool = False) -> list[Entry]:
    """Viñetas con filas ☐ que tocan hoy (o todas, con `include_future`), de la más vencida a la menos."""
    groups: dict[str, list[Failure]] = {}
    for failure in failures:
        if not failure.done:
            groups.setdefault(failure.vignette, []).append(failure)

    entries: list[tuple[date, Entry]] = []
    for vignette, rows in groups.items():
        # La fila más urgente (sin fecha primero) decide la fecha y el módulo con el que se busca el ítem.
        ordered = sorted(rows, key=lambda row: (next_due(row) is not None, next_due(row) or date.min))
        item = _entry_item(ordered[0]) or next((found for found in map(_entry_item, ordered) if found), None)
        if item is None:
            continue
        due = next_due(ordered[0])
        if not include_future and due is not None and due > today:
            continue
        entry = Entry(vignette, item, due, min(len(row.reviews) for row in rows), len(rows))
        entries.append((due or date.min, entry))
    # `sorted` es estable: a igual fecha se conserva el orden de aparición en la tabla.
    return [entry for _, entry in sorted(entries, key=lambda pair: pair[0])]
