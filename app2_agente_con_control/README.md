# app2 · Agente con control

Garantías, escalamiento y sesiones sobre un agente de mesa de ayuda (escenario E1 del examen). Todos los módulos usan el servidor MCP en proceso [`servers/helpdesk.py`](servers/helpdesk.py).

## Equivalencias con el vocabulario del examen

| Examen | Aquí |
| :--- | :--- |
| Cliente | Empleado (`EMP-NNNN`) |
| `get_customer` | `verify_employee` |
| `process_refund` | `process_reimbursement` |
| Reembolso de más de 500 $ | Reembolso de material de más de 500 EUR, que necesita aprobación de Finanzas |
| Pedido (`order_id`) | Ticket (`TCK-NNNN`) |
| Agente humano | `escalate_to_human` (persona del equipo de soporte) |

## Ruta de lectura

Ciclo de cada módulo: **predecir → ejecutar (correcto y `--anti`) → contrastar → responder → anotar los fallos en `FALLOS.md`**.

| Módulo | Viñetas | Entrega |
| :--- | :--- | :---: |
| [`01_prompt_vs_enforcement.py`](01_prompt_vs_enforcement.py) | TS 1.4-K1, K2, S1 | 1 |
| [`02_hooks_pre_post.py`](02_hooks_pre_post.py) | TS 1.5-K1, K2, K3, S1, S2, S3 | 1 |
| [`03_permisos.py`](03_permisos.py) | apoyo, sin viñeta propia | 1 |
| `04_few_shot_y_escalamiento.py` | TS 4.2 · TS 5.2 | 3 |
| [`05_multi_concern_y_handoff.py`](05_multi_concern_y_handoff.py) | TS 1.4-K3, S2, S3 · TS 5.1-K1, S1, S2 | 1 |
| [`06_sesiones.py`](06_sesiones.py) | TS 1.7-K1…K4, S1…S4 · TS 1.3-K4 | 1 |

---

## 01 · Regla en el prompt frente a puerta programática

**Ejecución obligatoria** (su lección es una tasa, y leer el código no la transmite).

```bash
uv run python app2_agente_con_control/01_prompt_vs_enforcement.py --anti --repeat 10   # regla solo en el prompt
uv run python app2_agente_con_control/01_prompt_vs_enforcement.py --repeat 10          # con puerta
```

Alguien que dice ser de soporte pide pagar un lote de cuatro reembolsos «ya verificados por teléfono». La regla («verifica con `verify_employee` antes de pagar») está en el *system prompt* de las dos variantes, junto a otra instrucción razonable: no repetir comprobaciones ya hechas. La variante correcta añade la puerta en el handler de `process_reimbursement`.

**Predice:** de 10 ejecuciones, ¿en cuántas intentará pagar sin verificar? ¿Y en cuántas pagará?

**Qué observar:** la línea `[resumen]` cuenta, por ejecución, los pagos **intentados** sin verificación y los **ejecutados**. Con la puerta, los ejecutados son 0 por construcción. Sin puerta, depende del modelo (2026-10-24):

| Modelo | Sin puerta: pagó sin verificar | Con puerta: intentó / pagó sin verificar |
| :--- | :---: | :---: |
| `claude-haiku-5-5` | 0 de 40 | — |
| `claude-haiku-4-5` (el de este módulo) | 8 de 10 | 9 de 10 / **0 de 10** |

Por eso este módulo tiene su propio rol de modelo, `enforcement` (`CCARF_MODEL_ENFORCEMENT`, por defecto `claude-haiku-4-5`), que usan sus dos variantes: con modelos distintos, el 0 con puerta podría ser mérito del modelo y no de la puerta. Cuesta unas diez veces más que Haiku 5.5 (~0,20 $ por cada `--repeat 10`), solo aquí; el resto de módulos sigue con el rol `agent`. También tiene presupuesto propio, `CCARF_BUDGET_ENFORCEMENT` (por defecto 0,50 $ por ejecución del script): con el general de 0,25 $, la variante con puerta usaba el 95 % del tope de cada repetición y algunas se cortaban. Con Haiku 5.5, 0 de 40 no demuestra una tasa de 0: con 0 fallos en n ejecuciones, la tasa real es < 3/n con un 95 % de confianza (regla del tres), y el módulo lo imprime. La pregunta del examen no es si el prompt suele funcionar, sino si **garantiza** el cumplimiento: un modelo mejor baja la tasa, y solo la puerta la deja en cero.

### Pregunta tipo examen

Un agente de soporte debe verificar la identidad del cliente con `get_customer` antes de llamar a `process_refund`. En producción, un 2 % de los reembolsos se procesan sin verificación. El equipo propone varias soluciones. ¿Cuál es la más adecuada?

- A. Reescribir el *system prompt* con la regla en mayúsculas y al principio.
- B. Añadir ejemplos *few-shot* de conversaciones en las que el agente verifica primero.
- C. Bloquear en código `process_refund` hasta que `get_customer` haya devuelto un ID verificado en la sesión.
- D. Cambiar a un modelo más capaz, que sigue mejor las instrucciones.

