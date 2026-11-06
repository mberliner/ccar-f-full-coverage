Tanda C de la entrega 3: pase de textos de `app3/10`, `11` y `12` (Opus 5.5). Trabajas en la rama `entrega-3c`, que ya tiene el código, los tests y los registros hechos por Sonnet 5.5 (225/240, sin fusionar). No cambies código ni datos: si un texto exige un cambio de código, anótalo al final y no lo hagas.

Lee primero `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md`, `docs/diseno-entrega-3.md` (tanda C), `NOTAS.md` (casilla de la tanda C), `docs/hallazgos.md` (sección de la tanda C y sonda C1), `app3_sistema_multiagente/CLAUDE.md`, `plantillas/modulo/README.md` y, como modelo de un pase ya hecho, las cabeceras y el README de `app3/04`–`06`.

**Qué hay que hacer**

1. **Cabeceras** de `10_confianza_y_revision.py`, `11_criterios_y_ci.py` y `12_revision_independiente.py`: quitar la línea `BORRADOR`. `QUÉ DICE LA GUÍA` se escribe contra el texto de la guía (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio), parafraseado y con cada K/S en su sitio; no se traduce ni se copia. Las Task Statements son 5.5 (`10`); 3.6, 4.1, 4.2-S2/S3 y 4.4-K3/S3 (`11`); 4.6, 1.6-K2/S2 y 3.6-K4 (`12`). `ANTI-PATRÓN / TRAMPA DEL EXAMEN` separa los hechos de la guía de las **inferencias propias**, rotuladas como tales.
2. **README**: quitar los comentarios `BORRADOR` de las tres secciones. Revisar predicciones, Paso 3, preguntas tipo examen y «Antes de empezar» contra las reglas 1 a 5 de «Incorporación de quien llega de cero» (roadmap §13): el contexto no adelanta resultados, las predicciones son por patrón y no por valor, los términos comunes enlazan al glosario, y en las preguntas las cuatro opciones son plausibles, de longitud y registro parecidos y la correcta no está siempre en la misma posición (las posiciones de `01`–`09` están en `NOTAS.md`; elige para `10`, `11` y `12` otras que mantengan el reparto equilibrado).
3. **Pregunta multiple-response** en `11` (18 viñetas, ≥ `DENSE_MIN`): obligatoria, tras la de respuesta única, con «**Selecciona dos**» (o el número que toque), una opción más que las que se eligen y como máximo cuatro, cada opción juzgable sola y la respuesta justificando cada una. Formato en `plantillas/modulo/README.md`; lo comprueba `tests/test_readme_modulos.py`. En `10` y `12` es opcional.
4. **Glosario** (`docs/glosario.md`): términos nuevos de la tanda (por ejemplo calibración, muestreo estratificado, cola de revisión, `detected_pattern`, pasada de integración, autorrevisión). Solo los que la tanda introduce.

**Lo que salió distinto de lo esperado: no se maquilla ni se convierte en respuesta de examen**

Sonnet 5.5 midió tres cosas que contradicen o no respaldan lo que dice la guía. En el examen manda siempre la guía; lo observado va en el Paso 3 rotulado `Producto observado (no evaluable)` y se dice expresamente que no cambia la respuesta de examen:

- **Autorrevisión** (`12`): no encontró menos que la instancia nueva. La guía (4.6-K1/K2, 3.6-K4) dice que la instancia independiente encuentra mejor los problemas sutiles. La respuesta de examen es la de la guía.
- **Tests existentes en contexto** (`11`, 3.6-S4): no redujeron los duplicados (1 con ellos, 0 sin ellos). La viñeta sigue siendo la que dice la guía.
- **`--anti conservador`** (`11`): con 3 ejecuciones parecía perder el bug A y con 5 más no. Que no haya señal estable es una lección en sí (4.1-K2) y se clasifica como tal en `docs/tipos-de-senal.md`; comprueba que la fila existe y coincide con lo medido (`tests/test_tipos_de_senal.py`).

Además:
- Las cifras de `11` están marcadas «antes» y «después» del segundo fallo entre archivos (F); la puntuación por símbolo no recalculó las anteriores; y en `12` hay hallazgos sin confianza por falta de presupuesto. Los tres avisos deben estar en el README y en `docs/hallazgos.md`, coherentes entre sí y con `NOTAS.md`.
- `autorrevision_explicita` está implementada y probada sin modelo pero **no medida**: el README lo dice y no se presenta ninguna cifra.
- El «razonamiento de generación» de `12` es el de copiar un cambio dado, no el de diseñarlo: es una adaptación y va rotulada como inferencia propia.
- Carriles de contenido: `claude -p`, `--json-schema` y el aislamiento de la sonda C1 son producto observado salvo que la guía los nombre (3.6-K1/K2 sí). Nada fuera del perímetro (`tests/perimetro_excluido.yaml`). Los dos rótulos se escriben exactamente como en `docs/estandares-codigo.md`.
- Un modelo es banco de pruebas, no la lección: ninguna fila del Paso 3 enfrenta dos modelos (`tests/test_sin_comparacion_de_modelos.py`).

**Reglas de siempre**
- Regla «una vez»: no muevas ni dupliques ningún `INTRODUCE`; `USA` solo sobre viñetas ya introducidas.
- Textos agnósticos en los documentos versionados: rutas relativas, sin nombres de personas, cuentas ni perfiles.
- Cifras: copia las de `docs/hallazgos.md` y `NOTAS.md`; no calcules otras. Si una cifra no coincide entre los tres sitios, no elijas: anótalo al final.
- Sin modelo: no ejecutes nada que llame a la API. `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.

**Commits y cierre**
- Un commit por módulo (cabecera + README + glosario de ese módulo) y uno para `NOTAS.md`/`docs/hallazgos.md`.
- `NOTAS.md`: marca el pase de textos como hecho y deja pendientes la revisión independiente (`docs/prompts-entrega-3/c-revision.md`), sus correcciones y la fusión.
- Informe final: commits, qué viñetas quedaron mejor o peor respaldadas por la guía, discrepancias de cifras, cambios de código que los textos piden y no hiciste.
