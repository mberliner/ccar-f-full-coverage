Eres una instancia independiente y no tienes contexto previo. Revisa las correcciones de la tanda B de la entrega 3 de este repositorio. No edites nada: informa de los hallazgos ordenados por gravedad, con archivo y línea en cada uno. Sé breve: esto es una segunda revisión, centrada en lo que se corrigió.

Qué revisar: `git diff 6ec934e..entrega-3b`, que contiene las correcciones de código, datos y textos de `app3_sistema_multiagente/04_errores_entre_agentes.py`, `05_procedencia.py` y `06_contexto_largo.py`, sus secciones en `app3_sistema_multiagente/README.md`, `servers/investigacion.py`, los tests, `datos/generar_sinteticos.py`, `docs/glosario.md`, `docs/hallazgos.md`, `docs/diseno-entrega-3.md` y `NOTAS.md`. La lista de lo que pidió la revisión anterior está en `docs/prompts-entrega-3/b4-correcciones-codigo.md` y en la entrada «Correcciones de B4» de `NOTAS.md`.

Las reglas están en `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md` y `.claude/rules/`. La guía es la Exam Guide (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio), TS 5.3, 5.4, 5.6, 5.1 (K2, S4–S6), 2.2-S3 y 1.3-S2.

Comprueba:

1. **`generico` en `04`:** que reintente igual que la correcta y solo cambie el mensaje final, y que la cabecera, el Paso 3, la predicción 3 y la pregunta tipo examen digan lo que se midió (sin efecto sobre el coordinador) sin presentarlo como lo que dice la guía.
2. **Viñetas que antes no se ejercitaban:** 5.3-S3 (fuente transitoria), 5.6-S1 y 5.1-S5 (ubicación y fragmento), 5.6-S3 (decide el coordinador), 5.6-S5 (`formato_uniforme`) y 5.1-S6 (relevancia y salida verbosa). ¿Las ejercita ahora el código? ¿Dice la cabecera lo que no dio señal?
3. **Medidas corregidas:** `gap_noted`, `partial_delivered`, `swallowed_sources` y las vacías legítimas en `04`; `conflicts_presented`, `explanation_found`, `merged_figures` y `sources_passed` en `05`. Busca un caso que siga fallando y comprueba que el README advierte lo que queda laxo.
4. **`06`:** *manifest* roto, de otra versión, con tipos o claves erróneos, que no cuadra con el *scratchpad*, y *scratchpad* con la última línea cortada. ¿Queda algún caso que lance una excepción sin capturar? ¿El estado va bajo `estado/<perfil>/`?
5. **Cifras:** que la cabecera, el README, `docs/hallazgos.md` y `NOTAS.md` coincidan, y que las mediciones de antes de las correcciones estén siempre marcadas como anteriores.
6. **Didáctica:** que el «Antes de empezar» no adelante resultados, que las predicciones sean por patrón, y que en las preguntas de `04`–`07` las cuatro opciones sean plausibles, de longitud parecida, sin que la correcta sea la única con el vocabulario de la guía.
7. **`→ roadmap`:** en la tanda B de `docs/hallazgos.md` solo debería quedar «toda medida de cifras debe aceptar `x/5`». ¿Sobra o falta alguna?

Puedes ejecutar `uv run pytest -q`. No ejecutes nada que llame al modelo.
