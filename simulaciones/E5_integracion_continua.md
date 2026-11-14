<!--
Caso de simulación por escenario (docs/simulaciones-por-escenario.md), escrito con plantillas/simulacion/ESCENARIO.md.
Lo comprueba tests/test_simulaciones_formato.py. Las respuestas se apoyan solo en la guía v1.0.
Pendiente de revisión por una instancia distinta de la que lo escribió (paquete 3.9 del plan de mejoras).
-->
# E5 · Claude Code en el pipeline de la mesa de ayuda

> **Escenario:** E5
> **Dominios principales:** D3 · D4
> **Preguntas:** 10
> **Tiempo orientativo:** 20 minutos

## Contexto

El equipo de la mesa de ayuda ha incorporado Claude Code a su pipeline de integración continua. En cada pull request, un job revisa el diff y publica los hallazgos como comentarios en línea; otro job propone pruebas para el código nuevo del servicio de tickets. Los primeros resultados son irregulares: algunos desarrolladores han empezado a cerrar los comentarios sin leerlos, cada nuevo commit vuelve a publicar avisos que ya estaban, y las pruebas propuestas repiten casos que la suite ya tiene. El equipo quiere ajustar los prompts y la arquitectura de revisión antes de extenderlo al resto de repositorios.

## Restricciones compartidas

- R1: el pipeline corre sin nadie delante; lo que produce Claude Code lo lee otro programa, que publica los comentarios.
- R2: cada comentario publicado tiene que merecer la atención de quien lo recibe; si los avisos falsos abundan, el equipo dejará de leerlos todos.
- R3: los criterios de revisión y de pruebas son del equipo y tienen que ser los mismos en el pipeline y en las sesiones locales.

## Plan de preguntas

| Nº | TS | Formato |
| :--- | :--- | :--- |
| 1 | TS 3.6 | una respuesta |
| 2 | TS 3.6 | multiple-response |
| 3 | TS 3.6 | una respuesta |
| 4 | TS 3.6 | una respuesta |
| 5 | TS 4.1 | una respuesta |
| 6 | TS 4.1 | multiple-response |
| 7 | TS 4.6 | una respuesta |
| 8 | TS 4.6 | una respuesta |
| 9 | TS 4.6 | multiple-response |
| 10 | TS 3.6 | una respuesta |

## Preguntas

### Pregunta 1 (TS 3.6 · una respuesta)

El equipo ha acordado qué debe señalar una revisión (fallos de lógica, uso inseguro de datos de clientes) y qué no (preferencias de estilo). Hoy esos criterios están escritos en el script del job, así que las sesiones locales no los ven. ¿Dónde los pone para cumplir R3?

- A. En un archivo de texto que el job lee y pega al final de cada prompt de revisión.
- B. En el `CLAUDE.md` del proyecto, que Claude Code carga también cuando lo invoca el CI.
- C. En el `~/.claude/CLAUDE.md` de la máquina que ejecuta los jobs del pipeline.
- D. En la descripción de cada pull request, para que quien la abre los repita allí.

<details>
<summary>Respuesta</summary>

**B.** `CLAUDE.md` es el mecanismo para dar a Claude Code invocado desde el CI el contexto del proyecto, incluidos los criterios de revisión (TS 3.6-K3); al estar en el repositorio, lo reciben igual el pipeline y las sesiones locales. A solo llega al job y deja fuera las sesiones locales, en contra de R3. C es configuración de usuario de una sola máquina, que no se comparte por el control de versiones (TS 3.1-K2). D depende de que cada persona copie los criterios en cada pull request.
</details>

### Pregunta 2 (TS 3.6 · multiple-response)

El programa que publica los comentarios (R1) falla a menudo porque la salida de la revisión llega como prosa y cambia de forma de una ejecución a otra. El equipo quiere hallazgos con archivo, línea, gravedad y mensaje que se puedan leer sin interpretar texto. **Selecciona dos** opciones de la invocación de Claude Code que, juntas, lo consiguen. Evalúa cada opción por separado.

- A. Añadir `--output-format json` para que la salida sea JSON y no texto libre.
- B. Pedir en el prompt «responde en JSON» y extraer luego la parte que lo parezca.
- C. Añadir `--json-schema` con el esquema de los hallazgos que espera el publicador.
- D. Dejar la prosa y escribir expresiones regulares que localicen cada hallazgo.

<details>
<summary>Respuesta</summary>

**A y C.** Las dos opciones de la línea de comandos que la guía nombra para forzar salida estructurada en CI.

- **A** Correcta. `--output-format json` da una salida que otro programa puede analizar (TS 3.6-K2, TS 3.6-S2).
- **B** Incorrecta. Una instrucción en el prompt no impone la forma de la salida; la guía asigna esa tarea a las opciones de la línea de comandos (TS 3.6-K2).
- **C** Correcta. `--json-schema`, junto con `--output-format json`, fija la estructura de los hallazgos para publicarlos como comentarios en línea (TS 3.6-K2, TS 3.6-S2).
- **D** Incorrecta. Analizar prosa con expresiones regulares deja el problema como está: la forma sigue cambiando de una ejecución a otra.
</details>

