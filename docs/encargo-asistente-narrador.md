# Encargo · asistente que narra un módulo

**Estado:** pendiente, fuera del Hito T. Es un encargo, no un diseño: el diseño se hace en su propia sesión, en plan mode, partiendo de aquí. Escrito el 2026-11-01.

## Por qué

En la prueba de usabilidad del Hito T (`docs/prompts-hito-t/paso8-informe-resultado.md`), una participante que llegaba de cero puntuó su autonomía con un 2/7 y dijo: «no tener un contexto general de qué estamos haciendo; debería ser narrado por un asistente y no leído a trompicones».

La corrección de orientación del mismo hito ya resolvió parte del problema en el texto. Este encargo no la repite: se apoya en ella.
- «Empieza aquí» en el `README.md` raíz: qué es un módulo y el ciclo en 5 pasos.
- Una ficha al principio de cada módulo: qué vas a hacer, qué necesitas antes y el Modo.
- Bloques plegados con nombre de paso («Paso 3 · Contrastar», «Paso 4 · Respuesta») y la línea «Paso 5» hacia `FALLOS.md`.

Lo que el texto no puede dar es **acompañamiento**: que alguien te diga qué toca ahora, espere tu predicción y te avise de cuándo abrir cada bloque.

## Qué debe hacer

Un comando o una skill de proyecto, por ejemplo `/estudiar appN/NN`, que lleve a la persona por los 5 pasos de la ficha de un módulo:
1. Presentar la ficha y el contexto del módulo («Antes de empezar», «El ejercicio») con sus palabras y sin añadir nada que no diga el README.
2. Pedir las predicciones en texto libre y no seguir hasta tenerlas.
3. Según el Modo, proponer el comando que hay que ejecutar o el contraste sin ejecutar, y decir cuándo abrir «Paso 3 · Contrastar».
4. Plantear la pregunta tipo examen y, después de la respuesta de la persona, indicar que abra «Paso 4 · Respuesta».
5. Ofrecer, al final, la fila de `FALLOS.md` (`estado/<perfil>/`) con lo que falló, para que la persona la confirme.

## Restricciones

- **No revela antes de tiempo** el resultado de referencia ni la respuesta. Es el mismo riesgo por el que `promptSuggestionEnabled` está apagado (`docs/estandares-flujo.md`, «Ejercicios de evaluación»).
- Las predicciones van en texto libre. Las opciones múltiples se reservan para el formato de examen (mismo documento).
- Solo lectura sobre el repositorio. La única escritura posible es el estado personal, y solo con la confirmación de la persona.
- Dentro del perímetro de la guía: comandos y skills de proyecto son de TS 3.2, sin mecanismos que la guía no nombre.
- Lo común no se duplica: el asistente lee la plantilla y el README del módulo, no lleva una copia propia del contenido.

## Preguntas abiertas para su plan mode

- ¿Comando o skill? ¿Encaja `context: fork` con una conversación interactiva? (`docs/hallazgos.md` registra que la skill con fork corre en segundo plano y devuelve un informe.)
- ¿Cómo se impide que lea o cite el contenido de los `<details>` antes de tiempo: con una instrucción, con `allowed-tools` o leyendo la sección por partes? ¿Cómo se comprueba?
- ¿Ejecuta el módulo o solo propone el comando? (Coste, `--budget` y la credencial.)
- ¿Sustituye a la lectura o la acompaña?
- ¿Cómo se registra su uso en la sección D3, si introduce o usa alguna viñeta? (Regla «una vez».)

## Cómo se valida

Por decisión de la persona, no hay una prueba de usabilidad previa al diseño. Al terminar, se hace una prueba con una persona usando el guion `docs/prompts-hito-t/paso8-prueba-usuario.md` en modo narrado, con los mismos dos casos o con otros dos al azar. Después, una revisión por una instancia independiente.

## Cómo arrancar

```bash
claude -n narrador
```

En plan mode, leer primero este encargo, el informe de la prueba, `plantillas/modulo/README.md` y «Empieza aquí» en el `README.md` raíz.
