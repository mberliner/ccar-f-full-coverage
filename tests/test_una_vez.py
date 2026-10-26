"""Test «una vez por viñeta» (roadmap §2 y §11.2).

PROPÓSITO: comprobar que cada viñeta de la guía tiene un único marcador
`INTRODUCE`, en el destino que le asigna `CONCEPTOS.md`, y que los `USA` solo
apuntan a viñetas ya introducidas.

POR QUÉ EXISTE: la regla «una vez» es la medida de cobertura del proyecto. Sin
un test, una viñeta reexplicada en dos módulos o introducida fuera de su sitio
solo se detectaría leyendo todo el repositorio.

QUÉ NO HACE: no valida el contenido de los comentarios ni lee la guía oficial;
trabaja solo con identificadores y rutas. No llama al modelo.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Recuento (K, S) por Task Statement en la Exam Guide v1.0. Es una segunda fuente,
# independiente de CONCEPTOS.md, para que un error al editar la tabla no pase inadvertido.
EXPECTED_COUNTS = {
    "1.1": (3, 3), "1.2": (4, 4), "1.3": (4, 4), "1.4": (3, 3), "1.5": (3, 3), "1.6": (3, 3), "1.7": (4, 4),
    "2.1": (4, 4), "2.2": (4, 4), "2.3": (4, 5), "2.4": (4, 5), "2.5": (4, 5),
    "3.1": (4, 4), "3.2": (4, 5), "3.3": (3, 3), "3.4": (4, 4), "3.5": (4, 5), "3.6": (4, 5),
    "4.1": (3, 3), "4.2": (4, 5), "4.3": (4, 6), "4.4": (4, 4), "4.5": (4, 4), "4.6": (3, 3),
    "5.1": (4, 6), "5.2": (4, 5), "5.3": (4, 4), "5.4": (4, 5), "5.5": (4, 4), "5.6": (4, 5),
}
TOTAL = 240

ROW_RE = re.compile(r"^\| (TS \d\.\d-[KS]\d+) \| (\S+) \| ([☐☑]) \|$")
COUNTER_RE = re.compile(r"\*\*Introducidas: (\d+)/240\*\*")
# El marcador admite varias viñetas en una línea: «# INTRODUCE: TS 1.1-K1, TS 1.1-K2».
# Vale igual dentro de «#», «<!-- -->» o un comentario YAML, porque solo se busca el texto.
MARKER_RE = re.compile(r"\b(INTRODUCE|USA):\s*(.*)")
ID_RE = re.compile(r"TS \d\.\d-[KS]\d+")

# Se excluyen los registros (contienen todos los identificadores), los propios tests y el
# estado personal (`estado/`, ignorado por git) con sus plantillas.
SKIP_DIRS = {".git", ".venv", "tests", "__pycache__", ".pytest_cache", "estado", "plantillas"}
SKIP_FILES = {"CONCEPTOS.md", "NOTAS.md"}


def parse_conceptos(path: Path) -> tuple[dict[str, tuple[str, str]], int | None]:
    """Devuelve {viñeta: (destino, estado)} y el contador «Introducidas»."""
    text = path.read_text(encoding="utf-8")
    rows: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if m:
            assert m.group(1) not in rows, f"fila duplicada en CONCEPTOS.md: {m.group(1)}"
            rows[m.group(1)] = (m.group(2), m.group(3))
    counter = COUNTER_RE.search(text)
    return rows, int(counter.group(1)) if counter else None


def scan_markers(root: Path) -> dict[str, list[tuple[str, str]]]:
    """Devuelve {"INTRODUCE"|"USA": [(viñeta, ruta relativa), ...]} recorriendo el repositorio."""
    found: dict[str, list[tuple[str, str]]] = {"INTRODUCE": [], "USA": []}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or SKIP_DIRS & set(rel.parts[:-1]) or rel.name in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binarios y archivos no legibles: no pueden llevar marcadores
        for line in text.splitlines():
            for kind, rest in MARKER_RE.findall(line):
                found[kind] += [(bullet, rel.as_posix()) for bullet in ID_RE.findall(rest)]
    return found


def location_ok(dest: str, rel: str) -> bool:
    """¿Está el marcador en el destino que asigna CONCEPTOS.md?"""
    if dest == "d3":
        # Sección D3: README propio o archivos de la capa meta (roadmap §4.1 y §4.2),
        # incluidos los CLAUDE.md de cada app (jerarquía, 3.1).
        return (
            rel.startswith(("d3_claude_code/", ".claude/", "docs/"))
            or rel == "CLAUDE.md"
            or re.fullmatch(r"app\d_[^/]+/CLAUDE\.md", rel) is not None
        )
    app, module = dest.split("/", 1)
    # El marcador va en el propio módulo; los servers/ compartidos solo llevan USA.
    return rel.startswith(f"{app}_") and module in rel


def check(root: Path, rows: dict[str, tuple[str, str]]) -> list[str]:
    """Lista los incumplimientos de la regla «una vez» (vacía si todo cuadra)."""
    errors = []
    markers = scan_markers(root)
    introduced: dict[str, list[str]] = {}
    for bullet, rel in markers["INTRODUCE"]:
        introduced.setdefault(bullet, []).append(rel)

    for bullet, files in introduced.items():
        if bullet not in rows:
            errors.append(f"{bullet} no existe en CONCEPTOS.md ({files[0]})")
            continue
        if len(files) > 1:
            errors.append(f"{bullet} introducida {len(files)} veces: {files}")
        dest, _ = rows[bullet]
        errors += [f"{bullet} introducida en {rel}, su destino es {dest}" for rel in files if not location_ok(dest, rel)]

    for bullet, (dest, state) in rows.items():
        if state == "☑" and bullet not in introduced:
            errors.append(f"{bullet} marcada ☑ sin marcador INTRODUCE en {dest}")
        if state == "☐" and bullet in introduced:
            errors.append(f"{bullet} tiene marcador pero sigue ☐ en CONCEPTOS.md")

    for bullet, rel in markers["USA"]:
        if rows.get(bullet, ("", "☐"))[1] != "☑":
            errors.append(f"USA de {bullet} en {rel}, pero la viñeta no está introducida")
    return errors


# --- Repositorio real -------------------------------------------------------

ROWS, COUNTER = parse_conceptos(ROOT / "CONCEPTOS.md")


def test_conceptos_matches_guide_counts():
    assert len(ROWS) == TOTAL
    for ts, (k, s) in EXPECTED_COUNTS.items():
        expected = {f"TS {ts}-K{n}" for n in range(1, k + 1)} | {f"TS {ts}-S{n}" for n in range(1, s + 1)}
        assert {b for b in ROWS if b.startswith(f"TS {ts}-")} == expected, ts
    assert sum(k + s for k, s in EXPECTED_COUNTS.values()) == TOTAL


def test_conceptos_destinations_are_valid():
    bad = [b for b, (dest, _) in ROWS.items() if dest != "d3" and not re.fullmatch(r"app[123]/\d\d_[a-z_]+", dest)]
    assert not bad


def test_counter_matches_checked_rows():
    assert COUNTER == sum(1 for _, state in ROWS.values() if state == "☑")


def test_once_per_bullet():
    assert check(ROOT, ROWS) == []


@pytest.mark.xfail(strict=True, reason="cobertura completa hasta la entrega 3 (roadmap §10)")
def test_full_coverage():
    assert all(state == "☑" for _, state in ROWS.values())


# --- Autotests del escáner sobre un repositorio de prueba ---------------------

FAKE_ROWS = {
    "TS 1.1-K1": ("app1/01_bucle_manual", "☑"),
    "TS 3.1-K1": ("d3", "☑"),
    "TS 1.1-K2": ("app1/01_bucle_manual", "☐"),
}


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scanner_accepts_valid_layout(tmp_path):
    write(tmp_path, "app1_agente_unico/01_bucle_manual.py", "# INTRODUCE: TS 1.1-K1\n")
    write(tmp_path, ".claude/rules/tests.md", "<!-- INTRODUCE: TS 3.1-K1 -->\n")
    write(tmp_path, "app2_agente_con_control/01_x.py", "# USA: TS 1.1-K1, TS 3.1-K1\n")
    assert check(tmp_path, FAKE_ROWS) == []


def test_scanner_detects_duplicate(tmp_path):
    write(tmp_path, "app1_agente_unico/01_bucle_manual.py", "# INTRODUCE: TS 1.1-K1\n# INTRODUCE: TS 3.1-K1\n")
    write(tmp_path, "app1_agente_unico/01_bucle_manual_extra.py", "# INTRODUCE: TS 1.1-K1\n")
    errors = check(tmp_path, FAKE_ROWS)
    assert any("introducida 2 veces" in e for e in errors)
    assert any("TS 3.1-K1 introducida en app1_agente_unico" in e for e in errors)


def test_scanner_detects_wrong_location_and_state(tmp_path):
    write(tmp_path, "app1_agente_unico/servers/helpdesk.py", "# INTRODUCE: TS 1.1-K1\n")
    write(tmp_path, "CLAUDE.md", "<!-- INTRODUCE: TS 3.1-K1, TS 1.1-K2 -->\n")
    errors = check(tmp_path, FAKE_ROWS)
    assert any("TS 1.1-K1 introducida en app1_agente_unico/servers" in e for e in errors)
    assert any("TS 1.1-K2 tiene marcador pero sigue ☐" in e for e in errors)


def test_scanner_detects_orphan_usa_and_missing_marker(tmp_path):
    write(tmp_path, "harness/options.py", "# USA: TS 1.1-K2\n")
    errors = check(tmp_path, FAKE_ROWS)
    assert any("USA de TS 1.1-K2" in e for e in errors)
    assert any("TS 1.1-K1 marcada ☑ sin marcador" in e for e in errors)
