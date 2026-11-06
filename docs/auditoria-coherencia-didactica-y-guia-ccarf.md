# Auditoría de coherencia, didáctica y alineación con CCAR-F

**Estado del proyecto auditado:** en construcción, 190/240 objetivos introducidos.  
**Fuente normativa usada:** Exam Guide v1.0, efectiva en julio de 2026, suministrada para esta auditoría en `../analisis/claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`.  
**Fecha de auditoría:** 2026-11-06.  
**Modalidad:** revisión de código y documentación; tests sin modelo y sin coste. No se ejecutaron sondas con modelos.

## Estado de implementación (2026-11-06)

| Hallazgo | Estado | Qué se hizo |
| :--- | :--- | :--- |
| G-02 `updatedInput` en `app2/07` | ✅ **Terminado** | Pregunta reformulada: la respuesta correcta es el hook `PreToolUse` que bloquea y redirige (TS 1.4-S1, 1.5-S2). El módulo queda rotulado como apéndice de producción no evaluable (README y cabecera). |
| G-03 permisos en `app2/03` | ✅ **Terminado** | La pregunta pasa a «Pregunta tipo examen (comprobación operativa, no evaluable)», con la aclaración de que lo evaluable está en `app2/01` y `app2/02`. El encabezado conserva el prefijo que exigen el narrador y `test_readme_modulos`. |
| C-01 fila de `app3/08` | ✅ **Terminado** | La tabla indica K1, K2, K4, S1, S2 y S4, con K3 y S3 en `app3/11`. |
| C-02 ruta raíz de app3 | ✅ **Terminado** | `README.md` describe `01`→`09` y deja `10`–`12` como pendientes. |
| C-03 `app3/CLAUDE.md` | ✅ **Terminado** | Diez fuentes (verificado en `datos/generar_sinteticos.py`) y estado de `06` en `estado/<perfil>/app3-06/`. |
| G-06 multiple-response | 🟡 **Piloto hecho** | Formato definido en `plantillas/modulo/README.md` y `docs/estandares-flujo.md`; el narrador muestra todas las preguntas y respuestas de un módulo; `tests/test_readme_modulos.py` comprueba cuántas elegir, el número de opciones y la justificación por opción. Piloto en `app3/01` (TS 1.2) y `app3/05` (TS 5.6), añadido a la pregunta de respuesta única. Pendiente: extender a más módulos y a las tandas C y D, y decidir cómo plantear 5 opciones con el límite de 4 de `AskUserQuestion`. |
| G-01 strict mode en `app3/07` | ⏳ Pendiente | Requiere comprobar antes si `strict` se puede aplicar a tools MCP del Agent SDK. |
| G-05 test de perímetro | ✅ **Terminado** | La garantía se rebautiza como «lista de exclusión conocida» (docstring del test y del YAML). Se añaden `updatedInput` y `disallowed_tools` con `permitido_en` por archivo, y un test que obliga a borrar las excepciones que ya no se usan. `permission_mode` queda fuera de la lista a propósito: `dontAsk` es fontanería en unos 14 módulos y la excepción no protegería nada. |
| Resto (G-04, G-06 a G-09, C-04, C-05, D-01 a D-05) | ⏳ Pendiente | Fases 1 a 3 del plan. |

Verificación: `uv run pytest -q -rsx` → 829 passed, 1 skipped, 1 xfailed (sin cambios respecto de la auditoría).

## 1. Corrección respecto de la auditoría anterior

La cobertura parcial **no es una falla**. El repositorio está en desarrollo y documenta expresamente el avance en `CONCEPTOS.md`, `NOTAS.md` y `docs/diseno-entrega-3.md`. Los 190 objetivos introducidos y los 50 pendientes forman parte del plan de entrega.

La frase inicial de `README.md` —«para practicar [...] todas las viñetas»— puede leerse como la meta del proyecto. No se clasifica aquí como contradicción ni como defecto. Como mejora de comunicación durante el desarrollo, podría acompañarse de un indicador visible de avance, pero eso no afecta la calidad de lo ya construido.