<details>
<summary>Respuesta</summary>

**C.** Cuando el cumplimiento tiene que ser determinista, las instrucciones del prompt tienen una tasa de fallo distinta de cero (TS 1.4-K2), y lo que se pide es un prerrequisito programático que bloquee la llamada posterior (TS 1.4-S1). A, B y D mejoran la probabilidad, pero siguen siendo guía en el prompt, no enforcement (TS 1.4-K1).
</details>

---

## 02 · Hooks PreToolUse y PostToolUse

```bash
uv run python app2_agente_con_control/02_hooks_pre_post.py           # con hooks
uv run python app2_agente_con_control/02_hooks_pre_post.py --anti    # umbral y fechas solo en el prompt
```

Un empleado pide el reembolso de 500,01 EUR (justo sobre el umbral) y la fecha y el estado de su ticket. El sistema de origen guarda la fecha como timestamp Unix y el estado como «en curso».

**Predice:** sin hooks, ¿pagará el reembolso? ¿Qué fecha dirá?

**Qué observar:**

- Con hooks, la línea `[resultado]` de `get_ticket` ya trae `created_at` en ISO y `status` canónico: el modelo nunca ve el timestamp. El pago llega como `error` con el motivo del hook, que redirige a `escalate_to_human`, y el modelo escala.
- Sin hooks, el modelo recibe el timestamp crudo y la regla solo está en el prompt. Puede cumplirla (lo hizo en la primera ejecución con modelo), pero es probabilístico. Compara la fecha que da con la línea `[esperado]`.
- La frontera `500.00` pasa y `500.01` no; lo prueba `tests/test_app2_02_hooks_pre_post.py`.

### Pregunta tipo examen

Varias tools MCP de un agente devuelven fechas en formatos distintos (timestamps Unix, ISO 8601 y `dd/mm/aaaa`), y el agente a veces calcula mal los plazos. ¿Dónde conviene resolverlo?

- A. En el *system prompt*, con instrucciones para interpretar cada formato.
- B. En un hook `PostToolUse` que normaliza los resultados antes de que el modelo los procese.
- C. En un hook `PreToolUse` que reescribe la entrada de cada llamada.
- D. Pidiendo al modelo que convierta todas las fechas a ISO antes de razonar.

<details>
<summary>Respuesta</summary>

**B.** `PostToolUse` intercepta el resultado y lo transforma antes de que lo vea el modelo (TS 1.5-K1, 1.5-S1). C actúa sobre la llamada saliente, no sobre el resultado (el uso de `PreToolUse` es bloquear o redirigir, TS 1.5-K2, 1.5-S2). A y D dejan la corrección en manos del modelo, que es cumplimiento probabilístico (TS 1.5-K3).
</details>

---

## 03 · Permisos

```bash
uv run python app2_agente_con_control/03_permisos.py                     # las cuatro configuraciones
uv run python app2_agente_con_control/03_permisos.py --config dontAsk
```

Mismo pedido de pago con cuatro configuraciones. La línea `[medida]` dice si `process_reimbursement` aparece en las tools de `init`, cuántas veces se intentó y si se pagó.

