"""Tests de `harness/hojas_repaso.py`: hojas de repaso por dominio generadas de las cabeceras, con `--check`. Sin modelo.

PROPÓSITO: fijar el contrato de las hojas `docs/repaso/D1.md`…`D5.md` (plan de mejoras, fase 3). Cada
hoja reúne, para un dominio, lo que las cabeceras ya dicen: qué viñetas introduce cada módulo (o cada
archivo de D3), qué dice la guía de ellas y cuál es la trampa del examen.

POR QUÉ EXISTE: para repasar un dominio había que abrir cada script y leer su cabecera. La hoja lo
junta sin duplicar nada: se genera, y `--check` falla si deja de coincidir con las cabeceras, igual
que `datos/generar_sinteticos.py --check` con los datos.

QUÉ NO HACE: no comprueba que las cabeceras digan lo que dice la guía (eso es de la revisión contra la
guía) ni el formato de las cabeceras. La unidad es el bullet de «QUÉ DICE LA GUÍA», que suele citar
varias viñetas: no hay una fila por viñeta, porque las cabeceras no se pueden cortar así.
"""

import ast
import re
from pathlib import Path

import pytest

from tests.contrato import require

require("3.4")  # se salta entero mientras falte `harness/hojas_repaso.py`

from harness.hojas_repaso import build_sheets, main  # noqa: E402
from tests.test_comprobaciones_cortas import cited  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ["D1", "D2", "D3", "D4", "D5"]
CONCEPT_ROW = re.compile(r"^\| (TS \d\.\d-[KS]\d) \| (\S+) \| ☑ \|", re.MULTILINE)
DOMAIN_ROW = re.compile(r"^\| (D\d) \| ([^|]+) \|", re.MULTILINE)
# Líneas que pone el generador y no vienen de una cabecera: encabezados, avisos, rótulos en negrita y la lista de viñetas.
OWN_LINE = re.compile(r"(#|>|Viñetas)|\*\*[^*]+\*\*$")
MIN_COPIED_LINE = 40


def concepts() -> dict[str, str]:
    """{viñeta: origen}, con el destino de `CONCEPTOS.md` reducido a `appN/NN` o `d3`."""
    text = (ROOT / "CONCEPTOS.md").read_text(encoding="utf-8")
    return {vignette: destination.split("_", 1)[0] for vignette, destination in CONCEPT_ROW.findall(text)}


