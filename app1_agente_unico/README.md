# app1 · Agente único

Un agente, sus tools y su bucle: la base sobre la que se apoyan app2 y app3. El dominio es una mesa de ayuda TI con datos sintéticos (`datos/sinteticos/`).

## Ruta de lectura

Cada módulo sigue el ciclo de `README.md` del proyecto: **predecir → ejecutar (correcto y `--anti`) → contrastar → responder la pregunta → anotar los fallos en tu `FALLOS.md` (`estado/<perfil>/`)**.

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_bucle_manual.py`](01_bucle_manual.py) | TS 1.1-K1, K2, K3, S1, S2, S3 · TS 5.1-K4 | 1 |
| [`02_tools_integradas.py`](02_tools_integradas.py) | TS 2.5-K1, K2, K3, K4, S1, S2, S3, S4, S5 | 2 |
| `03_servidor_mcp.py` | TS 2.1 | 2 |
| `04_errores_estructurados.py` | TS 2.2 | 2 |
| `05_scoping_y_tool_choice.py` | TS 2.3 | 2 |
| `06_mcp_config.py` | TS 2.4 | 2 |
| `07_recorte_de_contexto.py` | TS 5.1-K3, S3 | 3 |

---

## 01 · Bucle manual

```bash
uv run python app1_agente_unico/01_bucle_manual.py                  # correcto
uv run python app1_agente_unico/01_bucle_manual.py --anti texto     # o tope, texto_asistente, sin_historial, arbol_fijo
uv run python app1_agente_unico/01_bucle_manual.py --budget 0.05    # prueba barata (el tope solo baja)
```

El agente atiende el ticket ambiguo «Soy Laura Gómez y necesito que me restablezcáis la contraseña», que no trae `user_id`. Hay dos empleadas con ese nombre, así que necesita encadenar `get_ticket` → `get_user` → `search_kb` y pedir un identificador.

La salida muestra la credencial y las versiones (§11.1), el modelo y el presupuesto con su origen, cada iteración con su `stop_reason` y sus tools, y la causa de la parada.

**Predice antes de ejecutar:**

1. ¿Cuántas iteraciones necesitará la variante correcta? ¿Cuál será su `stop_reason` final?
2. Con `--anti tope` (tope de 2), ¿llegará a pedir el identificador?
3. Con `--anti sin_historial`, ¿qué hará el modelo en la segunda petición?
4. Con `--anti arbol_fijo`, ¿qué devolverá `get_user` y qué respuesta redactará el modelo?

**Qué observar:**

| Variante | Parada | Qué se rompe |
| :--- | :--- | :--- |
| correcta | `end_turn` | — |
| `texto` | la primera vez que el texto dice «terminado», «listo»… | para cuando el modelo comenta, no cuando acaba |
| `tope` | tras 2 iteraciones | corta a mitad del trabajo, sin respuesta final |
| `texto_asistente` | en cuanto hay texto junto a un `tool_use` | el texto «voy a mirar el ticket» no es una respuesta |
| `sin_historial` | red de seguridad (12) | el modelo no ve sus resultados y repite la misma llamada |
| `arbol_fijo` | una llamada al modelo | la secuencia no se adapta: `get_user` falla sin `user_id` y no hay rama para buscar por nombre |

La variabilidad entre ejecuciones es parte de la lección: según la ejecución, el modelo puede no escribir texto junto a sus llamadas, y entonces `texto_asistente` no corta. Las variantes se prueban de forma determinista en `tests/test_app1_01_bucle_manual.py`.

### Pregunta tipo examen

Un agente de soporte construido con la Messages API a veces deja tareas a medias: responde «Perfecto, ya lo tengo» y el bucle termina antes de consultar el sistema de pedidos. El código actual sale del bucle cuando la respuesta contiene un bloque de texto. ¿Qué cambio es el más adecuado?

- A. Añadir al *system prompt* «no escribas texto hasta haber terminado».
- B. Continuar mientras `stop_reason` sea `"tool_use"` y terminar con `"end_turn"`, devolviendo cada `tool_result` al historial.
- C. Buscar frases como «he terminado» o «listo» en el texto para decidir el final.
- D. Fijar un máximo de 5 iteraciones para asegurar que el bucle consulta todas las tools.

<details>
<summary>Respuesta</summary>

**B.** La parada la decide `stop_reason` (TS 1.1-K1, 1.1-S1) y los resultados vuelven al historial con su `tool_use_id` (TS 1.1-K2, 1.1-S2). A intenta arreglar en prosa un error del código de control; C es el anti-patrón de interpretar lenguaje natural y D el de usar un tope como parada principal (TS 1.1-S3). El texto junto a un `tool_use` es comentario, no una señal de fin.
</details>

---

## 02 · Tools integradas

```bash
uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda                    # Grep y Glob
uv run python app1_agente_unico/02_tools_integradas.py --parte busqueda --anti sin_grep
uv run python app1_agente_unico/02_tools_integradas.py --parte incremental [--anti leer_todo]
uv run python app1_agente_unico/02_tools_integradas.py --parte wrapper [--anti solo_nombre]
uv run python app1_agente_unico/02_tools_integradas.py --parte edicion
uv run python app1_agente_unico/02_tools_integradas.py --parte wrapper --repeat 3 --budget 0.10   # prueba barata
```

Mismo agente que en `01`, ahora con el Agent SDK y sus tools integradas (`Read`, `Write`, `Edit`, `Grep`, `Glob`). Trabaja sobre una **copia temporal** de `repo_mesa/` (un paquete pequeño de la mesa de ayuda, generado por `datos/generar_sinteticos.py`): `Edit` y `Write` escriben en la copia y los datos sintéticos originales no se tocan nunca. `--anti` solo vale con la parte a la que pertenece.

La salida muestra `[contexto]`, cada llamada con su resultado y, al final de cada petición, `[medida]` (llamadas por tool, número de `Read` y coste) y `[comprobación]` (calculada en código, no leída del texto del modelo).

**Predice antes de ejecutar:**

1. `busqueda`: ¿qué tool usará para localizar el mensaje de error y cuál para listar los tests? ¿Cuántos `Read` hará? Y con `--anti sin_grep`, ¿cuántos más?
2. `incremental`: ¿por qué archivo empezará? ¿Cuántos `Read` hará la variante correcta frente a `leer_todo`, y cuánto subirá el coste?
3. `wrapper`: `calcular_sla` tiene llamadores que nunca escriben ese nombre. ¿Cuántos de los 4 encontrará cada variante?
4. `edicion`: el ancla `TIMEOUT = 30` aparece dos veces. ¿Qué pasará con el primer `Edit`? ¿Y después?

**Qué observar:**

| Parte / variante | Señal | Qué se rompe |
| :--- | :--- | :--- |
| `busqueda` correcta | `Grep` → `core/sla.py` y `Glob` → los 3 tests, con 0–1 `Read` | — |
| `busqueda` `sin_grep` | más `Read`, a veces apoyados en `Glob` | leer archivo por archivo para algo que una búsqueda resuelve |
| `incremental` correcta | `Grep` a un punto de entrada y `Read` de lo que importa | — |
| `incremental` `leer_todo` | un `Read` por cada `.py` y más coste | el mismo resultado, más caro, y contexto lleno de archivos irrelevantes |
| `wrapper` correcta | `api.py` primero, después una búsqueda por cada nombre: 4 de 4 | — |
| `wrapper` `solo_nombre` | 2 de 4: `informes/resumen.py` y `notificaciones/avisos.py` no salen | un rastreo incompleto que parece completo |
| `edicion` | `Edit` con `is_error` y después `Write` (o un `Edit` con más contexto); archivo final correcto | — |

Notas:

- **`edicion`:** ampliar el ancla con más contexto también resuelve el fallo. Es válido y el comprobador lo acepta, porque mira el archivo final. La guía nombra `Read` + `Write` como respaldo; ampliar el ancla es una inferencia propia. `[comprobación]` indica cuál de los dos caminos tomó.
- **`busqueda`:** la primera pregunta localiza el mensaje de error «SLA vencido para…» y no los llamadores de la función, porque estos son el reto de `wrapper` (TS 2.5-S5).
- **Variabilidad:** con un modelo capaz, `sin_grep` o `leer_todo` pueden salir casi iguales en un repositorio de este tamaño. Lo estable es el comprobador de `wrapper` y el fallo de `Edit`. Usa `--repeat` para ver tasas. Las funciones de comprobación se prueban sin modelo en `tests/test_app1_02_tools_integradas.py`.

### Pregunta tipo examen

Un agente de mantenimiento debe encontrar todos los llamadores de `process_refund` antes de cambiar su firma. El módulo `payments/api.py` la reexporta como `issue_refund`, y otros servicios importan `issue_refund` y no el nombre original. ¿Qué enfoque es el más adecuado?

- A. Buscar el texto `process_refund` con `Grep` y dar por llamadores los archivos que devuelva, porque el nombre original identifica todos los usos.
- B. Leer con `Read` cada archivo del directorio de servicios en orden, para que ninguna búsqueda por patrón deje fuera un llamador.
- C. Identificar los nombres con que `payments/api.py` exporta la función y buscar cada uno con `Grep`, juntando los archivos de todas las búsquedas.
- D. Usar `Glob` con el patrón `**/*refund*.py` para dar con los archivos cuyo nombre menciona la función y revisar solo esos.

<details>
<summary>Respuesta</summary>

**C.** Para rastrear una función a través de un módulo *wrapper* se identifican primero todos los nombres exportados y después se busca cada uno (TS 2.5-S5); `Grep` es la tool para el contenido (TS 2.5-K1, 2.5-S1). A pierde los llamadores por alias y parece completa; B es leer todo cuando una búsqueda lo resuelve, contra la exploración incremental (TS 2.5-S4); D confunde `Glob` (rutas, TS 2.5-K2) con una búsqueda de contenido: un llamador no tiene por qué llevar «refund» en su nombre de archivo.
</details>
