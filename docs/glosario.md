# Glosario

Términos que usan los módulos de las tres apps y el arnés, para quien llega de cero. Cada entrada dice qué **es** la cosa; qué ocurre al usarla bien o mal es lo que enseña cada módulo, y está en su `README.md`.

## El repositorio y el ejercicio

- **Viñeta:** cada punto evaluable de la guía del examen, identificado como `TS x.y-Kn` (conocimiento) o `TS x.y-Sn` (destreza). `CONCEPTOS.md` dice qué módulo introduce cada una.
- **Módulo:** un script pequeño de una app que demuestra una o varias viñetas. Se ejecuta con `uv run python <app>/<módulo>.py`.
- **Anti-patrón:** una forma de construir algo que parece razonable pero es incorrecta. Los módulos lo traen como variante construida mal a propósito, que se elige con `--anti`.
- **`--anti`, `--repeat`, `--budget`:** opciones comunes de los módulos. `--anti` ejecuta una variante anti-patrón; `--repeat N` repite la ejecución para ver una tasa; `--budget` baja el tope de coste de esa ejecución (nunca lo sube).
- **Mesa de ayuda (*helpdesk*):** el dominio de todas las apps: un servicio de soporte TI interno con tickets, empleados y artículos. Los datos son sintéticos (`datos/sinteticos/`).
- **Ticket:** una incidencia o petición registrada en la mesa de ayuda (`TCK-NNNN`). Un empleado se identifica con `EMP-NNNN`.
- **KB (base de conocimiento):** los artículos con procedimientos de la mesa de ayuda (`KB-NNN`).
- **Arnés (`harness/`):** código común que no enseña ninguna viñeta: construye las opciones aisladas del agente, impone el presupuesto, lee la configuración, registra lo que pasa en cada ejecución y permite probar hooks y tools sin modelo.
- **Presupuesto (`max_budget_usd`):** tope de gasto en dólares de una ejecución con modelo. Al alcanzarlo, la ejecución se corta. En los módulos de la Messages API lo aplica el arnés.
- **Rol de modelo:** nombre con el que el arnés elige qué modelo usar (`agent`, `coordinator`, `subagent`, `enforcement`). El modelo concreto de cada rol sale de `.env`.
- **Modo ligero; ejecución obligatoria / ligera:** cómo se consume un módulo. En modo ligero (para cuando falta tiempo) se predice y se contrasta sobre el código, sus comentarios y el resultado de referencia plegado del `README.md`, sin ejecutar. Un módulo de **ejecución obligatoria** se ejecuta incluso en modo ligero, porque su lección es un resultado variable o temporal (una tasa, una latencia) que leer el código no transmite; uno de **ejecución ligera** se puede seguir sin ejecutar. Cada módulo lo indica en la línea **Modo** de su ficha, al principio de su sección.
- **Registro de la ejecución (`RunRecord`):** lo que el arnés recoge de una ejecución (llamadas a tools, quién las hizo, turnos, coste, denegaciones) para comprobarlo en código en lugar de leerlo del texto del modelo.

## El agente y su bucle

- **Agente:** un programa en el que un modelo decide qué pasos dar (qué tools pedir y cuándo terminar) para cumplir una tarea, en lugar de seguir una secuencia fijada por el código.
- **Messages API:** la API de Claude a bajo nivel: una petición con mensajes y una respuesta. El bucle lo escribe tu código (`app1/01`).
- **Agent SDK (`claude-agent-sdk`):** una biblioteca que trae el bucle hecho, tools integradas, hooks, permisos, sesiones y subagentes. La usan casi todos los módulos.
- ***System prompt*:** las instrucciones generales que recibe el modelo al principio, aparte de los mensajes de la conversación.
- **Tool:** una función que el código ofrece al modelo, con nombre, descripción y parámetros. El modelo decide cuándo pedirla y con qué datos; el código la ejecuta y devuelve el resultado. La descripción es lo que el modelo lee para elegir.
- **Handler:** la función del código (o del servidor MCP) que ejecuta una tool cuando el modelo la pide y devuelve su resultado.
- **Tools integradas:** las que trae el Agent SDK, como `Read`, `Write`, `Edit`, `Grep` (buscar en el contenido de archivos) y `Glob` (buscar archivos por su ruta).
- **Bucle agéntico:** el código envía el historial al modelo. El modelo responde con texto o pidiendo tools. El código ejecuta las tools, añade sus resultados al historial y vuelve a preguntar. Se repite hasta que el modelo termina.
- **Iteración (turno):** una vuelta del bucle, es decir, una petición al modelo. En una iteración el modelo puede pedir varias tools a la vez, así que iteraciones y llamadas a tools no son lo mismo.
- **`stop_reason`:** campo de cada respuesta que dice por qué se detuvo el modelo. Puede tener varios valores, y el bucle lo consulta para decidir qué hacer a continuación.
- **Historial:** la lista de mensajes que se reenvía completa en cada petición, con las peticiones de tools y sus resultados. El modelo no recuerda nada entre peticiones si no está en el historial.
- **Contexto:** todo lo que el modelo tiene delante en una petición (*system prompt*, historial, definiciones de tools). Tiene un tamaño limitado y cada parte cuesta.
- **`max_turns`:** número máximo de turnos de una ejecución del SDK. En este proyecto es una red de seguridad, no la forma de decidir cuándo parar.
- **`tool_choice`:** parámetro de la petición que controla cuánta libertad tiene el modelo para decidir si llama a una tool y a cuál. Admite varios modos (`auto`, `any` o una tool concreta); qué garantiza cada uno se practica en `app1/05`.
- **Scoping (acotar tools):** decidir qué tools ve cada agente según su tarea, en lugar de darle todas las disponibles.
- **Error estructurado:** la respuesta de una tool que falla, marcada como error y con datos que la describen (por ejemplo, una categoría y si tiene sentido reintentar), en lugar de un mensaje genérico.