### Pregunta 3 (TS 3.6 · una respuesta)

Cada vez que el autor de un pull request sube un commit nuevo, la revisión se repite sobre el diff completo y vuelve a publicar comentarios sobre problemas que ya estaban señalados, incluso los ya corregidos. ¿Qué cambio lo evita?

- A. Revisar solo el primer commit de cada pull request y no repetir la revisión después.
- B. Borrar todos los comentarios anteriores antes de publicar los de la nueva revisión.
- C. Subir la gravedad mínima para que solo se publiquen los hallazgos más importantes.
- D. Dar los hallazgos previos en el contexto y pedir solo los nuevos o aún sin resolver.

<details>
<summary>Respuesta</summary>

**D.** Al repetir la revisión tras nuevos commits, se incluyen en el contexto los hallazgos de la revisión anterior y se pide informar solo de los problemas nuevos o de los que siguen sin resolver, para no duplicar comentarios (TS 3.6-S3). A deja sin revisar el código que llega después. B pierde el historial y vuelve a publicar lo que no ha cambiado. C reduce lo que se publica, pero no distingue lo repetido de lo nuevo, y R2 pide que lo publicado merezca atención, no solo que sea poco.
</details>

### Pregunta 4 (TS 3.6 · una respuesta)

El job de pruebas propone para el servicio de tickets casos que la suite ya cubre, como crear un ticket con todos los campos válidos. ¿Qué cambio ataca la causa?

- A. Pedir en el prompt que las pruebas propuestas sean originales y no se repitan.
- B. Generar el doble de pruebas y descartar después las que se parezcan entre sí.
- C. Dar en el contexto los archivos de prueba existentes del servicio de tickets.
- D. Limitar el job a proponer una sola prueba por cada función nueva del servicio.

<details>
<summary>Respuesta</summary>

**C.** Si el modelo no ve las pruebas existentes, no puede saber qué escenarios ya están cubiertos; darlas en el contexto evita que proponga duplicados (TS 3.6-S4). A pide algo que el modelo no puede cumplir sin esa información. B solo compara las pruebas nuevas entre sí, no con la suite. D reduce la cantidad, pero la prueba que quede puede seguir repitiendo un caso ya cubierto.
</details>

### Pregunta 5 (TS 4.1 · una respuesta)

La revisión publica hallazgos en tres categorías: seguridad, lógica y estilo. Los de estilo son falsos positivos en su mayoría, y el equipo ha empezado a ignorar también los de seguridad (R2). Mejorar el prompt de estilo llevará varias semanas. ¿Qué hace mientras tanto?

- A. Desactivar por ahora la categoría de estilo y seguir afinando su prompt aparte.
- B. Mantener las tres categorías y añadir al prompt que sea más conservador en estilo.
- C. Publicar los de estilo solo cuando el modelo diga que está muy seguro de ellos.
- D. Mantener las tres categorías y pedir al equipo que no ignore las de seguridad.

<details>
<summary>Respuesta</summary>

**A.** Una categoría con muchos falsos positivos resta confianza también a las categorías acertadas (TS 4.1-K3), y la guía propone desactivar temporalmente esa categoría para recuperar la confianza mientras se mejora su prompt (TS 4.1-S2). B y C se apoyan en instrucciones generales del tipo «sé conservador» o «solo alta confianza», que no mejoran la precisión como lo hacen los criterios categóricos (TS 4.1-K2). D no cambia lo que se publica, que es lo que erosiona la confianza.
</details>

### Pregunta 6 (TS 4.1 · multiple-response)

El equipo reescribe el prompt de revisión para reducir los falsos positivos y para que la misma clase de problema reciba siempre la misma gravedad. **Selecciona dos** cambios que la guía respalda. Evalúa cada opción por separado.

- A. Añadir al prompt «informa solo de los hallazgos de los que tengas mucha confianza».
- B. Enumerar qué se informa (fallos, seguridad) y qué se omite (estilo, patrones locales).
- C. Añadir al prompt «sé conservador y, ante la duda, no publiques ningún comentario».
- D. Definir cada nivel de gravedad con criterios explícitos y un ejemplo concreto de código.

<details>
<summary>Respuesta</summary>

**B y D.** Los dos sustituyen instrucciones vagas por criterios explícitos.

- **A** Incorrecta. Filtrar por confianza es una instrucción general que no mejora la precisión frente a criterios categóricos (TS 4.1-K2, TS 4.1-S1).
- **B** Correcta. Decir qué tipos de problema se informan y cuáles se omiten, en lugar de filtrar por confianza, es la forma de ganar precisión (TS 4.1-K1, TS 4.1-S1).
- **C** Incorrecta. «Sé conservador» es el ejemplo de instrucción general que no mejora la precisión (TS 4.1-K2).
- **D** Correcta. Criterios explícitos de gravedad con ejemplos concretos de código para cada nivel dan una clasificación coherente (TS 4.1-S3).
</details>

### Pregunta 7 (TS 4.6 · una respuesta)

