"""Tests de los carriles de contenido: examen (guía v1.0), producto observado y producción. Sin modelo.

PROPÓSITO: la documentación distingue lo que dice la guía (sin marca) de lo que no es materia del examen. Lo no
evaluable lleva uno de dos rótulos exactos, `Producto observado (no evaluable)` (lo que hace hoy Claude Code, el
SDK o la API y la guía no describe) o `EN PRODUCCIÓN (no evaluable)` (una práctica o un mecanismo adicional que la
guía no nombra). El test impide las grafías sueltas, para que el lector reconozca el carril de un vistazo.

POR QUÉ EXISTE: auditoría D-03. Había seis formas de escribir «no evaluable» y un solo rótulo para dos cosas
distintas, así que el comportamiento del producto y el diseño de producción se confundían con lo evaluable.

QUÉ NO HACE: no decide en qué carril va cada frase (eso lo hace la revisión), no revisa los docstrings de los
módulos ni `docs/hallazgos.md`, y no impide mencionar «no evaluable» en prosa que no sea un rótulo.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION = "EN PRODUCCIÓN (no evaluable)"
OBSERVED = "Producto observado (no evaluable)"
CANONICAL = {PRODUCTION, OBSERVED}
# Un rótulo: «en producción» / «producto observado» / «nota de producto» seguido de «no evaluable» (con o sin paréntesis).
MARKER = re.compile(r"(?i)\b(?:en producción|producto observado|nota de producto)\b[^\n.;:*]{0,6}no evaluable\)?")
FILES = ["README.md", "d3_claude_code/README.md", "app1_agente_unico/README.md", "app2_agente_con_control/README.md",
         "app3_sistema_multiagente/README.md", "plantillas/modulo/README.md"]


def stray_markers(text: str) -> list[str]:
    """Rótulos de «no evaluable» que no son uno de los dos exactos."""
    return [found for found in MARKER.findall(text) if found not in CANONICAL]


def test_the_two_canonical_labels_are_accepted():
    assert stray_markers(f"**{PRODUCTION}:** x. Otra nota: {OBSERVED}.") == []


def test_every_other_spelling_is_flagged():
    for text in ("EN PRODUCCIÓN, no evaluable", "En producción (no evaluable)", "(EN PRODUCCIÓN, no evaluable)",
                 "nota de producto (no evaluable)", "producto observado, no evaluable"):
        assert stray_markers(text), text


def test_prose_that_is_not_a_label_is_left_alone():
    assert stray_markers("Esta práctica no es evaluable; la guía no la nombra.") == []
    assert stray_markers("comprobación operativa, no evaluable") == []


def test_no_documentation_file_uses_a_stray_label():
    offenders = {}
    for path in FILES:
        found = stray_markers((ROOT / path).read_text(encoding="utf-8"))
        if found:
            offenders[path] = found
    assert not offenders, f"rótulos «no evaluable» sin la forma exacta ({PRODUCTION!r} o {OBSERVED!r}): {offenders}"


def test_the_standard_defines_the_lanes_with_the_exact_labels():
    standard = (ROOT / "docs" / "estandares-codigo.md").read_text(encoding="utf-8")
    assert "Carriles de contenido" in standard
    assert PRODUCTION in standard and OBSERVED in standard
