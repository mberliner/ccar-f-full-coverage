<!--
PROPÓSITO: plantilla de la sección de un módulo en el `README.md` de su app (roadmap §13, reglas 1–5).
Se copia bajo `## NN · Título` y se rellena. Lo común (tool, iteración, `stop_reason`, historial,
hook, deny con motivo, ejecución obligatoria / ligera…) NO se repite aquí: se enlaza a docs/glosario.md
y se amplía solo con términos propios.
El orden sigue el ciclo de §13: predecir antes de ver los comandos y la salida.
`tests/test_readme_modulos.py` exige los rótulos «Antes de empezar» y «Pregunta tipo examen».
Borra estos comentarios al rellenar.
-->

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

**Ejecución obligatoria** o **ligera**: indica cuál y por qué. Obligatoria solo en los módulos que fija el roadmap (§13). Si el tope de `--budget` puede romper la medida, dilo aquí.

<!-- Modo normal (§13): sugiere aquí un parámetro que cambiar para ver qué se rompe. -->

### Qué observar

Qué señal mirar en la salida, sin dar aquí el resultado.

<details>
<summary>Resultado de referencia (ábrelo después de contrastar tu predicción)</summary>

Lo medido con modelo (modelo y fecha), lo estable frente a lo que varía y las notas.
</details>

### Pregunta tipo examen

Enunciado, opciones de longitud y registro parejos (la correcta no siempre en la misma posición) y respuesta en `<details>`.
