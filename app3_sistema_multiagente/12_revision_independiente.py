"""Revisión independiente: quién revisa un cambio importa tanto como cómo lo revisa.

CONCEPTO [TS 4.6-K1, K2, K3 · S1, S2, S3 · TS 1.6-K2, S2 · TS 3.6-K4]: revisar un cambio con una segunda instancia sin el
contexto de quien lo generó, en pasadas encadenadas (una por archivo y otra de integración entre archivos) y con una
pasada de verificación que da la confianza de cada hallazgo, frente a revisarlo en la misma sesión que lo generó.

QUÉ DICE LA GUÍA:
- La autorrevisión tiene un límite: el modelo conserva el contexto de razonamiento con el que generó el código y, en la
  misma sesión, es menos probable que ponga en duda sus propias decisiones (4.6-K1). Es el motivo de aislar el contexto
  de la sesión: la que generó el código revisa sus cambios peor que una instancia de revisión independiente (3.6-K4).
- Una instancia independiente, sin ese razonamiento previo, detecta mejor los problemas sutiles que pedirle a la misma
  sesión que se revise o darle más razonamiento extendido (4.6-K2). En la práctica, una segunda instancia de Claude
  revisa el código generado sin el contexto del generador (4.6-S1).
- Una revisión grande de varios archivos se parte en pasadas: una por archivo para lo local y otra aparte de
  integración para el flujo de datos entre archivos, lo que evita diluir la atención y obtener hallazgos contradictorios
  (4.6-K3, S2).
- Es un encadenamiento de prompts fijo: analizar cada archivo y después hacer una pasada de integración entre archivos
  (1.6-K2), el patrón adecuado para una revisión predecible de varios aspectos, frente a la descomposición dinámica de
  una investigación abierta (1.6-S2).
- Una pasada de verificación, en la que el modelo informa de su confianza junto a cada hallazgo, permite enrutar la
  revisión de forma calibrada (4.6-S3).

POR QUÉ IMPORTA (inferencia propia): quien revisa en la misma sesión parte de haber decidido ya que el código es
razonable. Una instancia nueva solo tiene el diff y lo que lea, así que no hereda esas decisiones; y un fallo entre
archivos solo lo ve quien mira a la vez al que cambia y al que llama.

ANTI-PATRÓN / TRAMPA DEL EXAMEN:
- Hechos de la guía:
  - Revisar en la misma sesión que generó el código (`--anti autorrevision`).
  - Creer que una instrucción de autorrevisión lo arregla (`--anti autorrevision_explicita`) o que lo arregla más
    razonamiento extendido (no se ejecuta aquí): la guía pone a los dos por debajo de la instancia independiente.
  - Revisar muchos archivos en una sola pasada larga, que diluye la atención.
- Lo medido aquí no respalda la viñeta central (cifras en el README y en `docs/hallazgos.md`):
  - La autorrevisión con `--resume --fork-session` no encontró menos que la instancia nueva (2 ejecuciones) y costó cerca
    del doble. En el examen manda la guía (4.6-K1, K2; 3.6-K4); la lección queda como conceptual.
  - `autorrevision_explicita` está implementada y probada sin modelo, pero no se midió: no hay cifra.
  - Los fallos entre archivos salieron por la pasada de integración en unas ejecuciones y por la de archivo en otras:
    ninguna pasada sola los garantizó.
- Inferencias propias:
  - El «razonamiento de generación» de la sesión generadora es el de copiar un cambio que se le da y explicar sus
    decisiones, no el de diseñarlo. Es una adaptación: no reproduce del todo la situación de la guía, y puede ser una de
    las razones de que la autorrevisión no se viera peor.
  - Una sesión bifurcada de la generadora no hace pasadas locales de verdad: recuerda todos los archivos que escribió.
    Solo una instancia nueva sin tools mira un archivo sin ver el resto.
  - La confianza de cada hallazgo la da la pasada de verificación y se mide contra lo sembrado con la calibración de
    `app3/10`. Con todos los hallazgos reales, no hay nada que separar.
- Producto observado (no evaluable): el `total_cost_usd` de una sesión reanudada es acumulado y `--max-budget-usd` no
  cuenta ese histórico, así que el tope de la rama lo lleva `headless.Ledger` (sonda C1 en `docs/hallazgos.md`). Una
  pasada con poco margen puede cortar sin resultado, y sus hallazgos quedan sin confianza.

Pregunta tipo examen: ver `app3_sistema_multiagente/README.md`, módulo 12.

INTRODUCE: TS 4.6-K1, TS 4.6-K2, TS 4.6-K3, TS 4.6-S1, TS 4.6-S2, TS 4.6-S3, TS 1.6-K2, TS 1.6-S2, TS 3.6-K4

Uso: `uv run python app3_sistema_multiagente/12_revision_independiente.py [--parte plan|revision] [--anti autorrevision|autorrevision_explicita] [--repeat N]`
"""

