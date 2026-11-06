<!--
PROPÓSITO: plantilla de la sección de un módulo en el `README.md` de su app (roadmap §13, reglas 1–5).
Se copia bajo `## NN · Título` y se rellena. Lo común (tool, iteración, `stop_reason`, historial,
hook, deny con motivo, modo ligero…) NO se repite aquí: se enlaza a docs/glosario.md
y se amplía solo con términos propios.
El orden sigue el ciclo de §13 y los 5 pasos de «Empieza aquí» del README raíz: la ficha orienta,
se predice antes de ver los comandos y la salida, y cada bloque plegado dice a qué paso pertenece.
`tests/test_readme_modulos.py` exige la ficha, «Antes de empezar», el orden Predice → Ejecutar,
los `summary` de los pasos 3 y 4, la línea del paso 5 y «Pregunta tipo examen».
Borra estos comentarios al rellenar.
-->

> **Qué vas a hacer:** la tarea en una frase, sin su resultado.
>
> **Necesitas antes:** nada, o el módulo del que depende, con enlace ([módulo 01](#01--titulo)).
>
> **Modo:** ejecución ligera (puedes hacerlo entero sin ejecutar) | ejecución obligatoria (hay que ejecutarlo: por qué).

### Antes de empezar

<!-- Solo lo propio de este módulo; explica qué HACE el código, nunca qué ocurre al ejecutarlo
ni qué valor toma una señal que se pide predecir. -->

- **El sistema:** qué hace este módulo y sobre qué datos sintéticos trabaja.
- **Términos propios:** los que no están en [`docs/glosario.md`](../docs/glosario.md).

### Las tools del ejercicio

<!-- Omite esta sección si el módulo no usa tools. -->

| Tool | Qué recibe | Qué devuelve |
| :--- | :--- | :--- |
| `nombre_tool` | parámetros | resultado |

### El ejercicio

Qué se le pide al agente y qué cambia en cada variante `--anti` (descripción del código de cada variante, sin su resultado):

- **`variante_a`:** qué hace distinto el código.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

<!-- Pide patrones, rangos o invariantes (lo igual en cualquier ejecución y lo que varía), no un valor
que el modelo pueda variar. No preguntes lo que el contexto ya responde («Antes de empezar», las tablas de tools, «El ejercicio»):
si una respuesta se lee tal cual, quítala o llévala a «Qué observar». -->

1. Pregunta sobre un patrón o un rango.

### Ejecutar

```bash
uv run python appN_nombre/NN_concepto.py            # correcta
uv run python appN_nombre/NN_concepto.py --anti ... # variante construida mal
```

**Si ejecutas:** para qué sirve ejecutar (qué se ve que no se ve leyendo). En los de ejecución obligatoria, por qué hay que hacerlo. Si el tope de `--budget` puede romper la medida, dilo aquí.

<!-- Modo normal (§13): sugiere aquí un parámetro que cambiar para ver qué se rompe. -->

### Qué observar

Qué señal mirar en la salida, sin dar aquí el resultado.

<details>
<summary>Paso 3 · Contrastar: lo que se observó (ábrelo después de predecir)</summary>

Lo medido con modelo (modelo y fecha), lo estable frente a lo que varía y las notas.
</details>

### Pregunta tipo examen

Enunciado, opciones de longitud y registro parejos (la correcta no siempre en la misma posición).

<details>
<summary>Paso 4 · Respuesta</summary>

**X.** Por qué, con las viñetas.
</details>

<!-- Variante multiple-response (opcional; obligatoria si el módulo introduce 10 o más viñetas; el examen real mezcla los dos formatos). Se añade DESPUÉS de la
pregunta de respuesta única, dentro de esta misma sección `### Pregunta tipo examen`, con su propio «Paso 4».
Si la añades, etiqueta la primera como «**Pregunta 1 (una respuesta).**». Reglas, que comprueba
`tests/test_readme_modulos.py`:
- El enunciado dice cuántas elegir con «**Selecciona dos**» (o tres, cuatro), siempre declarado.
- Al menos una opción más que las que hay que elegir y como máximo cuatro, el límite de `AskUserQuestion` con el
  que `practica-guiada` la plantea (lo habitual: cuatro opciones, dos correctas).
- El `summary` empieza por «Paso 4 · Respuesta» (p. ej. «Paso 4 · Respuesta (pregunta 2)») y el cuerpo, por
  «**A y C.**» con las letras correctas.
- El cuerpo justifica cada opción por separado con una viñeta `- **A** …`, también las incorrectas.
- Cada opción se puede juzgar sola: ninguna depende de otra ni el enunciado empareja opciones con problemas.

**Pregunta 2 (multiple-response).** Escenario. **Selecciona dos** … Evalúa cada opción por separado.

- A. …
- B. …
- C. …
- D. …

<details>
<summary>Paso 4 · Respuesta (pregunta 2)</summary>

**A y C.** Resumen de por qué.

- **A** …
- **B** …
- **C** …
- **D** …
</details>
-->

**Paso 5 ·** Si fallaste una predicción o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).