La guía oficial ahora sí estuvo disponible. Esto permite reemplazar la conclusión anterior de «alineación no verificable» por una comparación directa del temario, los temas fuera de alcance y las afirmaciones de los módulos.

## 2. Resumen ejecutivo

La estructura general está bien alineada con la Exam Guide:

- La guía contiene 30 Task Statements, 113 objetivos de conocimiento y 127 de habilidad: **240 en total**.
- `CONCEPTOS.md` reproduce correctamente esa estructura: 113 K, 127 S y 240 identificadores.
- Los pesos de los cinco dominios coinciden con la guía.
- La organización por agente único, control, sistema multiagente, Claude Code, extracción y fiabilidad cubre de forma reconocible los seis escenarios oficiales.
- Los 829 tests actuales pasan; existe 1 `skip` técnico y 1 `xfail` deliberado para la cobertura todavía incompleta.
- El ciclo predecir → ejecutar/contrastar → responder → registrar el fallo es didácticamente sólido.

La auditoría encontró dos problemas de alineación de prioridad alta:

1. `app3/07` afirma que la guía no nombra el modo estricto de JSON Schema, pero la guía sí lo incluye expresamente. El módulo usa schemas no estrictos, observa valores fuera del `enum` y, al mismo tiempo, introduce objetivos cuya redacción oficial habla de salida garantizada conforme al schema.
2. `app2/07` convierte `updatedInput`, ausente de la guía, en la solución correcta de una pregunta con formato de examen. Esto vulnera la regla interna de perímetro y puede entrenar una respuesta no respaldada por el blueprint.

También hay problemas medios: un módulo completo de permisos presenta como pregunta de examen semánticas que no aparecen en los objetivos; las comparaciones entre modelos ocupan un lugar didáctico importante pese a estar explícitamente fuera de alcance; el test de perímetro no puede sostener la garantía que se le atribuye; no se practica el formato multiple-response; y algunas tablas, instrucciones y datos internos están desactualizados.

## 3. Alcance y método

Se contrastaron:

- la sección 6 de la Exam Guide, con los 30 Task Statements;
- los apartados `In-Scope Topics` y `Out-of-Scope Topics`;
- los detalles y preguntas de muestra del examen;
- `README.md`, `CLAUDE.md`, `CONCEPTOS.md`, `NOTAS.md` y los estándares;
- los módulos entregados de las tres apps y sus README;
- la sección D3;
- los tests de trazabilidad y perímetro;
- el arnés cuando afecta a credenciales, presupuesto o aislamiento.

Comprobaciones ejecutadas:

```text
uv run pytest -q -rsx
829 passed, 1 skipped, 1 xfailed
```

El recuento independiente de la sección 6 de la guía produjo:

```text
task_statements=30 knowledge=113 skills=127 total=240
```

No se ejecutaron módulos con modelo. Las cifras históricas de Haiku, Sonnet o la CLI se trataron como registros del proyecto, no como resultados reproducidos.

## 4. Hallazgos de alineación con la guía

### ALTA — G-01. `app3/07` excluye erróneamente el modo estricto

**Clasificación:** contradicción directa con la Exam Guide y riesgo de enseñar TS 4.3 con una configuración distinta de la que fundamenta la garantía oficial.  
**Certeza:** alta.

La guía dice:

- línea 431: los JSON schemas estrictos mediante tool use eliminan errores de sintaxis, pero no errores semánticos;
- línea 441: las reglas de normalización se incluyen junto a schemas de salida estrictos;
- línea 876: `strict mode for syntax error elimination` aparece en la lista de tecnologías y conceptos.

El proyecto dice lo contrario:

- `app3_sistema_multiagente/07_extraccion_schema.py:65-67`: «el modo estricto [...] la guía no lo nombra y queda fuera»;
- `app3_sistema_multiagente/README.md:759`: repite que la guía no nombra el modo estricto;
- el módulo construye tools con `input_schema`, pero sin activar un modo estricto, y necesita un validador propio porque la API acepta valores fuera del `enum`.