import copy
import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Los módulos se ejecutan como script: la raíz del repositorio va al path para importar `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import credentials, headless  # noqa: E402
from harness.cli import build_parser, report_budget  # noqa: E402
from harness.config import report_model  # noqa: E402
from harness.data import load  # noqa: E402


def load_sibling(filename: str) -> Any:
    """Carga otro módulo de esta carpeta (su nombre empieza por un dígito y no admite `import`)."""
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location("_app3_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# `11` da el diff, el repositorio temporal, el schema de hallazgos y la puntuación contra lo sembrado; `10`, la calibración.
m11 = load_sibling("11_criterios_y_ci.py")
m10 = load_sibling("10_confianza_y_revision.py")

PARTS = ["plan", "revision"]
ANTI_VARIANTS = ["autorrevision", "autorrevision_explicita", "una_pasada"]
# Herramientas de la sesión que genera: puede escribir. Las de revisión nunca.
GENERATOR_TOOLS = ("Read", "Grep", "Glob", "Write", "Edit")
# Confianza (de la verificación) desde la que un hallazgo se publica sin pasar por una persona (elección propia).
PUBLISH_THRESHOLD = 0.8
CALIBRATION_EDGES = (0.0, 0.5, 0.8, 0.95, 1.01)
# Hallazgos de dos pasadas que cuentan como el mismo: mismo archivo, misma categoría y línea cercana.
MERGE_WINDOW = 2

FILE_TASK = (
    "Eres un revisor de código en CI. Revisa solo este archivo del cambio: no tienes acceso al resto del repositorio. "
    "Informa solo de problemas visibles en este archivo y responde solo con el objeto JSON del schema, con tu confianza (0 a 1) en cada hallazgo.\n"
)
INTEGRATION_TASK = (
    "Eres un revisor de código en CI. Esta es la pasada de integración: cada archivo ya se revisó por separado (hallazgos abajo). "
    "No repitas esos hallazgos; busca solo problemas entre archivos: contratos, unidades, firmas y flujo de datos entre quien cambia y quien llama. "
    "Puedes leer el repositorio con Read, Grep y Glob. Responde solo con el objeto JSON del schema, con tu confianza (0 a 1) en cada hallazgo.\n"
)
SINGLE_TASK = (
    "Eres un revisor de código en CI. Revisa el cambio completo de este commit, todos sus archivos, en una sola pasada: "
    "tanto los problemas de cada archivo como los que aparecen entre archivos. "
    "Puedes leer el repositorio con Read, Grep y Glob para comprobar a quién afecta un cambio. "
    "Responde solo con el objeto JSON del schema, con tu confianza (0 a 1) en cada hallazgo.\n"
)
VERIFICATION_TASK = (
    "Eres un verificador. Para cada hallazgo numerado, di con qué confianza (0 a 1) es un problema real del código de este diff, "
    "y por qué. Responde solo con el objeto JSON del schema.\n"
)
# Una sola frase distingue `autorrevision_explicita` de `autorrevision`.
SELF_REVIEW_NOTE = "Revisa críticamente tu propio cambio: busca los fallos que hayas podido pasar por alto al escribirlo.\n"


# --- Reparto en pasadas (4.6-K3, S2 · 1.6-K2, S2) ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Pass:
    kind: str  # `file` o `integration`
    name: str
    chunk: str
    tools: tuple[str, ...]


def split_diff(diff: str) -> dict[str, str]:
    """Un trozo de diff por archivo, en orden de aparición."""
    chunks: dict[str, str] = {}
    current = None
    for line in diff.splitlines(keepends=True):
        match = re.match(r"diff --git a/(\S+) b/", line)
        if match:
            current = match.group(1)
            chunks[current] = ""
        if current:
            chunks[current] += line
    return chunks


def plan_passes(diff: str, anti: str | None = None) -> list[Pass]:
    """Una pasada local por archivo (sin tools: no puede ver a los llamadores) y una de integración (con lectura).

    `--anti una_pasada` cambia solo este reparto: una única pasada larga sobre todo el diff (con las tools de lectura de la
    de integración), sin pasada por archivo ni de integración. La verificación y la instancia nueva son las mismas.
    """
    if anti == "una_pasada":
        return [Pass("single", "revisión única", diff, headless.READ_ONLY_TOOLS)]
    passes = [Pass("file", name, chunk, ()) for name, chunk in split_diff(diff).items()]
    return passes + [Pass("integration", "integración", diff, headless.READ_ONLY_TOOLS)]


def findings_schema() -> dict[str, Any]:
    """El schema de `11` con la confianza (0 a 1) de cada hallazgo (4.6-S3)."""
    schema = copy.deepcopy(m11.review_schema())
    item = schema["properties"]["findings"]["items"]
    item["properties"]["confidence"] = {"type": "number", "minimum": 0, "maximum": 1}
    item["required"] = [*item["required"], "confidence"]
    return schema


def verification_schema() -> dict[str, Any]:
    verdict = {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}, "reason": {"type": "string"}},
        "required": ["id", "confidence", "reason"],
        "additionalProperties": False,
    }
    return {"type": "object", "properties": {"verdicts": {"type": "array", "items": verdict}}, "required": ["verdicts"], "additionalProperties": False}


def file_pass_prompt(file_diff: str, *, message: str) -> str:
    return m11.build_review_prompt(file_diff, message=message, task=FILE_TASK)


def single_pass_prompt(diff: str, *, message: str) -> str:
    """La pasada única de `--anti una_pasada`: mismos criterios y ejemplos que las demás, sobre todo el diff a la vez."""
    return m11.build_review_prompt(diff, message=message, task=SINGLE_TASK)


def _listing(findings: list[dict]) -> str:
    return "\n".join(f"- {f['file']}:{f['line']} ({f['category']}): {f['problem']}" for f in findings) or "ninguno"


def integration_prompt(diff: str, local: list[dict], *, message: str) -> str:
    prompt = m11.build_review_prompt(diff, message=message, task=INTEGRATION_TASK)
    return prompt.replace(INTEGRATION_TASK, INTEGRATION_TASK + "Hallazgos de la pasada por archivo:\n" + _listing(local) + "\n", 1)


def verification_prompt(diff: str, findings: list[dict]) -> str:
    numbered = "\n".join(f"{i} {f['file']}:{f['line']} ({f['category']}): {f['problem']}" for i, f in enumerate(findings))
    return f"{VERIFICATION_TASK}\nHallazgos:\n{numbered}\n\nDiff:\n{diff}"


def with_arm_note(prompt: str, anti: str | None) -> str:
    """La rama `autorrevision_explicita` antepone una frase; las otras usan el prompt tal cual."""
    if anti not in (None, "autorrevision", "autorrevision_explicita", "una_pasada"):
        raise ValueError(f"variante desconocida: {anti}")
    return SELF_REVIEW_NOTE + prompt if anti == "autorrevision_explicita" else prompt


def session_args(anti: str | None, generator_session: str) -> dict[str, Any]:
    """La instancia nueva (también la de `una_pasada`) no parte de ninguna sesión; la autorrevisión bifurca la que generó el código."""
    return {"resume": None, "fork": False} if anti in (None, "una_pasada") else {"resume": generator_session, "fork": True}


# --- Fusión, confianza y enrutado ----------------------------------------------------------------------------------------------------------


def _alike(a: dict, b: dict) -> bool:
    """¿Hablan del mismo problema? El mismo `detected_pattern` normalizado, o palabras del problema en común (Jaccard ≥ 0,3)."""
    pa, pb = m11.normalize_pattern(a.get("detected_pattern")), m11.normalize_pattern(b.get("detected_pattern"))
    if pa == pb and pa != "sin_patron":
        return True
    words = lambda f: {w for w in re.findall(r"\w+", str(f.get("problem", "")).casefold()) if len(w) > 3}  # noqa: E731
    wa, wb = words(a), words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= 0.3


def _same(a: dict, b: dict) -> bool:
    """Mismo archivo, misma categoría, línea cercana **y** el mismo problema.

    Con solo la ventana, dos hallazgos distintos a una línea de distancia se fusionaban y el segundo se perdía. Límite que
    queda: el mismo problema contado con otras palabras y otro `detected_pattern` no se fusiona, y cuenta dos veces.
    """
    return a["file"] == b["file"] and a["category"] == b["category"] and abs(a["line"] - b["line"]) <= MERGE_WINDOW and _alike(a, b)


def merge_findings(per_file: dict[str, list[dict]], integration: list[dict]) -> list[dict]:
    """Une las dos pasadas. Un hallazgo de integración que repite uno local no se duplica (conserva la confianza más alta)."""
    merged = [{**f, "source": "file"} for findings in per_file.values() for f in findings]
    for f in integration:
        twin = next((m for m in merged if _same(m, f)), None)
        if twin is None:
            merged.append({**f, "source": "integration"})
        elif (f.get("confidence") or 0) > (twin.get("confidence") or 0):
            twin["confidence"] = f["confidence"]
    return merged


def apply_verdicts(findings: list[dict], verdicts: list[dict]) -> list[dict]:
    """La confianza que cuenta es la de la verificación; la declarada al generar el hallazgo se conserva aparte."""
    by_id = {v["id"]: v["confidence"] for v in verdicts if isinstance(v, dict) and "id" in v and "confidence" in v}
    return [{**f, "declared_confidence": f.get("confidence"), "confidence": by_id.get(i)} for i, f in enumerate(findings)]


def route_by_confidence(findings: list[dict], *, threshold: float) -> tuple[list[dict], list[dict]]:
    """(publicar, a una persona): sin confianza o por debajo del umbral va a revisión humana."""
    publish, human = [], []
    for f in findings:
        confidence = f.get("confidence")
        (publish if isinstance(confidence, (int, float)) and confidence >= threshold else human).append(f)
    return publish, human


def finding_cells(findings: list[dict], labels: dict, *, scope: int) -> list[Any]:
    """Un hallazgo como celda de `app3/10`: su confianza y si coincide con un fallo sembrado."""
    cells = []
    for f in findings:
        confidence = m10._valid_confidence(f.get("confidence"))
        correct = m11.score_findings([f], labels, scope=scope).true_findings == 1
        cells.append(m10.Cell(f"{f.get('file')}:{f.get('line')}", "hallazgos", str(f.get("category")), str(f.get("source", "")), "finding", confidence, confidence, correct, False, False))
    return cells


def found_by_pass(merged: list[dict], labels: dict, *, scope: int) -> dict[str, set[str]]:
    """Qué fallos sembrados encontró cada pasada. Uno que salió en las dos cuenta para la local. Con `una_pasada`, todo es de la única."""
    if merged and all(f.get("source") == "single" for f in merged):
        return {"single": m11.score_findings(merged, labels, scope=scope).found}
    local = m11.score_findings([f for f in merged if f.get("source") == "file"], labels, scope=scope).found
    both = m11.score_findings(merged, labels, scope=scope).found
    return {"file": local, "integration": both - local}


# --- La sesión generadora y el repositorio ----------------------------------------------------------------------------------------------


def generator_prompt(change: dict) -> str:
    """Especificación del cambio: el mensaje y el contenido exacto de cada archivo, con la orden de explicar las decisiones."""
    files = "\n".join(f"### {name}\n```python\n{content}```\n" for name, content in change["commit_1"].items())
    return (
        f"Implementa este cambio en el repositorio del directorio actual: {change['message_1']}.\n"
        f"Escribe cada archivo con Write con exactamente este contenido, sin modificarlo:\n\n{files}\n"
        "No crees ningún otro archivo ni toques ninguno que no esté en esta lista.\n"
        "Cuando termines, explica en un párrafo por qué tomaste cada decisión de este cambio.\n"
    )


@dataclass
class GeneratorRepo:
    path: Path
    base: str
    target_diff: str  # el diff del cambio dado, calculado aparte: el repositorio del generador no lo contiene


def build_generator_repo() -> GeneratorRepo:
    """Repositorio temporal en el estado base, con un único commit: la sesión generadora escribe el cambio sobre él.

    No es el repositorio de `11` devuelto con `reset --hard`: ese conserva los dos commits del cambio (y sus mensajes, en el
    reflog y en `COMMIT_EDITMSG`) al alcance de `Grep` y `Read`, y el revisor podría leer el cambio ya hecho. El diff esperado
    se calcula en otro repositorio.
    """
    full = m11.build_review_repo()
    target = m11.diff_of(full, full.base, full.commit_1)
    clean = m11.build_review_repo(commits=0)
    return GeneratorRepo(clean.path, clean.base, target)


def generated_diff(repo: Any) -> str:
    """Lo que ha cambiado el árbol de trabajo respecto al estado base, también los archivos nuevos sin seguimiento.

    `git diff <base>` no los ve; `add -N` (intent-to-add) los registra sin guardar su contenido y entran en el diff.
    """
    m11._git(repo.path, "add", "-N", "--all")
    return m11._git(repo.path, "diff", "--no-color", "-U3", repo.base)


def matches_target(repo: Any, change: dict) -> bool:
    """¿Escribió la sesión exactamente el cambio que se le dio? Si no, se puntúa su diff real, no el esperado."""
    return generated_diff(repo) == repo.target_diff


def mismatch_files(repo: Any, change: dict) -> list[str]:
    """Archivos cuyo contenido no es el que se dio a la sesión, y los que ha tocado de más."""
    wrong = [name for name, content in change["commit_1"].items() if not (repo.path / name).is_file() or (repo.path / name).read_bytes() != content.encode("utf-8")]
    touched = m11._git(repo.path, "status", "--porcelain", "--untracked-files=all").splitlines()
    extra = [line[3:].strip().strip('"') for line in touched if line[3:].strip().strip('"') not in change["commit_1"]]
    return sorted({*wrong, *extra})


def pass_command(cwd: Path, *, model: str, budget: float, schema: dict, tools: tuple[str, ...], session: dict[str, Any]) -> list[str]:
    return headless.build_command(cwd=cwd, model=model, max_budget_usd=budget, schema=schema, tools=tools, resume=session["resume"], fork=session["fork"])


# --- Ejecución ------------------------------------------------------------------------------------------------------------------------------


def run_plan(model: str, budget: float, anti: str | None = None) -> None:
    repo = m11.build_review_repo()
    diff = m11.diff_of(repo, repo.base, repo.commit_1)
    plan = plan_passes(diff, anti)
    message = load("cambio_revision.json")["message_1"]
    print(f"\n=== plan de pasadas · {len(plan)} sobre el diff del primer commit ({len(diff.splitlines())} líneas) ===")
    for p in plan:
        if p.kind == "single":
            prompt = single_pass_prompt(p.chunk, message=message)
        else:
            prompt = file_pass_prompt(p.chunk, message=message) if p.kind == "file" else integration_prompt(p.chunk, [], message=message)
        print(f"  {p.kind:11} {p.name:28} tools={','.join(p.tools) or 'ninguna'} · prompt {len(prompt)} caracteres")
    print("  verificación: confianza por hallazgo, sin tools")
    if anti == "una_pasada":
        cmd = pass_command(repo.path, model=model, budget=budget, schema=findings_schema(), tools=plan[0].tools, session=session_args(anti, "<sesión generadora>"))
        print("[una_pasada: instancia nueva, una sola pasada con lectura; sin --resume]")
        headless.print_command(cmd, stdin_chars=len(single_pass_prompt(plan[0].chunk, message=message)))
        return
    cmd = pass_command(repo.path, model=model, budget=budget, schema=findings_schema(), tools=(), session=session_args("autorrevision", "<sesión generadora>"))
    print("[la autorrevisión bifurca la sesión que generó el código]")
    headless.print_command(cmd, stdin_chars=0)


def _call(ledger: headless.Ledger, cmd_args: dict[str, Any], prompt: str, repo: Any, schema: dict, generator: headless.HeadlessResult | None) -> headless.HeadlessResult:
    cmd = pass_command(repo.path, budget=min(ledger.remaining(), 0.20), schema=schema, **cmd_args)
    result = headless.run(cmd, prompt, cwd=repo.path, schema=schema)
    ledger.add(result, resumed_from=generator if cmd_args["session"]["resume"] else None)
    return result


def run_revision(args: Any, model: str, budget: float) -> None:
    labels = load("cambio_revision_etiquetas.json")
    change = load("cambio_revision.json")
    ledger = headless.Ledger(budget)
    repo = build_generator_repo()
    # La sesión que genera: escribe el cambio y explica por qué. Persiste, porque se va a reanudar.
    gen_cmd = headless.build_command(cwd=repo.path, model=model, max_budget_usd=min(ledger.remaining(), 0.30), tools=GENERATOR_TOOLS, persist=True)
    print("\n=== sesión generadora ===")
    generator = headless.run(gen_cmd, generator_prompt(change), cwd=repo.path, schema=None)
    ledger.add(generator)
    if not generator.ok:
        print(f"[corte] la sesión generadora no terminó: {generator.status} {generator.detail}")
        return
    diff = generated_diff(repo)
    exact = matches_target(repo, change)
    print(f"[generador] el diff coincide con el cambio dado: {exact} · {len(diff.splitlines())} líneas · coste {ledger.spent:.4f} $")
    if not exact:
        print(f"[generador] difieren o sobran: {mismatch_files(repo, change)}; se puntúa el diff que escribió, no el esperado")
    arm = args.anti
    steps = "una pasada sobre todo el diff + verificación" if arm == "una_pasada" else "pasadas por archivo + integración + verificación"
    print(f"\n=== revisión · {'instancia nueva' if arm is None else arm} · {args.repeat} ejecuciones · {steps} ===")
    pooled_cells: list[Any] = []
    message = change["message_1"]
    for run in range(1, args.repeat + 1):
        session = session_args(arm, generator.session_id)
        if arm == "una_pasada":
            # Una sola pasada larga con lectura, sin pasada por archivo ni de integración: lo único que cambia respecto a la instancia nueva.
            (p,) = plan_passes(diff, arm)
            r = _call(ledger, {"model": model, "tools": p.tools, "session": session}, single_pass_prompt(p.chunk, message=message), repo, findings_schema(), generator)
            merged = [{**f, "source": "single"} for f in (r.structured["findings"] if r.ok else [])]
        else:
            per_file: dict[str, list[dict]] = {}
            for p in plan_passes(diff):
                if p.kind != "file":
                    continue
                prompt = with_arm_note(file_pass_prompt(p.chunk, message=message), arm)
                r = _call(ledger, {"model": model, "tools": p.tools, "session": session}, prompt, repo, findings_schema(), generator)
                per_file[p.name] = r.structured["findings"] if r.ok else []
            local = [f for fs in per_file.values() for f in fs]
            r = _call(ledger, {"model": model, "tools": headless.READ_ONLY_TOOLS, "session": session}, with_arm_note(integration_prompt(diff, local, message=message), arm), repo, findings_schema(), generator)
            integration = r.structured["findings"] if r.ok else []
            merged = merge_findings(per_file, integration)
        verdicts: list[dict] = []
        if merged:
            v = _call(ledger, {"model": model, "tools": (), "session": session}, with_arm_note(verification_prompt(diff, merged), arm), repo, verification_schema(), generator)
            verdicts = v.structured["verdicts"] if v.ok else []
        verified = apply_verdicts(merged, verdicts)
        score = m11.score_findings(verified, labels, scope=1)
        by_pass = found_by_pass(verified, labels, scope=1)
        publish, human = route_by_confidence(verified, threshold=PUBLISH_THRESHOLD)
        cells = finding_cells(verified, labels, scope=1)
        pooled_cells += cells
        where = f"una pasada: {sorted(by_pass['single'])}" if "single" in by_pass else f"por archivo: {sorted(by_pass['file'])} · integración: {sorted(by_pass['integration'])}"
        print(
            f"[{run}/{args.repeat}] {where} · faltan {sorted(score.missed)} · "
            f"falsos positivos {len(score.false_positives)} · marcó lo correcto {len(score.flagged_ok)} · publicados {len(publish)} (acierto {m10.pct(m10.accuracy([c for c in cells if c.confidence is not None and c.confidence >= PUBLISH_THRESHOLD]))}) · "
            f"a una persona {len(human)} · coste acumulado {ledger.spent:.4f} $"
        )
    bands = m10.confidence_bands(pooled_cells, edges=CALIBRATION_EDGES)
    for band in bands:
        if band.n:
            print(f"  confianza {band.low:.2f}–{min(band.high, 1.0):.2f}: {band.n} hallazgos, coinciden con un fallo sembrado {m10.pct(band.accuracy)}, la verificación decía {m10.pct(band.mean_confidence)}")
    print(f"  hueco de calibración de la verificación: {m10.calibration_gap(bands):.3f}")
    print(f"\n[fin] coste={ledger.spent:.4f} $ de ${budget} (incluye la sesión generadora una vez; cada revisión cuenta solo lo suyo)")


def main() -> int:
    parser = build_parser(__doc__.splitlines()[0], anti_variants=ANTI_VARIANTS)
    parser.add_argument("--parte", choices=PARTS, default="plan", help="`plan` muestra las pasadas y la orden sin ejecutar nada; `revision` genera y revisa con `claude -p`")
    args = parser.parse_args()
    if args.anti and args.parte != "revision" and not (args.parte == "plan" and args.anti == "una_pasada"):
        parser.error("--anti es de la parte revision (`--parte plan` acepta solo una_pasada, para ver su única pasada)")
    print(credentials.describe())
    model = report_model("reviewer")
    budget = report_budget(args.budget, "multiagent")
    if args.parte == "plan":
        run_plan(model, budget, args.anti)
        return 0
    try:
        run_revision(args, model, budget)
    except headless.BudgetExhausted as exc:
        print(f"[corte] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
