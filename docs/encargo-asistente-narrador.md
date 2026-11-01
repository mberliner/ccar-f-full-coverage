# Encargo · asistente que narra la práctica (`/practica-guiada`)

**Estado:** pendiente, fuera del Hito T. Es un encargo, no un diseño: el diseño se hace en su propia sesión, en plan mode, partiendo de aquí. Escrito el 2026-11-01; decisiones del análisis incorporadas el mismo día.

## Por qué

En la prueba de usabilidad del Hito T (`docs/prompts-hito-t/paso8-informe-resultado.md`), una participante que llegaba de cero puntuó su autonomía con un 2/7 y dijo: «no tener un contexto general de qué estamos haciendo; debería ser narrado por un asistente y no leído a trompicones».

La corrección de orientación del mismo hito ya resolvió parte del problema en el texto. Este encargo no la repite: se apoya en ella.
- «Empieza aquí» en el `README.md` raíz: qué es un módulo y el ciclo en 5 pasos.
- Una ficha al principio de cada módulo: qué vas a hacer, qué necesitas antes y el Modo.
- Bloques plegados con nombre de paso («Paso 3 · Contrastar», «Paso 4 · Respuesta») y la línea «Paso 5» hacia `FALLOS.md`.

Lo que el texto no puede dar es **acompañamiento**: que alguien te diga qué toca ahora, espere tu predicción y te avise de cuándo abrir cada bloque.

## Qué debe hacer

Una skill de proyecto, `/practica-guiada`. El objetivo son los conceptos del examen; el módulo es el medio. La experiencia es narrada de principio a fin: abrir el README o el script queda como opción de la persona, no como paso.

- **Sin argumento:** muestra un menú con todo lo disponible, sacado de las tablas «Ruta de lectura» de cada app, con el primer módulo recomendado marcado y una entrada «Puesta en marcha».
- **Puesta en marcha (desde cero):** comprueba `uv`, que existe `.env` (solo que existe: su lectura está denegada) y el estado personal (`harness.estado init`), y dice qué hacer con lo que falte. El paso previo, abrir `claude` en el repositorio y escribir `/practica-guiada`, va en una línea de «Empieza aquí».
- **Con un módulo,** lleva a la persona por los 5 pasos:
  1. Narra la ficha, «Antes de empezar» y «El ejercicio». Explica con sus palabras, apoyándose en `docs/glosario.md` y en «Empieza aquí».
  2. Pide las predicciones en texto libre y no sigue hasta tenerlas.
  3. Según el Modo, propone el comando, que la persona lanza con `! uv run python …` para que la salida llegue a la conversación, o hace el contraste sin ejecutar. Después narra «Paso 3 · Contrastar» y lo compara con la predicción. Quién decide si falló es la persona.
  4. Plantea la pregunta tipo examen con `AskUserQuestion`: opciones en el orden del README, ninguna marcada como recomendada; «Other» sirve para responder con sus palabras. Después narra «Paso 4 · Respuesta».
  5. Propone la fila de `FALLOS.md` (`estado/<perfil>/`, formato de `plantillas/estado/`) y la escribe solo con confirmación explícita en texto.
- **Dependencias:** si la ficha dice «Necesitas antes» (app1/05, app2/02, app2/06, app3/02, app3/03), pregunta si se hizo el módulo previo y ofrece ir a él o seguir. No bloquea: ningún script depende de otro para ejecutarse.

## Restricciones

- **No revela antes de tiempo** el resultado de referencia ni la respuesta. Es el mismo riesgo por el que `promptSuggestionEnabled` está apagado (`docs/estandares-flujo.md`, «Ejercicios de evaluación»).
- Las predicciones van en texto libre. Las opciones múltiples se reservan para el formato de examen (mismo documento).
- Solo lectura sobre el repositorio. La única escritura posible es el estado personal, y solo con la confirmación de la persona.
- Dentro del perímetro de la guía: comandos y skills de proyecto son de TS 3.2, sin mecanismos que la guía no nombre.
- Lo común no se duplica: el asistente lee la plantilla y el README del módulo, no lleva una copia propia del contenido.

## Decisiones tomadas (2026-11-01)

- **Skill sin `context: fork`:** con fork corre en segundo plano y devuelve un informe (`docs/hallazgos.md`); el narrador necesita conversar. Skill y no comando porque puede llevar archivos de apoyo.
- **La revelación la controla un script por fases**, no `allowed-tools` ni una instrucción sola. Un script del arnés sin modelo (p. ej. `harness/narrador.py`) resuelve `appN/NN` a la carpeta real y entrega el módulo por fases: `ficha`, `ejercicio`, `pregunta`, `contraste`, `respuesta`. Las previas a la respuesta no llevan el contenido de los `<details>` que aún no toca. La skill solo lo llama a él y no lee el `README.md` ni el `.py` del módulo antes del paso 4 (la cabecera del `.py` puede dar la respuesta).
- **Por qué no `allowed-tools`:** en una skill sin fork preautoriza las tools listadas, pero no restringe las demás (comprobado; ver `docs/hallazgos.md`). Sí se aprovecha para la escritura: `Write` no va en `allowed-tools`, así la sesión interactiva pide permiso antes de tocar `FALLOS.md`.
- **No ejecuta el módulo:** lo propone y la persona decide el gasto (`--budget`, `--repeat`).
- **D3:** las viñetas de TS 3.2 ya están introducidas; la skill solo lleva `USA: TS 3.2-K1, TS 3.2-S1` (y `K2`, `S3` si usa frontmatter con `allowed-tools`). Sin cambios en `CONCEPTOS.md`.
- **Prueba sin modelo, antes del módulo:** un test del script comprueba, en todos los módulos, que ninguna fase previa contiene el texto de los bloques plegados.

## Cómo se valida

Por decisión de la persona, no hay una prueba de usabilidad previa al diseño. Al terminar, se hace una prueba con una persona usando el guion `docs/prompts-hito-t/paso8-prueba-usuario.md` en modo narrado, con los mismos dos casos o con otros dos al azar. Después, una revisión por una instancia independiente.

## Cómo arrancar

```bash
claude -n narrador
```

En plan mode, leer primero este encargo, el informe de la prueba, `plantillas/modulo/README.md` y «Empieza aquí» en el `README.md` raíz.