## MCP

- **MCP (Model Context Protocol):** un protocolo estándar para que un programa externo, el **servidor MCP**, ofrezca tools y recursos a un agente.
- **Servidor en proceso / stdio:** un servidor MCP puede vivir dentro del mismo programa que el agente (en proceso) o ser un programa aparte con el que se comunica por entrada y salida estándar (stdio).
- **Resource (recurso):** contenido que un servidor MCP expone para leerlo, como un catálogo, sin ser una acción que se ejecuta.
- **`.mcp.json`:** archivo de configuración del proyecto que declara qué servidores MCP se conectan y cómo se lanzan. Puede referirse a variables de entorno en lugar de llevar secretos escritos.

## Control del agente

- ***Enforcement* (cumplimiento programático):** hacer cumplir una regla con código (una comprobación, una puerta, un hook) en lugar de pedirlo en el prompt.
- **Puerta (*gate*):** una comprobación en código que impide una acción hasta que se cumple una condición previa.
- **Hook:** código propio que el SDK ejecuta en puntos fijos del ciclo del agente, por ejemplo antes de que se ejecute una tool (`PreToolUse`) o después, con su resultado (`PostToolUse`). Puede dejar pasar, bloquear o modificar.
- **Deny con motivo:** la respuesta de un hook `PreToolUse` que impide una llamada. La tool no se ejecuta, y el texto del motivo (`permissionDecisionReason`) le llega al modelo en lugar del resultado.
- **Permiso:** la decisión de si una llamada a tool se ejecuta, se pregunta a alguien o se deniega. Lo configuran el modo de permisos (`permission_mode`) y las listas de tools del agente (`allowed_tools`, `disallowed_tools`).
- **Pre-aprobar:** que las llamadas a una tool se ejecuten sin pedir permiso. En el SDK se hace listándola en `allowed_tools`.
- ***Few-shot*:** ejemplos de casos resueltos que se incluyen en el prompt para mostrar al modelo cómo actuar.
- **Escalamiento:** pasar un caso a una persona cuando el agente no debe o no puede resolverlo.
- ***Handoff* (traspaso):** el paquete de información que acompaña a un escalamiento, para que quien recibe el caso pueda seguir sin volver a preguntar.
- **Sumarización progresiva:** resumir la conversación cada cierto tiempo y seguir trabajando a partir del resumen, para no llenar el contexto.
- ***Case facts* (hechos del caso):** un bloque con los datos concretos del caso (importes, fechas, IDs, estados) que se mantiene aparte del resumen y se incluye en cada petición.
- **Sesión:** una conversación con el agente y su historial, identificada por un `session_id`.
- **Reanudar (*resume*):** continuar una sesión anterior con su historial. En la CLI de Claude Code se puede hacer por nombre (`claude --resume <nombre>`).
- **Bifurcar (*fork*):** partir del historial de una sesión existente para explorar otro camino.

## Sistemas multiagente

- **Coordinador:** el agente principal de un sistema multiagente. Recibe la tarea, la reparte entre subagentes y compone la respuesta.
- **Subagente:** un agente que otro agente lanza para una subtarea, con su propio prompt, sus propias tools y su propio contexto. En el SDK se define con `AgentDefinition`.
- **`Agent` / `Task`:** la tool con la que un coordinador lanza un subagente. La guía la llama `Task`; el SDK de este proyecto, `Agent`.
- ***Hub-and-spoke* (estrella):** organización en la que toda la comunicación entre subagentes pasa por el coordinador.
- **Descomposición:** dividir una tarea en subtareas, ya sea con una cadena fija de pasos o de forma adaptativa según lo que se va encontrando.
- **Tool cross-role (entre roles):** una tool de otro rol que se da a un agente de forma muy limitada, para lo frecuente y sencillo.