La guía, en TS 4.3-K1, describe tool use con JSON Schema como el enfoque más fiable para obtener salida garantizada conforme al schema. TS 4.3-K3 separa esa conformidad de los errores semánticos, como totales que no suman. El módulo mezcla tres niveles distintos:

1. JSON parseable;
2. conformidad con tipos, `required` y `enum`;
3. verdad semántica respecto del documento.

Su experimento demuestra correctamente que una tool no estricta puede producir JSON parseable que incumple el schema. El problema es atribuir a esa variante no estricta las garantías con las que la guía describe el mecanismo evaluable.

**Riesgo didáctico:** el estudiante puede concluir que el modo estricto es un detalle de producción fuera del examen, cuando la guía lo menciona expresamente.

**Mejora recomendada:** tratar strict mode como parte evaluable; separar con nombres claros «JSON válido», «schema válido» y «dato correcto»; conservar la variante no estricta como anti-patrón o contraste.

### ALTA — G-02. `app2/07` usa contenido no respaldado por la guía como respuesta correcta tipo examen ✅ TERMINADO 2026-11-06

**Clasificación:** violación del perímetro interno y desalineación verificable con el blueprint.  
**Certeza:** alta.

La guía cubre hooks que:

- bloquean llamadas que violan políticas;
- redirigen a un flujo alternativo;
- normalizan resultados mediante `PostToolUse`.

No contiene `updatedInput` ni la reescritura de argumentos de `PreToolUse`.

El propio proyecto lo reconoce:

- `app2_agente_con_control/07_hook_reescritura.py:6-17` declara que no hay una viñeta para reescribir argumentos;
- `app2_agente_con_control/README.md:499` lo marca como no evaluable;
- `app2_agente_con_control/README.md:537-551` presenta una pregunta con formato de examen cuya respuesta correcta depende de `updatedInput`.

Esto contradice `docs/estandares-codigo.md:23-26`, que limita los mecanismos nuevos a comentarios `EN PRODUCCIÓN (no evaluable)`. Aquí el mecanismo aparece en código ejecutable, ocupa un módulo del itinerario y determina la respuesta correcta.

**Matiz:** la técnica puede ser válida en producción. El problema no es técnico, sino su posición dentro del entrenamiento para la certificación.

**Mejora recomendada:** moverla a un apéndice de producción fuera del itinerario evaluable o convertir la pregunta para que la solución respaldada por la guía sea el hook que bloquea y redirige.

### MEDIA — G-03. `app2/03` enseña semántica de permisos no definida por los objetivos ✅ TERMINADO 2026-11-06

**Clasificación:** ampliación del temario no respaldada; no contradicción factual demostrada.  
**Certeza:** alta sobre la ausencia en el blueprint.

La guía menciona `allowedTools` en dos contextos concretos:

- el coordinador debe incluir `Task` para lanzar subagentes;
- el frontmatter de una skill puede restringir sus tools.

No desarrolla:

- `permission_mode="dontAsk"`;
- `disallowed_tools`;
- la idea de que `allowed_tools` «pre-aprueba pero no restringe»;
- la herencia del modo de permisos;
- el orden hooks → deny → ask → modo → allow → `can_use_tool`.

`app2/03` declara correctamente que es «apoyo, sin viñeta propia», pero termina con una pregunta tipo examen cuya respuesta exige conocer precisamente esa semántica.

**Riesgo:** el alumno no puede distinguir con facilidad una ayuda operacional para ejecutar el SDK de un conocimiento evaluable.

**Mejora recomendada:** conservar el módulo como prerrequisito técnico, pero cambiar «Pregunta tipo examen» por «Comprobación operativa» y excluirlo del recuento o ruta de preparación evaluable.

### MEDIA — G-04. Las comparaciones entre modelos invaden el núcleo didáctico aunque la guía las excluye

**Clasificación:** contenido oficialmente fuera de alcance presentado como evidencia principal.  
**Certeza:** alta.

La guía declara fuera de alcance en la línea 925:

- `Performance benchmarking or model comparison metrics`.

