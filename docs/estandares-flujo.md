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

- `NOTAS.md`: avance de todos los hitos (el roadmap es una plantilla y no lo lleva), *scratchpad* de sesión y notas de producto no evaluables.
- Mejoras para el roadmap: una nota que le pasaría también a otra persona, con otra máquina y otra cuenta, se marca `→ roadmap`. Al llevarla al roadmap (sección afectada o §4.3, más una línea en §14) se reduce aquí a un puntero `✓ roadmap YYYY-MM-DD §x`, para no duplicarla. Las que dependen de esta implementación o aún no se han comprobado se quedan solo aquí (criterio en roadmap §12, «Mantener la plantilla al día»).
- `FALLOS.md`: predicciones y respuestas fallidas.
- Las notas son siempre agnósticas: rutas relativas al proyecto o genéricas (`~/.claude/…`), sin rutas absolutas, sin nombres de personas, cuentas ni perfiles.
- `CLAUDE.md` y estos estándares solo cambian cuando cambia una regla estable.

## Ejercicios de evaluación

- Las sugerencias de entrada de Claude Code (`promptSuggestionEnabled`) están desactivadas en `.claude/settings.json`, porque pueden proponer la respuesta correcta de un ejercicio. Una configuración local o una variable de entorno pueden anularlo: el repositorio fija el valor por defecto y no puede impedirlo.
- Las predicciones se piden en texto libre. Las opciones múltiples se reservan para practicar el formato de examen.
- Las opciones tienen la misma longitud y registro, y la correcta no ocupa siempre la misma posición.

## Revisión

- La revisa una instancia independiente, nunca la sesión que escribió el código.
