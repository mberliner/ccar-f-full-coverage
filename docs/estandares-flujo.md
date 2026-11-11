<!--
CONCEPTO [TS 3.4-K1, K2, K3, K4, S1, S2, S3, S4]: plan mode frente a ejecución directa.
QUÉ DICE LA GUÍA: plan mode es para cambios grandes, con varios enfoques válidos,
decisiones de arquitectura o muchos archivos, y permite explorar y diseñar sin
comprometer cambios. La ejecución directa es para cambios simples y acotados. El
subagente Explore aísla la exploración verbosa y devuelve un resumen. Lo habitual
es combinar ambos: plan mode para investigar y ejecución directa para implementar.
POR QUÉ IMPORTA: elegir mal cuesta retrabajo (ejecutar sin plan un cambio
arquitectónico) o tiempo (planificar un arreglo de una línea).
ANTI-PATRÓN: decidir por el tamaño del mensaje y no por la naturaleza del cambio,
o investigar en la conversación principal hasta agotar el contexto.
INTRODUCE: TS 3.4-K1, TS 3.4-K2, TS 3.4-K3, TS 3.4-K4, TS 3.4-S1, TS 3.4-S2, TS 3.4-S3, TS 3.4-S4
-->
# Estándares de flujo de trabajo

Importado por `CLAUDE.md`. Cómo se construye el proyecto.

## Plan mode frente a ejecución directa

- **Plan mode:** diseñar cada app, y cualquier cambio que toque varios archivos o admita más de un enfoque razonable (p. ej. la capa meta o un cambio en el arnés que afecte a todos los módulos).
- **Ejecución directa:** un módulo acotado cuyo diseño ya está en el plan de la app, o un arreglo localizado con causa clara (un test que falla con su traza).
- **Combinación habitual:** plan mode para investigar y diseñar; aprobado el plan, ejecución directa módulo a módulo.
- **Subagente `Explore`:** para las fases de descubrimiento verbosas (recorrer la guía, buscar dónde se usa una viñeta en todo el repositorio). Devuelve un resumen y la conversación principal conserva su contexto.

## Construcción de módulos

- Tests primero: la lógica sin modelo se prueba con `pytest` antes de escribir el módulo, y se itera sobre los fallos.
- Módulos pequeños: un concepto por módulo, ejecutable con y sin `--anti` cuando la viñeta describe un error.
- Una sesión con nombre por app (`claude -n <app>`, `--resume <app>`).

## Directivas

- Todas las directivas del proyecto viven en el repositorio: `CLAUDE.md`, `docs/` y `.claude/`.
- Nunca van en la memoria automática ni en la configuración de usuario. Ambas dependen del directorio de configuración (`CLAUDE_CONFIG_DIR`) y de la persona, así que no llegarían a otra sesión ni a otro miembro del equipo.

## Git

- Se puede commitear directamente en `main`, sobre todo los cambios acotados.
- Un cambio grande (una app, o un cambio en el arnés o en la capa meta que afecte a varios módulos) puede hacerse en una rama y fusionarse a `main` cuando sus tests pasen.

## Registro entre sesiones

Se separa lo que es del proyecto (versionado y igual para todos) de lo que es de una persona (fuera de git).

**Versionado:**
- `NOTAS.md`: avance de todos los hitos (el roadmap es una plantilla y no lo lleva) y notas de construcción.
- `docs/hallazgos.md`: notas de producto no evaluables y hallazgos de esta implementación.
- Mejoras para el roadmap: una nota que le pasaría también a otra persona, con otra máquina y otra cuenta, se marca `→ roadmap`. Al llevarla al roadmap (sección afectada o §4.3, más una línea en §14) se reduce en `docs/hallazgos.md` a un puntero `✓ roadmap YYYY-MM-DD §x`, para no duplicarla. Las que dependen de esta implementación o aún no se han comprobado se quedan solo allí (criterio en roadmap §12, «Mantener la plantilla al día»).
- Estos documentos son siempre agnósticos: rutas relativas al proyecto o genéricas (`~/.claude/…`), sin rutas absolutas, sin nombres de personas, cuentas ni perfiles.

