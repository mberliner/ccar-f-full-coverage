"""Argumentos comunes de los módulos de app (roadmap §2 y §13).

PROPÓSITO: construir el `argparse` de cada módulo con las tres opciones que
comparten todos: `--anti [variante]` (par anti-patrón / correcto), `--repeat N`
(medir una tasa en varias ejecuciones) y `--budget` (bajar el tope de coste
para una prueba barata), y calcular el presupuesto efectivo.

POR QUÉ EXISTE: repetir el mismo `argparse` en 8 módulos invita a que cada uno
lo haga a su manera. El módulo puede añadir sus propias opciones al parser
devuelto (`--parte` en app3/02).

QUÉ NO HACE: no tiene `--model`, para que el `.env` sea siempre la fuente que
manda (ver `harness/config.py`), y `--budget` nunca sube el tope resuelto: una
prueba puntual no puede gastar más de lo que fija el repositorio. No esconde
ninguna opción del agente: eso sigue visible en el módulo.
"""

import argparse

from harness.config import describe, resolve_budget


def positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("debe ser un importe positivo")
    return value


def positive_int(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("debe ser un entero positivo")
    return value


def build_parser(description: str, *, anti_variants: list[str]) -> argparse.ArgumentParser:
    """Parser con `--budget`, `--repeat` y, si la viñeta describe un error, `--anti`."""
    parser = argparse.ArgumentParser(description=description)
    if anti_variants:
        # `--anti` sin valor elige la primera variante: la que el módulo
        # considera el anti-patrón principal.
        parser.add_argument(
            "--anti",
            nargs="?",
            const=anti_variants[0],
            choices=anti_variants,
            help=f"ejecuta el anti-patrón ({', '.join(anti_variants)}); sin valor: {anti_variants[0]}",
        )
    else:
        parser.set_defaults(anti=None)
    parser.add_argument("--repeat", type=positive_int, default=1, help="número de ejecuciones (por defecto 1)")
    parser.add_argument("--budget", type=positive_float, help="baja el tope en USD; nunca lo sube")
    return parser


def effective_budget(requested: float | None, resolved: float, origin: str) -> tuple[float, str, str | None]:
    """Devuelve (tope, origen, aviso). El tope es `min(--budget, resuelto)`."""
    if requested is None or requested == resolved:
        return resolved, origin, None
    if requested < resolved:
        return requested, "--budget", None
    return resolved, origin, f"--budget {requested} no sube el tope: se usa {resolved} ({origin})"


def report_budget(requested: float | None, kind: str) -> float:
    """Resuelve el presupuesto de `kind`, imprime `[presupuesto]` (y el aviso) y devuelve el tope efectivo."""
    resolved, origin = resolve_budget(kind)
    value, final_origin, warning = effective_budget(requested, resolved, origin)
    if warning:
        print(f"[aviso] {warning}")
    print(describe("presupuesto", valor=value, origen=final_origin))
    return value
