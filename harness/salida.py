"""Salida estándar para quien estudia: `[mecanismo]`, `[esperado]`, `[clave]`, `[medida]` y `[respuesta completa]`.

PROPÓSITO: dar a cada módulo las mismas líneas, en el mismo orden, para que quien estudia sepa cuál es
la medida que contesta la predicción (`[clave]`) y cuáles son detalle (`[medida]`). También fija el
nombre de la variante correcta (`correcta`) y recorta la respuesta final salvo con `--verbose`.

POR QUÉ EXISTE: cada módulo imprimía su resultado a su manera y había que buscar cuál de las líneas era
la medida principal. La variante correcta se llamaba `hooks`, `puerta`, `case facts`…

QUÉ NO HACE: no mide nada ni llama al modelo; solo da formato a texto ya calculado. No imprime: devuelve
cadenas, y el módulo decide cuándo escribirlas.
"""

import re
from collections.abc import Iterable

# Nombre único de la variante correcta (la que se ejecuta sin `--anti`).
CORRECT_VARIANT = "correcta"
# Caracteres de la respuesta final que se muestran sin `--verbose`.
RESPONSE_LIMIT = 600

_VIGNETTE = re.compile(r"^TS \d+\.\d+-")


def variant_label(anti: str | None) -> str:
    """Nombre de la variante: la de `--anti`, o `correcta` si no hay (o viene vacía)."""
    return anti or CORRECT_VARIANT


def mechanism_line(vignette: str, sentence: str) -> str:
    """`[mecanismo] TS x.y-Kn · frase`; la viñeta debe empezar por `TS x.y-` y la frase ser de una línea."""
    if not _VIGNETTE.match(vignette):
        raise ValueError(f"viñeta no válida (se espera «TS x.y-Kn»): {vignette!r}")
    if not sentence.strip() or "\n" in sentence:
        raise ValueError("la frase del mecanismo debe tener una sola línea y no estar vacía")
    return f"[mecanismo] {vignette} · {sentence}"


def expected_line(text: str) -> str:
    return f"[esperado] {text}"


def key_line(text: str) -> str:
    """La medida principal; no puede estar vacía."""
    if not text.strip():
        raise ValueError("la línea [clave] no puede estar vacía")
    return f"[clave] {text}"


def measure_line(text: str) -> str:
    return f"[medida] {text}"


def full_response(text: str | None, *, verbose: bool) -> str:
    """`[respuesta completa] …`, recortada a `RESPONSE_LIMIT` caracteres salvo con `verbose`."""
    if not text:
        return "[respuesta completa] (sin respuesta)"
    if verbose or len(text) <= RESPONSE_LIMIT:
        return f"[respuesta completa] {text}"
    rest = len(text) - RESPONSE_LIMIT
    return f"[respuesta completa] {text[:RESPONSE_LIMIT]}… ({rest} caracteres más; --verbose para verla entera)"


def render(
    *,
    mechanism: tuple[str, str],
    expected: str,
    key: str,
    measures: Iterable[str] = (),
    response: str | None = None,
    verbose: bool = False,
) -> str:
    """Las líneas en el orden estándar. `response=None` omite `[respuesta completa]`."""
    lines = [mechanism_line(*mechanism), expected_line(expected), key_line(key)]
    lines += [measure_line(m) for m in measures]
    if response is not None:
        lines.append(full_response(response, verbose=verbose))
    return "\n".join(lines)
