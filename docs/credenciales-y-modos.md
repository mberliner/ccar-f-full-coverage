# Credenciales y modos, módulo a módulo

Qué necesitas para cada módulo entregado: con qué llama al modelo, qué credencial pide como mínimo, si se puede hacer leyendo (modo **ligera**) o hay que ejecutarlo (modo **obligatoria**) y qué cuesta. Sirve para decidir por dónde empezar con lo que tienes.

Lo comprueba `tests/test_credenciales_y_modos.py`: clasifica cada módulo leyendo su código y falla si la tabla no coincide con él o con la línea «Modo» de su README, o si un módulo nuevo no tiene fila.

## Tres situaciones

| Qué tienes | Qué puedes hacer |
| :--- | :--- |
| **Nada** (sin credencial) | Los módulos de modo **ligera** leyendo, con el resultado de referencia del Paso 3. Además `app2/07` se ejecuta tal cual (no usa modelo) y `app3/09` con `--ventanas`. **No** puedes completar los cuatro de modo obligatoria. |
| **Suscripción** (login de Claude Code) | Lo anterior y los 15 módulos del **Agent SDK**, incluidos tres de los cuatro obligatorios (`app2/01`, `app3/02`, `app3/04`). Según `harness/credentials.py`; no está verificado módulo a módulo. No sirve para la Messages API ni para Batches. |
| **API key** (`ANTHROPIC_API_KEY`) | Todo, incluidos los cinco módulos de la **Messages API o Batches** (`app1/01`, `app1/05`, `app3/07`, `app3/08`, `app3/09`). `app3/08` es obligatorio y solo funciona con API key. |

Cada ejecución imprime al empezar la credencial que usa y su tope de gasto (`[presupuesto]`, `--budget`). Los términos están en el [glosario](glosario.md).

## Qué demuestra cada camino

Que un módulo se pueda hacer sin credencial no quiere decir que sea equivalente a ejecutarlo, ni a construir:

| Camino | Qué es | Qué no es |
| :--- | :--- | :--- |
| **Leer en modo ligero** | *Preparación conceptual sin coste*: fija conceptos, vocabulario de la guía y los anti-patrones, con el resultado de referencia del Paso 3. | No muestra cómo se comporta el modelo hoy, ni te enfrenta a lo que sale distinto en tu máquina. |
| **Ejecutar los módulos** | Contacto práctico con el comportamiento real: lo que el modelo hace con una regla, un esquema o un reintento. | No es construir un sistema: los módulos son pequeños, con datos sintéticos y el diseño ya resuelto. |
| **Construir algo propio** | La *competencia práctica* que la guía describe: seis meses o más construyendo con las APIs de Claude, el Agent SDK, Claude Code y MCP. La práctica propia de D3 (`d3_claude_code/README.md`) es el primer paso. | No lo sustituye ningún módulo de este repositorio. |

Los cuatro módulos de ejecución obligatoria existen porque su lección solo se ve ejecutando. Quien los hace leyendo se queda con el concepto, no con la observación.

## La tabla

«Coste según su README» recoge solo lo que cada README dice; donde no da una cifra, la tabla tampoco la inventa.

| Módulo | Qué es y cómo llama al modelo | Credencial mínima | Modo | Coste según su README | Sin credencial |
| :--- | :--- | :--- | :--- | :--- | :--- |
| app1/01 | Bucle manual · Messages API | API key | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app1/02 | Tools integradas · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app1/03 | Servidor MCP · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app1/04 | Errores estructurados · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app1/05 | Scoping y `tool_choice` · Messages API y Agent SDK | API key | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app1/06 | Configuración MCP · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app2/01 | Regla en el prompt frente a puerta programática · Agent SDK | API key o suscripción | obligatoria | sin cifra en el README | Hay que ejecutarlo |
| app2/02 | Hooks `PreToolUse` y `PostToolUse` · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app2/03 | Permisos · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app2/05 | Varios asuntos, case facts y handoff · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app2/06 | Sesiones · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app2/07 | Reescribir argumentos (apéndice) · no llama al modelo | Ninguna | ligera | 0 $ | Se ejecuta sin credencial |
| app3/01 | Coordinador y subagentes · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app3/02 | Paralelo, refinamiento y descomposición · Agent SDK | API key o suscripción | obligatoria (parte `paralelo`) | sin cifra en el README | `paralelo`: hay que ejecutarla; el resto se completa leyendo |
| app3/03 | Tools entre roles · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app3/04 | Errores entre agentes · Agent SDK | API key o suscripción | obligatoria | 0,06–0,08 $ por variante (`--repeat 3`) | Hay que ejecutarlo |
| app3/05 | Procedencia entre agentes · Agent SDK | API key o suscripción | ligera | ~0,20 $ (`conflictos`) y ~0,19 $ (`medio`) con `--repeat 3` | Se completa leyendo (Paso 3) |
| app3/06 | Contexto largo · Agent SDK | API key o suscripción | ligera | sin cifra en el README | Se completa leyendo (Paso 3) |
| app3/07 | Extracción estructurada con schema · Messages API | API key | ligera | menos de 0,05 $ por ejecución con Haiku 5.5 | Se completa leyendo (Paso 3) |
| app3/08 | Validación y reintento · Messages API | API key | obligatoria | 0,05–0,07 $ por ejecución | Hay que ejecutarlo, y solo con API key |
| app3/09 | Batches: lotes, ventana y fallidos · Batches (Messages API) | API key | ligera | unos céntimos; `--ventanas` no cuesta | Se completa leyendo; `--ventanas` se ejecuta sin credencial |

## Cómo se mantiene

- Un módulo nuevo necesita su fila antes de poder cerrarse: el test falla si falta.
- La columna «Credencial mínima» sale de leer el código del módulo: `import anthropic` o `require_api_key` (Messages API o Batches) dan «API key»; las opciones del Agent SDK (`isolated_options`, `query`), «API key o suscripción»; ninguna de las dos, «Ninguna». Un módulo que use las dos cuenta como «API key».
- Un módulo con una parte que no usa modelo (como `app3/09` con `--ventanas`) se clasifica entero y la parte se anota en «Sin credencial».
