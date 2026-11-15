Tanda C de la entrega 3: medir más la autorrevisión de `app3/12` (Sonnet 5.5). Trabajas en la rama `entrega-3c`, ya con código, textos y registros. Es una tarea de investigación con modelo, autorizada a gastar más de lo habitual. No cambies código, datos ni puntuación: si crees que hay que cambiarlos, para y anótalo.

Lee primero `CLAUDE.md`, `app3_sistema_multiagente/CLAUDE.md`, la cabecera y el README de `app3/12`, y las secciones de `app3/12` en `docs/hallazgos.md` y de la sonda C1.

**Por qué**
- La guía dice que una instancia independiente encuentra mejor los problemas sutiles que la autorrevisión (4.6-K1/K2, 3.6-K4).
- En la tanda C, `--anti autorrevision` se midió solo en 2 ejecuciones y no encontró menos que la instancia nueva. `--anti autorrevision_explicita` no se midió.
- Con 2 ejecuciones no se puede decir si falta señal o falta muestra. El objetivo es saberlo, sin fabricar nada.

**Qué hacer**

1. **Una sola batería, las tres ramas con la misma versión del código y de la puntuación.** Si cambias algo a mitad, repites todo (lección de la tanda C):
   - `--parte revision --repeat 5` (instancia nueva)
   - `--parte revision --anti autorrevision --repeat 5`
   - `--parte revision --anti autorrevision_explicita --repeat 5`
2. **Tope de coste.** El tope por invocación (`--budget`) tiene que bastar para que la pasada de verificación tenga presupuesto: en la tanda C una autorrevisión se quedó sin él y sus hallazgos quedaron sin confianza. Calcula el tope por invocación con las cifras de `docs/hallazgos.md` (la sesión generadora cuenta una vez; cada revisión cuenta solo lo suyo; la sesión reanudada es coste acumulado) y anota el cálculo. Cada `[fin]` dentro de su tope. Si el total va a pasar de **4 $**, para y avisa antes de seguir.
3. **Qué se informa por rama:** número de ejecuciones, fallos sembrados encontrados (A a F) por pasada de archivo y por pasada de integración, falsos positivos, hallazgos sin confianza (y por qué), coste por ejecución y total. Con el modelo del rol `reviewer`. Cifras como `x/5`.
4. **Control positivo y falso resultado.** Antes de interpretar un cero, comprueba que la medida detecta el fallo en la rama de la instancia nueva. Si la autorrevisión encuentra lo mismo, lo dices: no se fuerza una diferencia. Si la autorrevisión encuentra menos, también lo dices, con la muestra.
5. **No concluyas sobre la guía.** Lo medido es producto observado (`Producto observado (no evaluable)`). La respuesta de examen es la de la guía, salga lo que salga.

**Registro (sin tocar README ni `docs/tipos-de-senal.md`: los actualiza Opus en el pase de correcciones)**
- `docs/hallazgos.md`: sección nueva de la batería, con las dos mediciones anteriores bajo su propio encabezado («antes») y esta («después»). Costes separados por rama.
- `NOTAS.md`: una línea en la casilla de la tanda C con el resultado y el coste.
- Una propuesta final, sin aplicarla, para `docs/tipos-de-senal.md`: qué tipo le corresponde a cada una de las tres ramas con esta muestra (`Probabilística con control positivo`, `Sin señal estable` o `Sin medir`) y por qué. Incluye la pregunta que dejó el pase de textos: si `--parte revision` (instancia nueva) sigue mereciendo `Probabilística con control positivo` cuando el contraste con la autorrevisión no da señal.

**Reglas de siempre**
- `max_budget_usd` en toda ejecución con modelo; los tests no llaman al modelo.
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de commitear.
- Un commit para el registro. Informe final: comandos ejecutados, tabla por rama (ejecuciones, hallazgos, falsos positivos, coste), qué quedó sin señal y la propuesta de clasificación.