El proyecto incluye comparaciones de modelos en partes centrales de varios ejercicios:

- `app1_agente_unico/README.md:324-333`: tabla de selección de tools por Haiku 5.5 y Haiku 4.5;
- `app2_agente_con_control/README.md:106-107`: tasas de cumplimiento y coste entre modelos;
- `app3_sistema_multiagente/README.md`, módulos 07 y 08: se cambia de modelo para producir errores de formato que permitan observar el reintento.

Usar otro modelo como banco de pruebas puede ser legítimo para construir una demostración. Convertir las diferencias entre modelos en parte del aprendizaje central, en cambio, consume atención en un tema que el examen declara fuera de alcance.

**Mejora recomendada:** dejar una única demostración estable del mecanismo; trasladar comparaciones, tasas por modelo y calibración histórica a `docs/hallazgos.md` como material experimental no evaluable.

### MEDIA — G-05. La garantía atribuida al test de perímetro es mayor que su capacidad real ✅ TERMINADO 2026-11-06

**Clasificación:** falso sentido de cobertura.  
**Certeza:** alta.

`tests/test_perimetro.py`:

- solo escanea archivos Python de cuatro directorios;
- ignora comentarios y docstrings deliberadamente;
- detecta únicamente patrones exactos incluidos en `tests/perimetro_excluido.yaml`.

La lista actual solo contiene cinco entradas. No incluye `updatedInput`, `permission_mode`, `disallowed_tools` ni comparaciones de modelos. Por eso el test pasa aunque existan los casos G-02, G-03 y G-04.

El test sí demuestra una propiedad útil: «ninguno de estos cinco mecanismos conocidos aparece de estas formas AST en los árboles analizados». No demuestra que todo el repositorio permanezca dentro del blueprint.

**Mejora recomendada:** renombrar la garantía como lista de exclusión conocida; incluir documentación y configuración en controles separados; derivar la lista de los apartados oficiales In-Scope/Out-of-Scope y de una revisión humana.

### MEDIA — G-06. La práctica no cubre el formato multiple-response

**Clasificación:** omisión didáctica respecto del formato del examen.  
**Certeza:** alta.

La guía, línea 36, dice que el examen contiene preguntas `multiple-choice` y `multiple-response`, indicando en cada pregunta cuántas respuestas seleccionar.

Las preguntas revisadas del proyecto usan una única respuesta correcta. La búsqueda en los README no encontró instrucciones como «selecciona dos», «elige tres» o «más de una respuesta».

**Impacto:** el contenido conceptual puede estar cubierto, pero el estudiante no practica una parte del formato real ni estrategias como evaluar cada opción de manera independiente.

**Mejora recomendada:** añadir preguntas multiple-response, especialmente en módulos densos, y declarar explícitamente cuántas opciones deben elegirse.

### MEDIA — G-07. Falta práctica integrada por escenario

**Clasificación:** oportunidad didáctica, no violación.  
**Certeza:** alta.

La guía, línea 37, estructura el examen como cuatro escenarios tomados de un banco de seis. Cada escenario sostiene varias preguntas y exige mantener contexto y restricciones comunes.

El proyecto refleja los temas de esos escenarios, pero la práctica se organiza principalmente en preguntas independientes por módulo. Las etiquetas E1, E3 y E4 aparecen en las apps; D3, CI y extracción cubren material de los demás escenarios, pero no existe todavía una simulación que agrupe varias preguntas sobre un mismo caso.

**Mejora recomendada:** al terminar cada entrega, incorporar un caso acumulativo con 5–10 preguntas, mezcla de respuesta única y múltiple, y restricciones compartidas.

### BAJA — G-08. `Task` frente a `Agent` está bien advertido, pero exige una convención más visible

**Clasificación:** deriva terminológica controlada.  
**Certeza:** alta.

La guía usa `Task` como mecanismo de invocación y exige que `allowedTools` incluya `Task` (`líneas 138, 656 y 870`). El producto usado por el proyecto expone `Agent`.