**Personal, fuera de git** (`estado/<perfil>/`, ignorado; plantillas en `plantillas/estado/`):
- `FALLOS.md`: predicciones y respuestas fallidas.
- `NOTAS_PERSONALES.md`: tabla de sesiones, práctica propia (`--resume`, D3) y *scratchpad*.
- Se crea con `uv run python -m harness.estado init [--perfil nombre]`, que nunca pisa lo ya escrito. Un clon puede tener varios perfiles (`CCARF_PERFIL`) y la base se puede mover con `CCARF_ESTADO_DIR`.
- Aquí no rige la regla de agnosticismo: es tuyo. Lo que le serviría a otra persona se lleva a `docs/hallazgos.md`.
- `CLAUDE.md` y estos estándares solo cambian cuando cambia una regla estable.

## Ejercicios de evaluación

- Las sugerencias de entrada de Claude Code (`promptSuggestionEnabled`) están desactivadas en `.claude/settings.json`, porque pueden proponer la respuesta correcta de un ejercicio. Una configuración local o una variable de entorno pueden anularlo: el repositorio fija el valor por defecto y no puede impedirlo.
- Las predicciones se piden en texto libre. Las opciones múltiples se reservan para practicar el formato de examen.
- **Predicciones autónomas:** cada predicción se contesta con su propio enunciado, pregunta una sola cosa, dice si evalúa la guía o un detalle del módulo y tiene su contraste en el Paso 3. El criterio completo está en `plantillas/modulo/README.md` y su forma la comprueba `tests/test_readme_modulos.py`.
- Las opciones tienen la misma longitud y registro, y la correcta no ocupa siempre la misma posición.
- **Simulaciones por escenario.** El examen agrupa las preguntas en 4 escenarios de un banco de 6. Para practicarlo, un caso (`simulaciones/E<n>_*.md`) reúne 8 a 10 preguntas con un contexto y unas restricciones compartidas, en ambos formatos. El formato está en `docs/simulaciones-por-escenario.md`, la plantilla en `plantillas/simulacion/` y el validador en `tests/test_simulaciones_formato.py`: un caso nuevo lo pasa antes de cerrarse. Al cerrar una tanda se actualiza el estado de preparación de los escenarios.
- **Tipo de señal de cada parte.** No toda ejecución con modelo muestra el mecanismo, así que cada parte de un módulo se clasifica en `docs/tipos-de-senal.md` como `Determinista` (no depende de lo que decida el modelo: se ve sin él o sale igual cada vez), `Probabilística con control positivo` (depende del modelo y hay una señal medida, con la variante correcta frente al anti-patrón), `Sin señal estable` (el efecto no apareció o es inestable, y la lección es conceptual) o `Sin medir` (la variante está implementada y se prueba sin modelo, pero el Paso 3 no recoge ninguna medida con modelo: no se sabe si su efecto se ve y ejecutarla es explorar). Una parte de ejecución obligatoria tiene que enseñar algo: ser determinista o mostrar una señal. Lo comprueba `tests/test_tipos_de_senal.py`. Un módulo nuevo añade sus filas al cerrarse.
- **Un modelo es un banco de pruebas, no la lección.** La guía deja fuera de alcance las comparaciones entre modelos. El Paso 3 de un módulo muestra cada variante con el modelo en que su señal se ve (una fila por modelo y variante, con «modelo de la medida»), pero no enfrenta dos modelos en una misma fila o cabecera de tabla; lo comprueba `tests/test_sin_comparacion_de_modelos.py`. Las comparaciones, los costes por modelo y la calibración van a `docs/hallazgos.md`, y el README remite allí. No se quita ninguna señal: si solo se ve con un modelo, ese es el de la medida.
- **Formatos de pregunta:** el examen mezcla respuesta única y multiple-response, así que se practican los dos. La multiple-response declara siempre cuántas elegir («**Selecciona dos**»), lleva al menos una opción más que las que hay que elegir y como máximo cuatro (el límite de `AskUserQuestion`), cada opción se puede juzgar sola y la respuesta justifica cada una. Va después de la de respuesta única, en la misma sección del módulo; el formato exacto está en `plantillas/modulo/README.md` y lo comprueba `tests/test_readme_modulos.py`. Es obligatoria en los módulos que introducen 10 o más viñetas (`DENSE_MIN` en `tests/test_readme_modulos.py`), así que los módulos densos de las tandas C y D (`app2/04`, `app3/11`) nacen sujetos a ella; en los demás es opcional.

## Revisión

- La revisa una instancia independiente, nunca la sesión que escribió el código.
