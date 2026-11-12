<!--
PROPÓSITO: plantilla de la sección de un módulo en el `README.md` de su app (roadmap §13, reglas 1–5).
Se copia bajo `## NN · Título` y se rellena. Lo común (tool, iteración, `stop_reason`, historial,
hook, deny con motivo, modo ligero…) NO se repite aquí: se enlaza a docs/glosario.md
y se amplía solo con términos propios.
El orden sigue el ciclo de §13 y los 5 pasos de «Empieza aquí» del README raíz: la ficha orienta,
se predice antes de ver los comandos y la salida, y cada bloque plegado dice a qué paso pertenece.
`tests/test_readme_modulos.py` exige la ficha, «Antes de empezar», el orden Predice → Ejecutar,
los `summary` de los pasos 3 y 4, la línea del paso 5, «Pregunta tipo examen» y la forma de las
predicciones (marca `(guía)` o `(módulo)`, dos interrogantes como máximo y su `**Pn**` en el Paso 3).
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

<!-- Da a cada variante y a cada tipo de caso una etiqueta corta (V1, V2…; T1, T2…) y úsala después.
«La correcta» nunca es un nombre: suena a «la respuesta correcta». Si una predicción menciona una
línea de la salida, lista aquí esas líneas con una frase cada una. -->

- **V1 · `variante_a`:** qué hace distinto el código.

### Predice antes de ejecutar

Con tus palabras; no hay un número que acertar:

<!-- Pide patrones, rangos o invariantes (lo igual en cualquier ejecución y lo que varía), no un valor
que el modelo pueda variar. No preguntes lo que el contexto ya responde («Antes de empezar», las tablas de tools, «El ejercicio»):
si una respuesta se lee tal cual, quítala o llévala a «Qué observar».

CRITERIO DE PREDICCIONES AUTÓNOMAS (lo comprueba `tests/test_readme_modulos.py` en lo que es de forma):
1. Autónoma: se contesta con su propio enunciado y con las etiquetas definidas justo antes, sin buscar
   en otra parte de la ficha ni abrir un archivo. Los datos que hagan falta van en el enunciado.
2. Una cosa por predicción: dos interrogantes como máximo («qué pasa y por qué»). Si junta más, se parte.
3. Marcada: empieza por `(guía)` si evalúa un concepto de la guía, o por `(módulo)` si evalúa un detalle
   de este ejercicio (un parámetro elegido aquí, una línea de la salida, un comportamiento del producto).
   Solo un fallo en una `(guía)` se anota en `FALLOS.md`.
4. Contrastable: el Paso 3 responde cada una con una entrada `- **Pn** …`, en el mismo orden. Si solo
   se puede contrastar ejecutando otra variante u otro modelo que el módulo no trae, no es una
   predicción: va a «Para pensar», al final del Paso 3, sin evaluación.
-->

1. (guía) Pregunta sobre un patrón o un rango.
2. (módulo) Pregunta sobre un detalle de este ejercicio.

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

**Tus predicciones:**

- **P1** Respuesta a la predicción 1, con la viñeta si es `(guía)`.
- **P2** Respuesta a la predicción 2.

Lo medido con modelo (modelo y fecha), lo estable frente a lo que varía y las notas. Clasifica cada parte por tipo de señal en `docs/tipos-de-senal.md` (determinista, probabilística con control positivo o sin señal estable). Una fila por variante y modelo, con el «modelo de la medida»: no se enfrentan dos modelos en una misma fila o cabecera (las comparaciones van a `docs/hallazgos.md`). Lo que hace hoy el producto y la guía no dice se rotula **Producto observado (no evaluable)**; una práctica adicional que la guía no nombra, **EN PRODUCCIÓN (no evaluable)** (carriles en `docs/estandares-codigo.md`).
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

<!-- Comprobaciones cortas (opcional; obligatorio en la práctica si la pregunta principal deja viñetas del módulo
sin ninguna respuesta evaluable: `tests/test_comprobaciones_cortas.py` exige que cada viñeta que el módulo
introduce se cite en un «Paso 4» o en una comprobación). Van en su propio `###`, después de la pregunta y antes
de la línea del paso 5. Cada una cambia de ángulo respecto a la pregunta principal (reconocer el anti-patrón,
elegir el mecanismo para un caso nuevo, detectar el error de una configuración), practica viñetas ya
introducidas, tiene cuatro opciones de longitud pareja y una respuesta plegada que cita las viñetas de su título.

### Comprobaciones cortas

Opcionales: cada una mira, desde otro ángulo, una idea del módulo que la pregunta principal no toca. Responde antes de abrir cada respuesta; un fallo también se anota en tu `FALLOS.md`.

**C1 · TS x.y-Kn, Sn.** Enunciado con un caso distinto del de la pregunta principal.

- A. …
- B. …
- C. …
- D. …

<details>
<summary>Comprobación C1 · Respuesta</summary>

**X.** Por qué, con las viñetas del título, y por qué no las demás.
</details>
-->

**Paso 5 ·** Si fallaste una predicción `(guía)` o la pregunta, anótalo en tu `FALLOS.md` ([estado personal](../README.md#5-crear-tu-estado-personal)).
