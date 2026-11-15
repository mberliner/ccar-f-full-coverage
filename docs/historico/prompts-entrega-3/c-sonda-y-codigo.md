Tanda C de la entrega 3: sonda C1 y código de `app3/10`, `11` y `12` (pasos C1 y C2 del diseño). Crea la rama `entrega-3c` desde `main`. Lee primero `docs/diseno-entrega-3.md` (tanda C y riesgos), `NOTAS.md` (tandas A y B), `docs/hallazgos.md` (las dos secciones de la tanda B) y `app3_sistema_multiagente/CLAUDE.md`.

El texto de la guía está fuera del clon. Las viñetas que necesitas van resumidas aquí, con el número de cada una. Los textos didácticos (`QUÉ DICE LA GUÍA`, `ANTI-PATRÓN`, predicciones y preguntas tipo examen) los hace Opus después: escríbelos provisionales y márcalos con `<!-- BORRADOR (Sonnet 5.5): pendiente del pase de textos de Opus 5.5. -->` en el README y con una línea `BORRADOR` en la cabecera. Incluye en el mismo commit que cada módulo el `INTRODUCE`, la fila ☑ de `CONCEPTOS.md` y el contador.

**Reglas de siempre**
- Tests primero; un commit por paso (sonda, cada módulo, registros).
- `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.
- `max_budget_usd` en toda ejecución con modelo. Si el total de la tarea va a pasar de **3 $**, para y avisa antes de seguir.
- Los datos solo se cambian desde `datos/generar_sinteticos.py`.
- Si una señal no aparece, no se fabrica: primero el modelo del rol y después Haiku 4.5 (rol `enforcement`), y si tampoco sale, se documenta.

**Lo aprendido en las tandas A y B (aplícalo desde el principio)**
1. **Cada `--anti` cambia una sola cosa** respecto a la correcta. En `app3/04`, una variante que cambiaba el mensaje y además quitaba el reintento atribuyó a una viñeta el efecto de otra.
2. **Otro modelo para una prueba puntual se pide por rol, no por variable de entorno:** `.env` manda sobre el entorno. El rol `enforcement` (Haiku 4.5) existe para eso; añade un selector de rol al módulo si lo necesitas, como `--rol-modelo` en `app3/08` o `--rol-subagente` en `app3/05`.
3. **Medidas de texto sin modelo:** cada una lleva un test con su falso positivo y su falso negativo; la negación va pegada a la palabra («no es un fallo»); por caso y no por texto completo; cifras en todas sus formas. **Control positivo:** una medida que da cero no demuestra que detecte el fallo. **Mide donde ocurre:** si un agente revisa a otro, mide también la salida intermedia, no solo la final.
4. **Registros:** costes separados por parte y por variante; las mediciones de antes y de después de un cambio, marcadas; el tamaño de la muestra (`--repeat 3` en lo que da la señal).
5. Si algo no se puede medir con modelo, la lección se enseña con un ejercicio determinista y lo que haría el modelo queda como hipótesis.

**C1 · Sonda de `claude -p` (antes de codificar `11` y `12`)**

Con la CLI que usen los módulos (la instalada y, si difiere, la del SDK fijado; anota las versiones):
1. Forma de la salida con `--output-format json` y con `--json-schema`: dónde va el objeto estructurado, qué pasa si el modelo no cumple el schema, qué campos de coste y de sesión trae.
2. **Aislamiento** (roadmap §3, regla 3): con qué flags se evita cargar la configuración de usuario y la memoria (`--setting-sources`, MCP estricto, el `env` de `harness/options.py`) **pero sí se carga el `CLAUDE.md` del `cwd` temporal**, que en `11` es el contexto de CI (3.6-K3). Comprueba las dos cosas: que llega el del proyecto temporal y que no llega nada de fuera. `[contexto]` sin la capa meta (§11.6) también en esta orden.
3. **Tope de coste:** si hay un flag; si no, cómo se acota (presupuesto por ejecución desde el arnés, `--max-turns` solo como red).
4. `--resume` desde `claude -p` para la autorrevisión de `12`: si conserva la sesión del generador y cuánto suma su coste (§4.3: el coste de una sesión reanudada es acumulado).
5. Según el resultado, `harness/headless.py`: construye la orden aislada, exige el tope y la imprime entera antes de ejecutarla. Tests sin modelo de la orden construida.

Resultado en `docs/hallazgos.md` (sección nueva de la tanda C) con `→ roadmap` donde corresponda (§3 regla 3 y §5). Rol `reviewer` (Sonnet 5.5) para la sonda.

**C2 · `app3/10_confianza_y_revision` (TS 5.5, 8 viñetas)**

Viñetas:
- K1: una exactitud agregada alta (p. ej. 97 %) puede esconder un tipo de documento o un campo con mal rendimiento.
- K2 y S1: muestreo aleatorio estratificado de las extracciones de alta confianza, para medir su tasa de error y detectar patrones de error nuevos.
- K3 y S3: confianza por campo que da el propio modelo, calibrada con un conjunto etiquetado para fijar los umbrales de revisión.
- K4 y S2: validar la exactitud por tipo de documento y por campo antes de automatizar las extracciones de alta confianza o reducir la revisión humana.
- S4: enrutar a revisión humana las extracciones de baja confianza **o con documentos ambiguos o contradictorios**, priorizando una capacidad de revisión limitada.

Huecos del diseño frente a la guía, que tienes que cubrir:
- **S3 pide que la confianza la dé el modelo.** La extracción de `07` no la trae. Haz una ejecución con modelo (Haiku 5.5, rol `agent`) que extraiga con confianza por campo, y usa un conjunto fijo para los tests. Mide si la confianza del modelo está calibrada; si no lo está, esa es la lección.
- **K1 necesita un segmento malo de verdad:** un tipo de documento o un campo donde se equivoque, escondido en una exactitud global alta. Si con los datos actuales no hay, hazlo en el generador (más documentos de un tipo difícil), no en el cálculo.
- **S4: capacidad limitada y documentos contradictorios.** Añade un cupo de revisión y una cola priorizada; los documentos con `conflict_detected` de `08` van a revisión aunque su confianza sea alta.
- Variantes: `--anti confianza_global` (una confianza por documento esconde el campo malo) y, si cabe en una sola diferencia, `--anti precision_agregada` (se automatiza mirando solo la exactitud global). Muestreo aleatorio simple frente a estratificado como contraste, sin modelo.

**C2 · `app3/11_criterios_y_ci` (18 viñetas)**

Viñetas:
- **3.6** K1: `-p` para el modo no interactivo. K2: `--output-format json` y `--json-schema` para salida estructurada en CI. K3: `CLAUDE.md` como el contexto del proyecto (estándares de tests, convenciones de *fixtures*, criterios de revisión) para Claude Code en CI. S1: `-p` para que no se quede esperando entrada. S2: hallazgos legibles por máquina para publicarlos como comentarios en línea de un PR. S3: al volver a revisar tras commits nuevos, los hallazgos previos en contexto y la orden de informar solo de lo nuevo o no resuelto, para no duplicar. S4: los tests existentes en contexto para que la **generación de tests** no proponga escenarios ya cubiertos. S5: estándares de tests, criterios de un test valioso y *fixtures* disponibles en `CLAUDE.md`, para que los tests generados sean mejores.
- **4.1** K1: criterios explícitos frente a instrucciones vagas («marca un comentario solo si lo que dice contradice el código» frente a «comprueba que los comentarios son correctos»). K2: «sé conservador» o «solo alta confianza» no mejoran la precisión frente a criterios categóricos. K3: una categoría con muchos falsos positivos hace desconfiar también de las acertadas. S1: criterios que dicen qué informar (bugs, seguridad) y qué no (estilo menor, patrones locales). S2: desactivar temporalmente las categorías con muchos falsos positivos mientras se mejoran. S3: severidades con ejemplos de código concretos para cada nivel.
- **4.2** S2: *few-shot* con el formato de salida (ubicación, problema, severidad, arreglo propuesto). S3: *few-shot* que distinguen un patrón aceptable de un problema real.
- **4.4** K3 y S3: un campo `detected_pattern` en cada hallazgo, para analizar qué patrones descartan los desarrolladores.

Huecos del diseño frente a la guía:
- **3.6-S3 necesita una segunda revisión tras un commit nuevo:** con los hallazgos de la primera en contexto, mide cuántos se repiten frente a sin ellos.
- **3.6-S4 y S5 hablan de generar tests, no de revisar.** Añade una parte pequeña: pedir los tests que faltan para el cambio, con y sin los tests existentes en contexto y con y sin los estándares en el `CLAUDE.md` temporal, y medir los escenarios duplicados.
- **4.1-S2:** una categoría con muchos falsos positivos (p. ej. estilo o comentarios) desactivada frente a activa, y su efecto en la precisión del resto.
- **4.4-S3:** un registro de hallazgos descartados (los que no coinciden con lo sembrado) agrupado por `detected_pattern`, sin modelo.
- **El diff:** una copia temporal de `repo_mesa` con un cambio que tenga fallos sembrados de categorías distintas, un cambio correcto que no debe marcarse y un patrón aceptable que parece un problema. Etiquetas en el generador.
- Variantes: `--anti conservador` (solo «sé conservador» en lugar de los criterios) y `--anti sin_ejemplos` (sin *few-shot*). Cada una cambia una sola cosa.
- Señal: JSON válido contra el schema, fallos sembrados encontrados, el cambio correcto sin marcar.

**C2 · `app3/12_revision_independiente` (9 viñetas)**

Viñetas:
- **4.6** K1: el modelo conserva el razonamiento de la generación y cuestiona menos sus decisiones en la misma sesión. K2: una instancia independiente, sin ese contexto, encuentra mejor los problemas sutiles que las instrucciones de autorrevisión o el *extended thinking*. K3 y S2: revisión en varias pasadas, una por archivo para lo local y otra de integración para el flujo de datos entre archivos, para evitar la dilución de la atención y los hallazgos contradictorios. S1: una segunda instancia revisa el código generado. S3: pasada de verificación con la confianza de cada hallazgo, para enrutar la revisión.
- **1.6** K2 y S2: el encadenamiento de prompts para revisiones (cada archivo, luego integración).
- **3.6** K4: la misma sesión que generó el código revisa peor sus cambios que una instancia independiente.

Huecos del diseño frente a la guía:
- **La autorrevisión necesita una sesión que haya generado el código.** Decide cómo: por ejemplo, que la sesión generadora aplique el cambio del diff a partir de una especificación, razonando, y que después se revise con `--resume`. Documenta la decisión en el módulo y en `NOTAS.md` antes de codificar.
- **K2 compara con dos cosas:** la instancia nueva frente a la autorrevisión con `resume` (`--anti autorrevision`) y, si cabe, frente a la misma sesión con una instrucción explícita de autorrevisión. Cada variante, una diferencia.
- **K3 necesita un fallo entre archivos:** uno que la pasada por archivo no puede ver y la de integración sí (un cambio de firma o de unidad en un archivo que rompe a quien lo llama en otro).
- **S3:** confianza por hallazgo y su calibración contra lo sembrado (reutiliza lo de `10` si encaja).
- El coste acumulado de la sesión reanudada entra en el tope de esa rama.

**Al terminar**

- `CONCEPTOS.md`: 190 + 8 + 18 + 9 = **225/240** (las 15 restantes son de la tanda D). Comprueba el recuento con `tests/test_una_vez.py`.
- `NOTAS.md` (casilla de la tanda C) y `docs/hallazgos.md` con las cifras.
- Un informe con:
  - los commits;
  - la sonda C1 y la decisión sobre `harness/headless.py`;
  - una tabla de cifras por módulo y variante, con el modelo, el número de ejecuciones y el coste de cada una;
  - qué hueco frente a la guía quedó cubierto y cuál no;
  - lo que no salió o salió distinto de lo esperado.