def squash(text: str) -> str:
    """Sin prefijos de comentario ni saltos de línea: la hoja puede unir las líneas de un párrafo."""
    lines = [re.sub(r"^\s*(#|<!--|-->|-)\s?", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def source_corpus() -> str:
    """Todo el texto del que puede salir una hoja: cabeceras de los módulos y archivos con marcador de D3."""
    texts = [ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or "" for path in sorted(ROOT.glob("app*/[0-9][0-9]_*.py"))]
    files = [ROOT / "CLAUDE.md", ROOT / "d3_claude_code" / "README.md", *sorted((ROOT / "docs").glob("estandares-*.md"))]
    files += [path for path in sorted((ROOT / ".claude").rglob("*")) if path.suffix in {".md", ".json"}]
    texts += [path.read_text(encoding="utf-8") for path in files]
    return squash("\n".join(texts))


@pytest.fixture(scope="module")
def sheets() -> dict[str, str]:
    return build_sheets()


# --- Contenido -------------------------------------------------------------------

def test_there_is_one_sheet_per_domain(sheets):
    assert sorted(sheets) == DOMAINS


def test_each_sheet_is_titled_with_its_domain_and_says_it_is_generated(sheets):
    names = dict(DOMAIN_ROW.findall((ROOT / "CONCEPTOS.md").read_text(encoding="utf-8")))
    for domain, text in sheets.items():
        first = text.splitlines()[0]
        assert first.startswith("# ") and domain in first and names[domain].strip() in first
        head = "\n".join(text.splitlines()[:12])
        # Quien la abre tiene que saber que no se edita y cómo se regenera.
        assert "harness.hojas_repaso" in head and "no se edita" in head.lower()
        # La cabecera de un script solo sale con la respuesta del módulo: la hoja es para después.
        assert "después" in head.lower()


@pytest.mark.parametrize("vignette, source", sorted(concepts().items()))
def test_every_vignette_is_in_the_sheet_of_its_domain(sheets, vignette, source):
    domain = f"D{vignette[3]}"
    assert vignette in cited(sheets[domain]), f"{vignette} ({source}) no aparece en {domain}"


def test_a_sheet_has_a_section_for_each_source_of_its_domain_and_no_other(sheets):
    by_domain: dict[str, set[str]] = {domain: set() for domain in DOMAINS}
    for vignette, source in concepts().items():
        by_domain[f"D{vignette[3]}"].add(source)
    for domain, text in sheets.items():
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        modules = {match for line in headings for match in re.findall(r"app\d/\d{2}", line)}
        assert modules == {source for source in by_domain[domain] if source != "d3"}, domain


def test_the_d3_sheet_points_to_the_files_that_carry_each_marker(sheets):
    text = sheets["D3"]
    for path in ("CLAUDE.md", ".claude/rules/tests.md", ".claude/skills/verificar-concepto/SKILL.md", "d3_claude_code/README.md"):
        assert f"`{path}`" in text, path
    # TS 3.6 (Claude Code en CI) es de D3 y la introduce un módulo de app3.
    assert "app3/11" in text


def test_each_section_brings_what_the_guide_says_and_the_trap(sheets):
    for domain, text in sheets.items():
        sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
        assert sections, domain
        for section in sections:
            title = section.splitlines()[0]
            assert "**Qué dice la guía**" in section, f"{domain} · {title}"
            assert "**Trampa del examen**" in section, f"{domain} · {title}"
            assert section.index("**Qué dice la guía**") < section.index("**Trampa del examen**")


def test_a_sheet_only_keeps_the_bullets_of_its_domain(sheets):
    # `app1/01` introduce seis viñetas de TS 1.1 y una de D5 (TS 5.1-K4). En D5 solo va el bullet que la cita.
    section = next(part for part in re.split(r"^## ", sheets["D5"], flags=re.MULTILINE) if "app1/01" in part.splitlines()[0])
    assert "La API no guarda estado" in section
    assert "ejecuta las tools pedidas" not in section, "ese bullet es de TS 1.1"
    assert "TS 5.1-K4" in cited(section) and "TS 1.1-K1" not in cited(section)


def test_known_header_text_reaches_its_sheet(sheets):
    assert "Solo `stop_reason` dice si" in squash(sheets["D1"])  # trampa de `app1/01`
    assert "un glob por tipo de archivo" in squash(sheets["D3"]) or "glob por tipo de archivo" in squash(sheets["D3"])


def test_sheets_copy_and_never_author(sheets):
    """Todo lo que no es estructura está, tal cual, en una cabecera: la hoja no añade contenido propio."""
    corpus = source_corpus()
    for domain, text in sheets.items():
        for line in text.splitlines():
            stripped = line.strip()
            if len(stripped) < MIN_COPIED_LINE or OWN_LINE.match(stripped):
                continue
            assert squash(stripped) in corpus, f"{domain}: línea que no sale de ninguna cabecera: {stripped[:80]}"


def test_sheets_are_deterministic():
    assert build_sheets() == build_sheets()


# --- Generar y comprobar ---------------------------------------------------------

def test_main_writes_the_five_sheets(tmp_path, sheets):
    assert main([], target=tmp_path) == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == [f"{domain}.md" for domain in DOMAINS]
    for domain in DOMAINS:
        assert (tmp_path / f"{domain}.md").read_text(encoding="utf-8") == sheets[domain]


def test_check_passes_on_fresh_sheets_and_writes_nothing(tmp_path):
    main([], target=tmp_path)
    before = {path.name: path.stat().st_mtime_ns for path in tmp_path.iterdir()}
    assert main(["--check"], target=tmp_path) == 0
    assert {path.name: path.stat().st_mtime_ns for path in tmp_path.iterdir()} == before


def test_check_fails_on_an_edited_sheet_and_does_not_repair_it(tmp_path, capsys):
    main([], target=tmp_path)
    edited = tmp_path / "D2.md"
    edited.write_text(edited.read_text(encoding="utf-8") + "\nuna línea a mano\n", encoding="utf-8")
    assert main(["--check"], target=tmp_path) == 1
    assert "D2.md" in capsys.readouterr().out
    assert "una línea a mano" in edited.read_text(encoding="utf-8")


def test_check_fails_when_a_sheet_is_missing(tmp_path):
    main([], target=tmp_path)
    (tmp_path / "D4.md").unlink()
    assert main(["--check"], target=tmp_path) == 1
    assert main(["--check"], target=tmp_path / "no-existe") == 1


def test_the_versioned_sheets_are_up_to_date():
    """Las hojas de `docs/repaso/` son las que salen hoy de las cabeceras."""
    assert main(["--check"]) == 0
