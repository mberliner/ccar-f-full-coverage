Tanda C de la entrega 3: segunda ronda de correcciones de textos (Opus 5.5), tras la segunda revisión independiente. Rama `entrega-3c`. Solo textos (README de `app3`, cabecera de `app3/11`, `docs/hallazgos.md`, `docs/tipos-de-senal.md`, `NOTAS.md`); no cambies código, datos ni cifras. Ninguna cifra se calcula aquí.

Lee `docs/estandares-codigo.md` (carriles de contenido), la cabecera de `app3/11`, su sección del README y las secciones «después de las correcciones C4» de `docs/hallazgos.md`. Los números son los del informe de la revisión.

**1 · 3.6-S4: «0 repetidos» (README ~1285 y ~1346, `hallazgos.md` ~298, cabecera de `11` líneas 55-56, fila de `--parte tests` en `tipos-de-senal.md`)**
- Los textos dicen que los tests existentes «son justo los que el cambio rompe». Solo vale para 2 de los 5 escenarios (`calcular_sla(alta, 3)` y `horas_restantes`; lo dice `datos/generar_sinteticos.py` cerca de la línea 1151). Los otros 3 (`calcular_sla(alta, 9)` con `ValueError` y los dos `debe_escalar`) no cambian con el commit y repetirlos sería un duplicado real. Corrige la frase: 2 de 5 son los que el cambio rompe.
- La clave nueva (`_norm_expected`) exige que coincidan todos los números del texto de `expected`; un duplicado real escrito con un número de más («lanza ValueError: 9 h de 8 h») deja de contarse. Por tanto el 0 frente a 0 puede ser en parte un artefacto de la clave y **no demuestra que no hubiera duplicados reales**. Escríbelo como limitación de la medida, di que ningún test cubre ese caso y que las propuestas no se revisaron a mano (si las propuestas no están guardadas, dilo así).
- Resultado: el Paso 3 no presenta el 0 como señal ni a favor ni en contra de 3.6-S4. En el examen manda la guía. La parte «antes» (siempre `calcular_sla(alta, 3)`, el test roto reescrito a minutos) está bien explicada: no la toques.
- Anota en `docs/hallazgos.md`, como posible ampliación y sin hacerla, relajar la clave (comparar solo el número principal y la excepción) y revisar las propuestas a mano.

**2 · «Marca el cambio correcto»: la cifra incluye un artefacto (cabecera de `11` líneas ~49 y 59-60, README ~1269-1272, `hallazgos.md` ~285, `tipos-de-senal.md` ~108)**
- En la correcta, 2 de las 5 marcas son el renombrado a `NOTIF_TIMEOUT`, que la propia puntuación cuenta como marca sin serlo (nota del README ~1284); la única marca de la variante `comment` también es ese renombrado.
- Si cada ejecución marcó una sola cosa («3 + 2»), la marca que depende del criterio de comentarios (`REINTENTOS`) sale en **3 de 5 frente a 0 de 5**, no en 5 frente a 0 ni en 5 frente a 1. Reescribe con esa cifra y di cómo se obtuvo (la suma de la nota y la lectura «una marca por ejecución», marcada como lectura y no como medida directa). La señal se sostiene con 3/5 frente a 0/5: la fila de `--sin-categoria comment` puede seguir como está si el texto la apoya en esa cifra.
- Errata en `hallazgos.md` ~285: «5/5 en la correcta y en `sin_ejemplos` (4/5)» se contradice. Corrígela con la cifra de la tabla de cifras de ese mismo apartado.

**3 · «Antes/después» (`hallazgos.md` ~272, README ~1297)**
- Las correcciones C4 también cambiaron el prompt de todas las variantes (la línea de `bug` ya no cita el docstring y cambió el ejemplo de `minor`) y los datos (`NOTIF_TIMEOUT`). Lístalo junto a `--sin-categoria comment` y `TIMEOUT`.
- «Las pérdidas de A de `conservador` se explican, con mucha probabilidad, por el árbol contaminado» no tiene en cuenta esos otros cambios: baja a «una explicación posible, junto a los cambios de prompt y de datos; no se aisló».

**Reglas de siempre**
- Carriles: `Producto observado (no evaluable)` donde corresponda, escritos exactamente. Textos agnósticos. Regla «una vez» intacta (225/240).
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de commitear. Un commit por tema (`11`, registro).
- `NOTAS.md`: marca la segunda revisión y sus correcciones como hechas; pendientes quedan la fusión, `/verificar-concepto` y el roadmap origen.

**Ya corregido en código (no lo toques):** `found_by_pass` con `una_pasada` y sin hallazgos (commit `6fa67f5`).

**Informe final:** commits; qué frase de cada hallazgo cambió; discrepancias que no pudiste resolver.
