<!--
PROPÓSITO: plantilla de la sección de un módulo en el `README.md` de su app (roadmap §13, reglas 1–5).
Se copia bajo `## NN · Título` y se rellena. Lo común (tool, iteración, `stop_reason`, historial,
hook…) NO se repite aquí: se enlaza a docs/glosario.md y se amplía solo con términos propios.
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

### Ejecutar

```bash
uv run python appN_nombre/NN_concepto.py            # correcta
uv run python appN_nombre/NN_concepto.py --anti ... # variante construida mal
```

**Ejecución obligatoria** o ligera: indícalo (roadmap §13).

### Predice antes de ejecutar

<!-- Con tus palabras. Pide patrones, rangos o invariantes (lo igual en cualquier ejecución y lo que varía), no un valor que el modelo pueda variar. -->

1. Pregunta sobre un patrón o un rango.

### Qué observar

Qué señal mirar en la salida (sin dar aquí el resultado esperado).

### Pregunta tipo examen

Enunciado, opciones de longitud y registro parejos (la correcta no siempre en la misma posición) y respuesta en `<details>`.