Un job nuevo pide a Claude Code que implemente pequeños arreglos marcados en los tickets internos y, en la misma sesión, que revise lo que acaba de escribir antes de abrir el pull request. Las revisiones casi nunca encuentran nada, pero los revisores humanos sí. ¿Qué cambio mejora la revisión?

- A. Añadir a la misma sesión la instrucción de revisar su propio código con más rigor.
- B. Activar el pensamiento extendido en la misma sesión antes de la fase de revisión.
- C. Revisar el código con una segunda instancia que no tenga el razonamiento previo.
- D. Pedir a la misma sesión que revise dos veces y publicar solo lo que vea en ambas.

<details>
<summary>Respuesta</summary>

**C.** La sesión que genera el código conserva su razonamiento y es menos probable que cuestione sus propias decisiones (TS 4.6-K1, TS 3.6-K4); una instancia independiente, sin ese contexto, detecta mejor los problemas sutiles (TS 4.6-K2, TS 4.6-S1). A y B son justo las alternativas que la guía considera menos eficaces que una instancia independiente: instrucciones de autorrevisión y pensamiento extendido (TS 4.6-K2). D repite la autorrevisión en el mismo contexto y además descarta hallazgos reales que solo aparezcan una vez.
</details>

### Pregunta 8 (TS 4.6 · una respuesta)

Algunos hallazgos de la revisión son claros y otros dudosos, y el equipo quiere que los dudosos los mire una persona antes de publicarse, sin frenar los claros (R2). ¿Qué diseño lo permite?

- A. Publicar todos los hallazgos y pedir al equipo que marque los que resulten dudosos.
- B. Una pasada de verificación en la que el modelo da su confianza en cada hallazgo.
- C. Pedir en el prompt de revisión que no incluya ningún hallazgo del que dude.
- D. Repetir la revisión completa y publicar solo los hallazgos que aparezcan dos veces.

<details>
<summary>Respuesta</summary>

**B.** Una pasada de verificación en la que el modelo informa de su confianza junto a cada hallazgo permite encaminar la revisión de forma calibrada: los de baja confianza van a una persona y los demás se publican (TS 4.6-S3). A publica los dudosos y traslada el trabajo al equipo, en contra de R2. C es una instrucción general que no mejora la precisión (TS 4.1-K2) y no deja nada que encaminar. D descarta hallazgos reales que solo aparezcan en una ejecución.
</details>

### Pregunta 9 (TS 4.6 · multiple-response)

Para los pull requests grandes, el equipo ha partido la revisión en una pasada por archivo, para los problemas locales, y una pasada de integración para el flujo de datos entre archivos. **Selecciona dos** hallazgos que corresponden a la pasada de integración. Evalúa cada opción por separado.

- A. El serializador renombra un campo del ticket y el módulo de avisos aún lee el antiguo.
- B. Una función del módulo de avisos declara una variable local que no llega a usar.
- C. El servicio devuelve `None` sin tickets y quien lo llama en otro módulo espera una lista.
- D. Un bucle del serializador se salta el último elemento de la lista de adjuntos.

<details>
<summary>Respuesta</summary>

**A y C.** Los dos dependen de cómo pasan los datos de un archivo a otro.

- **A** Correcta. El fallo está en la relación entre dos archivos: cada uno por separado parece correcto, y lo detecta la pasada de integración del flujo de datos entre archivos (TS 4.6-K3, TS 4.6-S2).
- **B** Incorrecta. Una variable sin usar se ve dentro de un solo archivo: es un problema local de la pasada por archivo (TS 4.6-S2).
- **C** Correcta. El desajuste entre lo que devuelve un módulo y lo que espera otro es flujo de datos entre archivos (TS 4.6-K3, TS 4.6-S2).
- **D** Incorrecta. Un error en un bucle se ve leyendo ese archivo: es un problema local (TS 4.6-S2).
</details>

### Pregunta 10 (TS 3.6 · una respuesta)

Aunque ya no repite casos de la suite, el job de pruebas propone muchas de poco valor (comprobar que un constructor guarda sus argumentos) y construye a mano datos de ticket que el equipo ya tiene como fixtures. ¿Qué cambio mejora la calidad de lo que propone, según R3?

- A. Pedir en el prompt del job que proponga solo las pruebas que considere importantes.
- B. Pasar al job una lista de pruebas prohibidas, que se amplía con cada mala propuesta.
- C. Revisar a mano las pruebas propuestas y borrar las de poco valor antes del merge.
- D. Documentar en `CLAUDE.md` los estándares de pruebas, qué las hace valiosas y las fixtures.

<details>
<summary>Respuesta</summary>

**D.** Documentar en `CLAUDE.md` los estándares de pruebas, los criterios de una prueba valiosa y las fixtures disponibles mejora la calidad de las pruebas generadas y reduce las de poco valor (TS 3.6-S5, TS 3.6-K3); además, al estar en el repositorio, vale igual para el pipeline y las sesiones locales (R3). A es una instrucción vaga sin criterio explícito. B persigue los síntomas uno a uno y no dice qué fixtures existen. C no cambia lo que el job propone; solo filtra después.
</details>
