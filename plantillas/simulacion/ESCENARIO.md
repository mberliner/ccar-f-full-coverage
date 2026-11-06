<!--
Plantilla de un caso de simulación por escenario (docs/simulaciones-por-escenario.md).
Copia este archivo a simulaciones/E<n>_<tema>.md y sustituye los marcadores. Lo comprueba tests/test_simulaciones_formato.py.
- Escenario: E1 a E6, el de la guía. Dominios principales: los que la guía asigna a ese escenario.
- De 8 a 10 preguntas en un caso de estudio (15 en uno de examen completo), al menos 2 multiple-response.
- El contexto va en palabras propias: no se copia texto de la guía ni preguntas reales del examen.
- Las respuestas se apoyan solo en la guía, no en lo que hace hoy el producto ni en prácticas de producción.
- Opciones de la misma longitud y registro; la correcta no siempre en la misma posición ni la más larga.
- Antes de cerrarlo, lo revisa alguien distinto de quien lo escribió.
-->
# E<n> · Título del caso

> **Escenario:** E<n>
> **Dominios principales:** D1 · D2 · D5
> **Preguntas:** 8
> **Tiempo orientativo:** 16 minutos

## Contexto

El escenario en palabras propias: quién construye qué, con qué tools y qué se espera del sistema.

## Restricciones compartidas

- R1: una restricción o un objetivo que varias preguntas dan por sentado.
- R2: otra restricción.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS x.y | una respuesta |
| 2 | TS x.y | multiple-response |

## Preguntas

### Pregunta 1 (TS x.y · una respuesta)

Enunciado que se apoya en el contexto y en alguna restricción.

- A. Opción.
- B. Opción.
- C. Opción.
- D. Opción.

<details>
<summary>Respuesta</summary>

**B.** Por qué, citando la viñeta (TS x.y-K1). Qué trampa tenía cada una de las otras.
</details>

### Pregunta 2 (TS x.y · multiple-response)

Enunciado. **Selecciona dos** afirmaciones o cambios. Evalúa cada opción por separado.

- A. Opción.
- B. Opción.
- C. Opción.
- D. Opción.

<details>
<summary>Respuesta</summary>

**A y C.** Resumen de por qué.

- **A** Justificación, con su viñeta (TS x.y-S1).
- **B** Justificación.
- **C** Justificación.
- **D** Justificación.
</details>