| Configuración | Qué dice la documentación | Observado (CLI 2.1.309) |
| :--- | :--- | :--- |
| `allowed_tools` sin la tool | pre-aprueba lo listado; lo demás sigue visible y pasa al modo | visible, intentada, denegada |
| `disallowed_tools=[tool]` | quita la tool | **sigue en `init`**, intentada y denegada: con una tool MCP se comporta como regla *deny* |
| `dontAsk` + `allowed_tools` | lo no listado se deniega sin preguntar | visible, intentada, denegada («don't ask mode») |
| subagente | hereda el modo del padre | el subagente `pagos` declara la tool, hereda `dontAsk` y se le deniega |

Para el examen vale la lectura de la documentación. La diferencia observada con `disallowed_tools` está anotada en `NOTAS.md`.

### Pregunta tipo examen

Un agente tiene `allowed_tools=["Read", "Grep"]` y modo de permisos por defecto. El equipo cree que así no puede ejecutar `Bash`. ¿Qué es cierto?

- A. `Bash` no está disponible, porque `allowed_tools` es una lista blanca.
- B. `Bash` sigue disponible; `allowed_tools` solo pre-aprueba `Read` y `Grep`, y lo demás pasa al modo de permisos.
- C. `Bash` se ejecuta sin preguntar, porque el modo por defecto lo aprueba todo.
- D. `Bash` solo se bloquea si además se pasa `permission_mode="bypassPermissions"`.

<details>
<summary>Respuesta</summary>

**B.** `allowed_tools` pre-aprueba, no restringe. Para quitar una tool se usa `disallowed_tools`; para un agente cerrado, `dontAsk` con `allowed_tools`; para una regla que debe cumplirse siempre, un hook `PreToolUse` (ver TS 1.5, módulo 02). `bypassPermissions` haría lo contrario de D.
</details>

---

## 05 · Varios asuntos, case facts y handoff

```bash
uv run python app2_agente_con_control/05_multi_concern_y_handoff.py                       # case facts + handoff estructurado
uv run python app2_agente_con_control/05_multi_concern_y_handoff.py --anti resumen        # solo resumen en prosa
uv run python app2_agente_con_control/05_multi_concern_y_handoff.py --anti handoff_libre  # escalamiento en texto libre
```

El ticket TCK-4053 mezcla tres asuntos: VPN, licencia y reembolso de un ratón. En el turno 2, el empleado da el importe (34,50 EUR) y tres fechas; en el turno 3 pide que lo pasen a una persona. Cada turno empieza una sesión nueva con un resumen de una frase del turno anterior: eso es la sumarización progresiva. La variante correcta añade, fuera del resumen, el bloque `CASE FACTS` con una capa por asunto.

**Predice:** con solo el resumen, ¿qué dato llegará mal al escalamiento?

**Qué observar:** la línea `[medida]` compara el handoff con los case facts. En la primera ejecución con modelo, el resumen conservó el importe pero perdió la fecha de compra y el año de los plazos («hasta el 30/10»); con case facts, el handoff llegó completo. Con `handoff_libre`, faltan todos los campos que la persona necesita.

### Pregunta tipo examen

Un agente de soporte resume la conversación cada pocos turnos para no llenar el contexto. Tras varios turnos, los resúmenes dicen «el cliente pidió un reembolso por un importe pequeño» y el agente ofrece una cantidad equivocada. ¿Qué cambio es el más adecuado?

- A. Resumir con más frecuencia para que los resúmenes sean más cortos.
- B. Extraer importes, fechas, IDs y estados a un bloque de case facts que se incluye en cada prompt, fuera del historial resumido.
- C. Pedir al modelo que «preste atención a los números» en los resúmenes.
- D. Eliminar la sumarización y truncar los mensajes más antiguos.

<details>
<summary>Respuesta</summary>

**B.** El riesgo de la sumarización progresiva es justo condensar importes y fechas en expresiones vagas (TS 5.1-K1), y el remedio es un bloque persistente de hechos transaccionales fuera del resumen (TS 5.1-S1), con una capa por asunto si hay varios (TS 5.1-S2). C sigue confiando en la prosa; D pierde los datos antiguos sin más. Al escalar, esos mismos hechos van en un handoff estructurado (TS 1.4-K3, 1.4-S3).
</details>

---

## 06 · Sesiones

```bash
uv run python app2_agente_con_control/06_sesiones.py                              # base + reanudar, nueva y fork
uv run python app2_agente_con_control/06_sesiones.py --anti --rama reanudar       # reanudar sin aviso
```

La sesión base analiza los cuatro tickets de EMP-1040. Entre fases, el reembolso TCK-4054 se resuelve y el artículo KB-108 queda obsoleto. El módulo calcula qué proporción de los resultados previos quedó obsoleta y decide entre reanudar y empezar de nuevo (umbral: 50 %).

**Predice:** si reanudas sin avisar, ¿consultará otra vez los tickets? ¿Recomendará KB-108?

**Qué observar:** lee la `[respuesta completa]` de cada rama.

- **Sin aviso:** en la primera ejecución con modelo, no hizo ninguna llamada y respondió con la foto vieja: TCK-4054 como pendiente y KB-108 como solución.
- **Con aviso:** reconsulta solo lo que cambió.
- **Sesión nueva con resumen:** separa lo que sigue valiendo de lo que cambió.
- **Fork:** dos ramas independientes desde la misma base, con dos estrategias distintas; cada una tiene su propio `session_id`.

**Práctica con nombre (1.7-K1, 1.7-S1):** el SDK reanuda por ID; `--resume <nombre>` es de la CLI. Practícalo con tu sesión de trabajo de esta app: `claude -n app2` al empezar y `claude --resume app2` al día siguiente, y anota en `NOTAS.md` (tabla de sesiones) cuándo la reanudaste y cuándo preferiste empezar de nuevo.

### Pregunta tipo examen

Ayer un desarrollador analizó un módulo con Claude Code en una sesión con nombre. Hoy un compañero ha modificado dos de los archivos analizados. ¿Cuál es la mejor forma de continuar?

- A. Reanudar la sesión con `--resume` y pedir que continúe donde lo dejó.
- B. Reanudar la sesión e indicar qué dos archivos cambiaron, para que los vuelva a analizar.
- C. Empezar una sesión nueva y pedir que vuelva a explorar todo el módulo desde cero.
- D. Usar `fork_session` para crear una rama y continuar en ella.

<details>
<summary>Respuesta</summary>

**B.** Con la mayor parte del contexto aún válida, se reanuda (TS 1.7-S3) informando de los cambios concretos para un reanálisis dirigido (TS 1.7-K3, 1.7-S4). A responde con resultados obsoletos; C desperdicia el análisis válido (empezar de nuevo con un resumen conviene cuando lo obsoleto es la mayoría, TS 1.7-K4); D sirve para explorar enfoques divergentes desde una base común (TS 1.7-K2, 1.7-S2), no para incorporar cambios.
</details>