Los módulos `app3/01` y `app3/03` explican la diferencia. Esto evita clasificarlo como error. Sin embargo, la mayoría de tablas operativas muestran `Agent`, por lo que el nombre más repetido durante la práctica no es el que debe reconocerse en el examen.

**Mejora recomendada:** usar una etiqueta estable como «Task (en la guía) / Agent (en esta CLI)» en tablas, preguntas y glosario; mantener las preguntas evaluables con la terminología de la guía.

### OBSERVACIÓN — G-09. La propia guía tiene una inconsistencia menor en el campo de reintento

La guía usa `isRetryable` en las líneas 237 y 616, pero `retriable: false` en la línea 238. El proyecto estandariza `isRetryable` y documenta la diferencia. No se considera una falla del proyecto. Conviene conservar una nota que indique que el concepto evaluable es distinguir errores reintentables y no reintentables, no memorizar una grafía aislada.

## 5. Contradicciones internas independientes del estado incompleto

### MEDIA — C-01. La tabla de `app3/08` atribuye objetivos que siguen asignados a `app3/11` ✅ TERMINADO 2026-11-06

`app3_sistema_multiagente/README.md:20` muestra TS 4.4-K1…K4 y S1…S4. Sin embargo, `CONCEPTOS.md` asigna K3 y S3 a `app3/11_criterios_y_ci`, todavía pendiente. El código de `08_validacion_reintento.py` solo marca K1, K2, K4, S1, S2 y S4.

Esto no depende de que el proyecto esté terminado: la tabla del módulo entregado describe de manera inexacta lo que ese módulo introduce.

### MEDIA — C-02. La ruta principal de app3 quedó atrasada ✅ TERMINADO 2026-11-06

`README.md:40-44` resume app3 como `01`→`03`, aunque su README ya entrega `01`→`09`. Es deriva documental, no un problema de cobertura.

### MEDIA — C-03. `app3/CLAUDE.md` contiene hechos obsoletos ✅ TERMINADO 2026-11-06

- Declara nueve fuentes, mientras el generador y los datos contienen diez.
- Afirma que el estado de `app3/06` vive en un directorio temporal externo. El módulo lo guarda por defecto bajo `estado/<perfil>/app3-06/`, ignorado por Git, y solo queda fuera del clon cuando se configura `CCARF_ESTADO_DIR`.

Como `CLAUDE.md` condiciona cambios futuros, estos errores tienen más impacto que una descripción histórica ordinaria.

### MEDIA — C-04. Credenciales y modo ligero no usan una definición uniforme

La portada dice que toda ejecución con modelo necesita API key. El arnés diferencia:

- Agent SDK, que puede funcionar con la suscripción o el login de Claude Code;
- Messages API y Batches, que requieren API key.

También se afirma que sin clave se puede hacer el recorrido ligero, pero cuatro módulos entregados se marcan como ejecución obligatoria. La intención pedagógica es comprensible, pero «obligatoria» y «recorrido sin coste» quedan en tensión.

**Mejora recomendada:** una matriz por módulo con: sin credencial, suscripción, API key, ejecución opcional/obligatoria y alternativa de referencia.

### BAJA — C-05. La estimación uniforme de tiempo no representa algunos módulos

La portada indica unos 10 minutos sin ejecutar y 25 ejecutando variantes. Los módulos densos y Batches se alejan mucho de esa referencia. Conviene estimar por parte o por ruta, no por módulo completo.

## 6. Evaluación didáctica

### Fortalezas

1. **Recuperación activa.** Se pide predecir antes de mostrar resultados.
2. **Retroalimentación diferida.** Los contrastes y respuestas están plegados.
3. **Metacognición.** `FALLOS.md` convierte errores en material de repaso.
4. **Comparación con anti-patrones.** La mayoría de conceptos se aprende por contraste y no solo por definición.
5. **Datos sintéticos y reproducibles.** El estudiante puede experimentar sin información real.
6. **Separación frecuente de fuentes.** Muchos módulos distinguen guía, inferencia y observación del producto.
7. **Honestidad experimental.** Cuando una señal no aparece, el proyecto lo registra en vez de inventarla.
8. **Infraestructura comprobable sin coste.** La suite valida handlers, hooks, schemas, rutas y presupuesto sin invocar modelos.
9. **Progresión arquitectónica.** Agente único → controles → multiagente es una secuencia clara.

