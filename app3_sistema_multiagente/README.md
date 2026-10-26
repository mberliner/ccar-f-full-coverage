# app3 · Sistema multiagente

Un coordinador (Sonnet) y subagentes (Haiku) que investigan los tickets y la base de conocimiento de la mesa de ayuda (escenarios E3 y E4 del examen). El servidor MCP en proceso [`servers/investigacion.py`](servers/investigacion.py) devuelve cada resultado con el contenido separado de sus metadatos.

## Ruta de lectura

Ciclo de cada módulo: **predecir → ejecutar (correcto y `--anti`) → contrastar → responder → anotar los fallos en tu `FALLOS.md` (`estado/<perfil>/`)**.

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_coordinador.py`](01_coordinador.py) | TS 1.2-K1…K4, S1, S2, S4 · TS 1.3-K1, K2, K3, S1, S4 | 1 |
| [`02_paralelo_y_descomposicion.py`](02_paralelo_y_descomposicion.py) | TS 1.2-S3 · TS 1.3-S3 · TS 1.6-K1, K3, S1, S3 | 1 |
| [`03_tools_entre_roles.py`](03_tools_entre_roles.py) | TS 2.3-K2, K3, S1, S2, S3 | 2 |
| `04_errores_entre_agentes.py` … `12_revision_independiente.py` | D2, D4 y D5 | 3 |

---

## 01 · Coordinador y subagentes

```bash
uv run python app3_sistema_multiagente/01_coordinador.py                      # pregunta amplia, correcto
uv run python app3_sistema_multiagente/01_coordinador.py --pregunta simple    # selección dinámica
uv run python app3_sistema_multiagente/01_coordinador.py --anti estrecha      # o pipeline_completo, sin_hallazgos, procedimental
```

Tres subagentes con `AgentDefinition`: `tickets_analyst` (solo `search_tickets`), `kb_analyst` (solo `search_kb`) y `synthesizer` (sin tools). El coordinador recibe objetivos y criterios de calidad, no pasos, y decide a quién invocar.

**Predice:**

1. Para «¿Qué dice KB-109?», ¿a cuántos subagentes llamará?
2. Con `estrecha`, ¿qué subtema de «problemas de red» faltará en la respuesta?
3. Con `sin_hallazgos`, ¿qué contestará el sintetizador?

**Qué observar** (líneas `[medida]`). En la primera ejecución con modelo:

| Variante | Observado |
| :--- | :--- |
| correcta, pregunta amplia | invoca a los dos analistas y redacta él mismo la respuesta (no necesitó el sintetizador); cubre VPN y wifi |
| `--pregunta simple` | solo `kb_analyst` |
| `estrecha` | todo sobre la VPN; la wifi no aparece (`wifi: False`) |
| `sin_hallazgos` | el sintetizador recibe 0 de 33 hallazgos y dice que no tiene datos; el coordinador acaba redactando él |

Las llamadas por agente (`[llamada rN · tickets_analyst]`) muestran que cada subagente solo usó su tool, y que nada pasó de un subagente a otro sin pasar por el coordinador.

### Pregunta tipo examen

Un sistema de investigación tiene un coordinador y tres subagentes: búsqueda web, análisis de documentos y síntesis. Los informes finales omiten con frecuencia datos que los subagentes de búsqueda sí encontraron. Los registros muestran que el coordinador invoca al sintetizador con la pregunta original. ¿Cuál es la causa más probable?

- A. El sintetizador necesita un modelo con una ventana de contexto mayor.
- B. Los subagentes no heredan el contexto del coordinador: el sintetizador nunca recibió los hallazgos, que había que pasarle en el prompt.
- C. Los subagentes de búsqueda deberían escribir sus resultados en una memoria compartida.
- D. Falta `"Task"` en las `allowedTools` del sintetizador.

<details>
<summary>Respuesta</summary>

**B.** El contexto del subagente es aislado y no hereda el historial del coordinador (TS 1.2-K2, 1.3-K2): los hallazgos completos se incluyen en su prompt (TS 1.3-S1), con los metadatos separados del contenido para conservar la atribución. C contradice que no comparten memoria entre invocaciones. D confunde quién necesita `Task`: es el coordinador, para lanzar subagentes (TS 1.3-K1).
</details>

---

## 02 · Paralelo, refinamiento y descomposición

```bash
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte paralelo          # paralelo y secuencial, con latencias
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte refinamiento
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte descomposicion
uv run python app3_sistema_multiagente/02_paralelo_y_descomposicion.py --parte legacy
```

**Ejecución obligatoria:** `--parte paralelo`, cuya lección es una latencia. Ejecuta los dos modos seguidos y los compara; con `--anti` solo ejecuta el secuencial.

**Predice:**

1. ¿Cuántas llamadas `Agent` llegarán en la primera respuesta en cada modo? ¿Cuánto más rápido irá el paralelo?
2. En `legacy`, ¿qué hará el agente antes de proponer ningún test?

**Qué observar.** En la primera ejecución con modelo:

- **paralelo:** 3 llamadas `Agent` en `r1` frente a una por respuesta (`r1`, `r3`, `r5`); 16,8 s frente a 27,9 s (×1,66). El recorder, que agrupa por `message_id`, las puso las tres en la misma respuesta.
- **refinamiento:** el comprobador busca VPN, wifi e impresora en la síntesis y devuelve al coordinador solo las brechas, como mucho 2 rondas. En la primera ejecución no hubo brechas en la ronda 1 y el bucle no llegó a actuar. Repítelo, o cambia `REQUIRED_SUBTOPICS`, para verlo re-delegar.
- **descomposicion:** la cadena fija procesa los reembolsos en tres pasos, y cada uno recibe solo la salida del anterior. La investigación abierta delegó en 2 rondas, y las subtareas de la segunda (tickets del 19 al 22 de septiembre, bloqueos de cuenta) salieron de los hallazgos de la primera.
- **legacy:** primero `Glob` y `Grep` y después `Read` de los siete archivos. El plan menciona la dependencia escondida: `depreciacion.valor_actual` importa `almacen` dentro de la función y lee la caché que llena `asignaciones`.

### Pregunta tipo examen

Un coordinador debe investigar tres temas independientes con tres subagentes. Hoy los invoca uno por turno y cada investigación tarda el triple de lo necesario. ¿Qué cambio es el más adecuado?

- A. Emitir las tres llamadas a Task en una sola respuesta del coordinador.
- B. Fusionar los tres subagentes en uno con todas las tools.
- C. Bajar `max_turns` para que el coordinador termine antes.
- D. Pedir a cada subagente que lance al siguiente cuando termine.

<details>
<summary>Respuesta</summary>

**A.** Los subagentes en paralelo se lanzan con varias llamadas a Task en la misma respuesta (TS 1.3-S3). B pierde la especialización y el reparto del alcance; C es usar un tope como mecanismo de control (el anti-patrón de TS 1.1-S3); D rompe el hub-and-spoke, en el que toda la comunicación pasa por el coordinador.
</details>

---

## 03 · Tools entre roles

```bash
uv run python app3_sistema_multiagente/03_tools_entre_roles.py                      # correcta
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --anti todas         # el sintetizador con todas las tools
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --anti fetch_url     # tool genérica en el investigador
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --anti sin_verify    # sin tool cross-role
uv run python app3_sistema_multiagente/03_tools_entre_roles.py --repeat 3 --budget 0.60
```

Mismo patrón que `01` (coordinador Sonnet con `tools=["Agent"]` y subagentes Haiku con `AgentDefinition`), con el servidor `investigacion` ampliado. La petición pide un informe con el contenido de ocho URLs (cuatro son documentos y cuatro no: login, seguimiento, imagen y preferencias) y la verificación de cinco afirmaciones (tres simples, con un artículo, y dos complejas, con varios).

| Rol | Tools de la configuración correcta |
| :--- | :--- |
| `researcher` | `search_kb` y `load_document` (valida que la URL sea un documento) |
| `synthesizer` | solo `verify_fact` (acotada: verifica afirmaciones simples; las complejas devuelven «enrutar al coordinador») |

La salida muestra las llamadas por agente, las llamadas fuera de rol (la vara es la configuración correcta), las URLs que no son documentos abiertas con `fetch_url`, las rechazadas por `load_document`, las delegaciones y las llamadas a `verify_fact`, con cuántas volvieron al coordinador.

**Predice antes de ejecutar:**

1. Con la configuración correcta, ¿cuántas de las cinco verificaciones resolverá `verify_fact` y cuántas volverán al coordinador?
2. Con `--anti todas`, ¿qué hará el sintetizador con las tools que no son suyas?
3. Con `--anti fetch_url`, ¿qué URLs abrirá el investigador? ¿Qué pasaba con `load_document`?
4. Con `--anti sin_verify`, ¿cuántas delegaciones habrá en comparación con la correcta y qué hará el coordinador con las verificaciones?

**Qué observar (coordinador Sonnet 5.5, subagentes Haiku 5.5, 3 repeticiones):**

| Variante | Señal observada | Qué dice |
| :--- | :--- | :--- |
| correcta | 0 fuera de rol, 2 delegaciones, 5 llamadas a `verify_fact` y 2 devueltas al coordinador por complejas, ~0,05 $ | cada rol hace lo suyo; la tool acotada cubre lo frecuente y lo complejo sube |
| `todas` | **sin señal**: 0 fuera de rol en las 3 ejecuciones, y tampoco con Haiku 4.5 (3 más); el sintetizador solo usó `verify_fact` | la guía dice que se pondría a buscar; en esta tarea no lo necesita |
| `fetch_url` | en 2 de 3 ejecuciones abrió las 4 páginas que no son documentos; en la 3.ª no abrió ninguna | la tool genérica no impide meter login o seguimiento en los hallazgos |
| `sin_verify` | 0 llamadas a `verify_fact`; el sintetizador no se invoca (1 delegación en vez de 2); coste menor (~0,03 $) | sin tool acotada, la verificación se la queda el coordinador, no el sintetizador |

Notas:

- **`todas`:** la señal que describe la guía (un agente de síntesis que se pone a buscar) no apareció. El sintetizador recibe en su prompt todo lo que necesita y solo verifica; las tools extra están ahí, pero no le hacen falta. Se manifestaría si el sintetizador recibiera información incompleta. Lo estable es lo que se mide con la configuración: qué tools tiene cada rol. En el examen manda la guía.
- **`fetch_url`:** «fuera de rol» cuenta aquí todas las llamadas del investigador a `fetch_url`, incluidas las de documentos válidos, porque esa tool no es de su rol; la señal propia es «URLs no documento abiertas». Con la configuración correcta el investigador no llegó a intentar abrir ninguna URL que no fuera un documento, así que `load_document` no tuvo que rechazar nada.
- **`sin_verify`:** la hipótesis de partida era «más delegaciones»; lo observado es lo contrario. Sin una tool con la que verificar, el coordinador no invoca al sintetizador: redacta el informe y resuelve las afirmaciones él, con lo que el investigador le devuelve. La verificación pierde la herramienta determinista y pasa a ser un juicio del coordinador, algo que este módulo no mide.
- Las tools por rol, las medidas sobre el registro y las opciones del coordinador se prueban sin modelo en `tests/test_app3_03_tools_entre_roles.py`.

### Pregunta tipo examen

Un agente de síntesis recibe todas las tools del sistema y, aunque su cometido es redactar, empieza a hacer búsquedas que duplican el trabajo del agente investigador. ¿Qué cambio es el más adecuado?

- A. Reforzar el *system prompt* del sintetizador con «no hagas búsquedas, solo redacta» y mantener todas sus tools.
- B. Fusionar al investigador y al sintetizador en un solo agente con todas las tools, para que no haya trabajo duplicado.
- C. Restringir sus tools a las de su rol y darle una tool acotada de verificación para las comprobaciones simples frecuentes, enrutando las complejas por el coordinador.
- D. Quitarle todas las tools y hacer que cada comprobación pase por el coordinador, para centralizar el control.

<details>
<summary>Respuesta</summary>

**C.** Un agente con tools fuera de su especialización tiende a malusarlas (TS 2.3-K2); la solución es el acceso acotado, con las tools de su rol (TS 2.3-S1) y una tool cross-role muy limitada para las necesidades de alta frecuencia, con los casos complejos por el coordinador (TS 2.3-K3, TS 2.3-S3). A pide por prosa lo que la configuración debería garantizar; B pierde la especialización y el reparto del alcance; D elimina la tool acotada, y cada verificación simple pasa a depender del coordinador (el anti-patrón de TS 2.3-S3).
</details>
