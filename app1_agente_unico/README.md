# app1 · Agente único

Un agente, sus tools y su bucle: la base sobre la que se apoyan app2 y app3. El dominio es una mesa de ayuda TI con datos sintéticos (`datos/sinteticos/`).

## Ruta de lectura

Cada módulo sigue el ciclo de `README.md` del proyecto: **predecir → ejecutar (correcto y `--anti`) → contrastar → responder la pregunta → anotar los fallos en `FALLOS.md`**.

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_bucle_manual.py`](01_bucle_manual.py) | TS 1.1-K1, K2, K3, S1, S2, S3 · TS 5.1-K4 | 1 |
| `02_tools_integradas.py` | TS 2.5 | 2 |
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
