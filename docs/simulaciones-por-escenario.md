# Simulaciones por escenario: formato

Cómo se practica con varias preguntas que comparten un mismo contexto, como en el examen. Este documento fija el formato; todavía no hay ningún caso escrito. La plantilla está en [`plantillas/simulacion/ESCENARIO.md`](../plantillas/simulacion/ESCENARIO.md) y el formato lo comprueba `tests/test_simulaciones_formato.py`.

## Por qué

Según la guía, el examen tiene 60 ítems de respuesta única y múltiple, en 120 minutos, y los agrupa en 4 escenarios elegidos al azar de un banco de 6. Cada escenario presenta un contexto de producción que enmarca varias preguntas. La práctica de este repositorio es de preguntas sueltas por módulo, que no ejercita mantener un contexto y unas restricciones a lo largo de varias preguntas, ni alternar de un tema a otro dentro del mismo caso.

Una simulación no sustituye a los módulos: los usa. Se hace cuando los módulos de ese escenario ya están hechos.

## Los seis escenarios

Los dominios principales son los que la guía asigna a cada escenario. El estado de preparación dice si el repositorio ya tiene el material para escribir el caso; es una instantánea (190 de 240 viñetas, 2026-11-06) que se actualiza al cerrar cada tanda.

| Caso | Escenario de la guía | Dominios principales | Qué cubre del repositorio | Estado de preparación |
| :--- | :--- | :--- | :--- | :--- |
| E1 | Customer Support Resolution Agent (agente de resolución de soporte) | D1 · D2 · D5 | `app2/01`–`03`, `05`–`07`; `app1/03`–`04` | Espera: el escalamiento (TS 5.2, `app2/04`) está en 0 de 9 y es el centro del escenario |
| E2 | Code Generation with Claude Code (generación de código con Claude Code) | D3 · D5 | Sección D3 (TS 3.1 a 3.5) | Casi: D3 3.1–3.5 está completo; en D5 faltan TS 5.2 y 5.5 |
| E3 | Multi-Agent Research System (sistema multiagente de investigación) | D1 · D2 · D5 | `app3/01`–`06`; `app1/03`–`04` | Listo: D1, D2 y D5 (5.1, 5.3, 5.4 y 5.6) están entregados |
| E4 | Developer Productivity with Claude (productividad de desarrollo) | D1 · D2 · D3 | `app1/02`, `03`, `06`; `app3/02` (legacy); sección D3 | Listo: D2 y D3 3.1–3.5 completos; D1 en 46 de 48 |
| E5 | Claude Code for Continuous Integration (Claude Code en CI) | D3 · D4 | Sección D3; `app3/11` y `app3/12` (pendientes) | Espera: TS 3.6 (0 de 9), 4.1 (0 de 6) y 4.6 (0 de 6) llegan con `app3/11` y `app3/12` |
| E6 | Structured Data Extraction (extracción estructurada) | D4 · D5 | `app3/07`–`09`; `app2/04`, `app3/10` y `app3/11` (pendientes) | Casi: la extracción (4.3, 4.5) está entregada y 4.4 en 6 de 8; faltan 4.2 (3 de 9) y 5.5 (0 de 8) |

Las etiquetas E1, E3 y E4 ya se usan en los README de las apps. Qué módulos cubren cada escenario es una propuesta del proyecto a partir de los dominios, no algo que diga la guía.

## Formato de un caso

Un caso es un archivo `simulaciones/E<n>_<tema>.md` con esta estructura (ver la plantilla):

- **Cabecera:** el escenario (`E1` a `E6`), sus dominios principales, el número de preguntas y un tiempo orientativo.
- **Contexto:** el escenario en palabras propias, ambientado en la mesa de ayuda cuando encaja. No se copia el texto de la guía ni preguntas reales del examen (`docs/estandares-codigo.md`).
- **Restricciones compartidas:** al menos dos (`R1`, `R2`…), por ejemplo un objetivo de resolución o una regla que no puede romperse. Las preguntas se apoyan en el contexto y en ellas.
- **Plan de preguntas:** una fila por pregunta con su Task Statement y su formato.
- **Preguntas:** cada una con su TS, de respuesta única o multiple-response, cuatro opciones (A a D) y la respuesta plegada.

Reglas del formato:

1. **Tamaño.** Un caso de estudio lleva de 8 a 10 preguntas. Un caso de examen completo lleva 15, que es lo que sale de repartir 60 ítems entre 4 escenarios. El validador admite de 8 a 15.
2. **Ambos formatos.** Al menos dos preguntas multiple-response por caso. Cada una dice cuántas hay que elegir («**Selecciona dos**») y su respuesta nombra exactamente ese número. La proporción real de cada formato en el examen no la publica la guía; este mínimo es del proyecto.
3. **Respuesta única o múltiple, igual que en los módulos:** la respuesta empieza por la letra o letras en negrita y cita al menos una viñeta de su propio TS. Una misma letra no es la correcta en más de la mitad de las de respuesta única.
4. **Solo la guía.** Ninguna respuesta depende de `Producto observado (no evaluable)` ni de `EN PRODUCCIÓN (no evaluable)` (carriles en `docs/estandares-codigo.md`).
5. **Opciones.** Misma longitud y registro, con la correcta no siempre en la misma posición ni siempre la más larga (`docs/estandares-flujo.md`).
6. **Revisión.** Antes de darlo por cerrado, un revisor distinto de quien lo escribió lo contrasta con la guía.

El validador comprueba la estructura (cabecera, secciones, restricciones, numeración, opciones, respuesta, formato y viñetas) y el reparto de letras. No comprueba que las preguntas se apoyen de verdad en el contexto ni que evalúen bien su viñeta: eso es de la revisión.

## Ritmo y corrección

- **Tiempo:** unos 2 minutos por pregunta, que es lo que sale de 120 minutos para 60 ítems. Un caso de estudio son 16 a 20 minutos.
- **Antes de abrir ninguna respuesta,** contesta todo el caso. Después abre las respuestas y revisa cada fallo con las viñetas que cita.
- **Informe por dominio:** el porcentaje acertado en cada dominio, que es lo que informa la guía en su informe de resultados. No se calcula la nota escalada (la guía usa una escala de 100 a 1.000 con corte en 720), porque con unas pocas preguntas no se puede reproducir.
- **Anota los fallos** en tu `FALLOS.md`, con la viñeta de cada pregunta.

## La simulación completa

Al llegar a 240 de 240, una simulación completa son 4 casos de examen (15 preguntas cada uno, 60 ítems, 120 minutos) de escenarios distintos. El reparto objetivo por dominio sigue los pesos del blueprint; con 4 escenarios al azar no sale exacto, así que se ajusta eligiendo las preguntas por TS.

| Área | Dominio | Ítems | Peso |
| :--- | :--- | :---: | :---: |
| D1 | Agentic Architecture & Orchestration | 16 | 27 % |
| D2 | Tool Design & MCP Integration | 11 | 18 % |
| D3 | Claude Code Configuration & Workflows | 12 | 20 % |
| D4 | Prompt Engineering & Structured Output | 12 | 20 % |
| D5 | Context Management & Reliability | 9 | 15 % |

## Qué falta

- **Los casos.** Ninguno escrito. E3 y E4 podrían escribirse ya; E2 y E6, casi; E1 y E5 esperan a las tandas C y D.
- **Presentarlos con la práctica guiada.** `practica-guiada` narra módulos; para un caso hay que definir cómo se presentan varias preguntas con contexto compartido. No está hecho.
- **Los casos de examen completo.** Dependen del 240 de 240.
