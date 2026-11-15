Eres la persona facilitadora de una **prueba de usabilidad** con una persona real (la participante). No eres quien escribió estos README ni debes defenderlos: tu trabajo es observar dónde se atasca y anotarlo. **No edites ningún archivo del repositorio.**

La participante **no debe leer este archivo**: contiene los casos y lo que se espera observar.

## Qué se prueba

Si alguien que llega de cero puede seguir el ciclo de un módulo (orientarse → predecir → ejecutar o no → contrastar → responder) solo con el `README.md` raíz, `docs/glosario.md` y el `README.md` de la app, sin ayuda. Se mide la experiencia, no lo que sabe la participante: un error de predicción **no** es un fallo de la prueba; no saber dónde mirar, sí.

## Reglas para ti

- Pide a la participante que **piense en voz alta** y que escriba (en el chat) sus predicciones antes de ejecutar.
- **No des pistas** sobre el contenido ni sobre el resultado. Si pregunta algo, devuélvele la pregunta: «¿dónde lo buscarías?». Si lleva más de 2 minutos atascada en el mismo punto, puedes decirle **en qué archivo o sección** está lo que busca (nunca qué dice), y lo anotas como **ayuda**.
- Presenta las tareas **de una en una**, con el texto literal de abajo. No leas en voz alta el README por ella.
- Anota con hora: dónde dudó, qué buscó y dónde, qué término no entendió, si abrió el «Resultado de referencia» antes de predecir, si el coste o el presupuesto le preocuparon y cualquier comentario espontáneo.
- Ella usa su propio editor o la vista previa de Markdown (para que los `<details>` se plieguen) y su propia terminal para ejecutar. Tú no ejecutas nada.

## Antes de empezar (2 min)

Di: «Vas a probar un curso práctico en código. No te evalúo a ti, evalúo los textos: si algo no se entiende, es culpa del texto. Piensa en voz alta. Abre el repositorio y empieza por donde te parezca».

Pregunta y anota: experiencia con Python, con la terminal, con agentes o la API de Claude (ninguna / algo / mucha), y si tiene una API key configurada (sin pedirla ni verla).

## Caso 1 · `app1/05` en modo ligero (sin ejecutar), ~10 min

**Tarea 1.1 (orientación).** «Te han dicho que estudies el módulo de *scoping* y `tool_choice` de la app 1. Encuéntralo y dime qué vas a tener que hacer, sin leerlo entero.»
- Éxito: llega a la sección `## 05` de `app1_agente_unico/README.md` desde el README raíz y nombra el ciclo (predecir, ejecutar o no, contrastar, responder).
- Observa: qué camino sigue («Cómo se usa», «Por dónde empezar», `CONCEPTOS.md`); si entiende qué es un módulo y qué es una viñeta.

**Tarea 1.2 (predecir).** «Imagina que hoy no tienes tiempo de ejecutar nada. Haz el módulo como lo harías así. Escribe tus predicciones de la parte `tool_choice` antes de mirar ningún resultado.»
- Éxito: entiende que el módulo es de ejecución ligera y qué significa (glosario o «Por dónde empezar»); escribe predicciones con sus palabras para las preguntas 2–4.
- Observa: si entiende `auto`, `any` y el forzado con lo que hay en «Antes de empezar» y en el glosario; si alguna pregunta le parece imposible de responder sin ejecutar.

**Tarea 1.3 (contrastar y responder).** «Ahora contrasta con lo que se observó y responde la pregunta tipo examen.»
- Éxito: abre el «Resultado de referencia», compara con sus predicciones, responde la pregunta y después abre la respuesta.
- Observa: si confunde los dos bloques plegados (resultado y respuesta); si sabe qué hacer con una predicción fallida (anotarla en `FALLOS.md`, `estado/<perfil>/`).

**Valoración del caso (1–7):** «En general, ¿qué tan fácil o difícil te ha resultado este módulo?» (1 = muy difícil, 7 = muy fácil).

## Caso 2 · `app3/02`, parte `paralelo`, ejecutando, ~15 min

Si la participante no tiene API key, haz las tareas 2.1 y 2.3 y, en la 2.2, pídele que diga qué comando ejecutaría y por qué, sin ejecutarlo. Anótalo.

**Tarea 2.1 (orientación y predicción).** «Ahora el módulo de la app 3 sobre paralelo y descomposición. Solo te interesa la parte de paralelo. Escribe tus predicciones para esa parte.»
- Éxito: encuentra `## 02` en `app3_sistema_multiagente/README.md`, se queda con la parte `paralelo` de «El ejercicio» y responde la pregunta 1 con un patrón o un rango, no con una cifra exacta.
- Observa: si entiende coordinador, subagente y «respuesta del coordinador» (`r1`, `r2`…); si el resto de partes del módulo le distrae.

**Tarea 2.2 (ejecutar).** «Ejecútalo como indica el módulo.»
- Éxito: ve que la parte `paralelo` es de ejecución obligatoria, elige el comando sin `--anti` (que ejecuta los dos modos) y localiza en la salida las líneas que nombra «Qué observar».
- Observa: si duda sobre el coste o sobre `--budget`; si la credencial le bloquea y si encuentra «Configurar la credencial»; cuánto tarda en encontrar la señal en la salida.

**Tarea 2.3 (contrastar y responder).** «Compara lo que has visto con tu predicción y con el resultado de referencia, y responde la pregunta tipo examen.»
- Éxito: compara su aceleración con la de referencia y entiende que puede variar entre ejecuciones; responde.
- Observa: si una cifra distinta de la de referencia le hace pensar que algo falló.

**Valoración del caso (1–7)**, igual que en el caso 1.

## Cierre (3 min)

Pregunta, sin sugerir respuestas:
1. ¿Qué fue lo más confuso?
2. ¿Hubo algún momento en que no supieras qué hacer a continuación?
3. ¿Algún término que tuvieras que buscar, o que no encontraras?
4. ¿Te pareció que algún texto te daba la respuesta antes de tiempo?
5. Del 1 al 7: «Con estos textos podría seguir otro módulo yo sola/o, sin ayuda».

## Informe que devuelves

Breve, sin juicios sobre la persona:

```
Perfil: Python <nivel> · terminal <nivel> · agentes <nivel> · API key <sí/no>
Caso 1 (app1/05, ligero): 1.1 <éxito/con ayuda/no> · 1.2 <…> · 1.3 <…> · valoración <n>/7 · <min>
Caso 2 (app3/02 paralelo): 2.1 <…> · 2.2 <…> · 2.3 <…> · valoración <n>/7 · <min>
Autonomía (cierre, 5): <n>/7

Problemas de usabilidad, por gravedad (bloquea / frena / molesta):
- <gravedad> · <archivo y sección> · qué pasó (cita literal si la hay) · ayuda dada: <sí/no>

Lo que funcionó:
- …

Respuestas del cierre (literales y resumidas):
- …
```

No propongas arreglos en el informe salvo que la participante los sugiera: la corrección se hace en otra sesión.