### Construcciones que reducen la eficacia

#### D-01. Demasiados objetivos dentro de una sola unidad de recuperación

`app3/05` introduce 14 objetivos, `app3/07` introduce 13 y `app3/01` introduce 12. Sin embargo, cada módulo suele cerrar con una sola pregunta. El estudiante puede acertarla y seguir sin dominar buena parte de las viñetas.

**Mejora:** mantener un script compartido, pero dividir su recorrido en microlecciones. Cada subgrupo debería tener su propia predicción, contraste y comprobación.

#### D-02. Algunas ejecuciones probabilísticas no muestran el mecanismo

En distintos módulos se registran variantes sin señal o con una señal contraria a la esperada. Esto es científicamente honesto, pero didácticamente costoso: el alumno ejecuta para observar un efecto y recibe una tabla histórica o una explicación de por qué no ocurrió.

**Mejora:** clasificar cada parte como:

- demostración determinista;
- observación probabilística con control positivo;
- explicación conceptual sin señal estable.

Solo la primera debería ser obligatoria para comprender el mecanismo.

#### D-03. Se mezcla certificación, comportamiento actual del producto y diseño de producción

Las marcas `EN PRODUCCIÓN (no evaluable)` ayudan, pero algunos contenidos siguen dentro de las mismas preguntas, tablas y comandos que el material evaluable. `app2/07` es el caso extremo.

**Mejora:** separar visual y estructuralmente tres carriles:

- **Examen v1.0**;
- **Producto observado en versión X**;
- **Diseño de producción adicional**.

#### D-04. D3 concentra demasiada materia en pocas comprobaciones

Hay 40 objetivos D3 ya introducidos, pero la sección usa tres preguntas finales y queda fuera del narrador de módulos. La práctica operacional es valiosa, aunque la recuperación explícita por objetivo es menor que en las apps.

**Mejora:** dividir D3 por TS y añadir una comprobación corta por 3.1–3.5.

#### D-05. El recorrido ligero puede sustituir práctica que la guía considera experiencial

La guía describe un candidato con seis meses o más de experiencia y recomienda construir agentes, configurar Claude Code, diseñar MCP y probar extracción. El modo ligero es útil para repasar, pero no debería presentarse como equivalente completo a la práctica.

**Mejora:** distinguir «preparación conceptual sin coste» de «competencia práctica demostrada».

## 7. Trazabilidad

### Lo comprobado

- La fuente oficial contiene 30 Task Statements y 240 objetivos: 113 K y 127 S.
- `CONCEPTOS.md` contiene los mismos recuentos y rangos por TS.
- El contador de 190 coincide con las filas marcadas.
- Los marcadores `INTRODUCE` actuales son únicos según el escáner.
- Los `USA` apuntan a objetivos ya introducidos.
- Los pesos por dominio coinciden con el blueprint.

### Lo que los tests no comprueban

- Que una paráfrasis conserve todos los matices del objetivo oficial.
- Que el ejercicio demuestre cada objetivo que marca.
- Que la pregunta evalúe todos los objetivos del módulo.
- Que la respuesta y los distractores se mantengan dentro del blueprint.
- Que las tablas de README coincidan con `CONCEPTOS.md`; `app3/08` demuestra esa brecha.
- Que una funcionalidad no listada en `perimetro_excluido.yaml` esté realmente dentro de alcance.

La métrica correcta es **trazabilidad estructural de 190 objetivos**, no todavía validación semántica exhaustiva de esos 190.

## 8. Tratamiento de temas oficialmente fuera de alcance

La guía excluye, entre otros, autenticación, OAuth, precios de API y métricas comparativas entre modelos.

No todo uso de uno de esos mecanismos constituye una falla:

- `harness/credentials.py` debe detectar una credencial para poder ejecutar los ejercicios. Es infraestructura, no materia evaluable.
- Mostrar un presupuesto aproximado ayuda a que el estudiante no incurra en costes inesperados.
- La reducción del 50 % de Batches sí aparece expresamente dentro de TS 4.5, aunque las tablas de precios concretos no sean evaluables.

La regla útil no debería ser «el repositorio nunca contiene nada fuera de alcance», porque una aplicación ejecutable necesita infraestructura. Debería ser:

> Ningún contenido fuera de alcance determina una respuesta tipo examen ni se presenta como conocimiento que el candidato deba memorizar. La infraestructura adicional queda separada y rotulada.

Con esa formulación, credenciales y presupuestos son aceptables; `app2/07`, `app2/03` y las comparaciones de modelos requieren revisión.

## 9. Hoja de ruta recomendada

### P0 — corregir alineación antes de añadir más contenido

1. Resolver la contradicción de strict mode en `app3/07`.
2. Sacar `updatedInput` del carril evaluable o reformular su pregunta.
3. Reclasificar `app2/03` como soporte operativo sin pregunta tipo examen.
4. Cambiar la descripción del test de perímetro para que no prometa exhaustividad.
5. Corregir la fila de `app3/08`.

### P1 — fortalecer la preparación para el examen

1. Añadir preguntas multiple-response.
2. Crear prácticas acumulativas basadas en los seis escenarios.
3. Mantener siempre la terminología oficial junto a la terminología actual del producto.
4. Añadir un manifiesto por objetivo: fuente oficial, paráfrasis, ejercicio, pregunta, respuesta y evidencia de revisión.
5. Revisar manualmente, contra la guía, cada tanda antes de marcarla como cerrada.

### P1 — mejorar navegación y requisitos

1. Actualizar la ruta raíz hasta app3/09.
2. Corregir los hechos obsoletos de `app3/CLAUDE.md`.
3. Publicar la matriz de credenciales, coste y modo por módulo.
4. Separar tiempos de lectura, ejecución síncrona y espera externa.

### P2 — mejorar retención

1. Dividir módulos densos en checkpoints.
2. Añadir microcasos por grupo de objetivos.
3. Incluir repaso espaciado entre apps.
4. Crear pruebas mixtas por dominio y escenario.
5. Balancear posiciones de respuesta sin convertir la posición en una pista.

### P2 — estabilizar demostraciones

1. Preferir mecanismos deterministas para la lección principal.
2. Exigir controles positivos cuando se use una métrica textual.
3. Mover comparaciones históricas de modelos a material experimental.
4. Registrar versión de modelo, SDK, CLI y fecha solo cuando el comportamiento del producto sea relevante.

### P3 — completar el proyecto

Completar las tandas C y D según el plan existente. Esto no corrige una falla: cumple la meta pendiente. Al llegar a 240/240:

1. retirar el `xfail` solo cuando la cobertura estructural pase;
2. ejecutar una revisión semántica final contra esta versión concreta de la guía;
3. revisar de nuevo el perímetro;
4. realizar una prueba completa del narrador con una persona;
5. preparar al menos una simulación con cuatro escenarios y preguntas de ambos formatos.

## 10. Conclusión

El proyecto incompleto no es un proyecto fallido. Su avance de 190/240 está planificado y controlado. La arquitectura didáctica y la infraestructura de pruebas son buenas, y la correspondencia numérica con la Exam Guide es correcta.

Las mejoras prioritarias están en la frontera entre guía y producto. El caso de strict mode enseña como no evaluable algo que la guía sí nombra. Los módulos de permisos y `updatedInput` hacen lo contrario: llevan al formato de examen conocimientos que el blueprint no respalda. Las comparaciones entre modelos también deben quedar fuera del núcleo porque la guía las excluye expresamente.

Una vez corregida esa frontera, el mayor salto didáctico vendrá de practicar multiple-response, organizar simulaciones por escenario y dividir los módulos densos en unidades de recuperación más pequeñas. El proyecto podrá completar las 50 viñetas restantes sin rebajar su criterio y llegar a 240/240 con una alineación más fácil de auditar.