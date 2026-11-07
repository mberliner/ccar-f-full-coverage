# Tipos de señal, parte a parte

Qué parte de cada módulo te enseña el mecanismo y cuál solo se explica. Una ejecución con modelo no siempre muestra el efecto que el módulo quiere enseñar: a veces el modelo hace lo correcto aunque se le dé el anti-patrón, y lo que queda es una tabla histórica o una explicación de por qué no apareció. Esta clasificación te lo dice antes de gastar la ejecución. Lo comprueba `tests/test_tipos_de_senal.py`.

## Los cuatro tipos

- **Determinista:** no depende de lo que decida el modelo. Se ve sin él (se prueba con un modelo simulado o sin modelo) o sale igual cada vez. Es lo que da el mecanismo con seguridad.
- **Probabilística con control positivo:** depende del modelo, y el Paso 3 recoge una señal que sí apareció, con la variante correcta frente al anti-patrón. Conviene ejecutarla, y el resultado puede variar de una ejecución a otra. Cuando el efecto solo se ve con un modelo, ese es el «modelo de la medida» (ver el README del módulo).
- **Sin señal estable:** el README reconoce que el efecto no apareció, o que es inestable, o que depende del modelo hasta no ser fiable. La lección es conceptual: ejecutarla no la demuestra. Se explica leyendo.
- **Sin medir:** la variante está implementada y se prueba sin modelo, pero el Paso 3 no recoge ninguna medida con modelo. No se sabe si su efecto se ve; ejecutarla es explorar.

## Cómo usarlo

- Para **entender el mecanismo**, bastan las partes deterministas y lo que dice el README: no necesitas ejecutar nada más.
- Para **ver el comportamiento del modelo**, ejecuta las partes probabilísticas con control positivo.
- Las partes «sin señal estable» y «sin medir» no tienen por qué ejecutarse. Si lo haces y ves algo distinto, es un hallazgo: anótalo.
- **La ejecución obligatoria no es lo mismo que determinista.** Los cuatro módulos obligatorios (`app2/01`, `app3/02` parte `paralelo`, `app3/04` y `app3/08`) lo son porque su lección solo se ve ejecutando: es una tasa, una latencia o lo que hace el modelo tras un reintento, es decir, una parte probabilística con control positivo. El test exige que todo módulo obligatorio tenga al menos una parte que enseñe algo.

## La tabla

Una fila por parte o variante que el módulo ejecuta. La columna de evidencia resume lo que dice el README; los datos completos están en su Paso 3 y en `docs/hallazgos.md`.

| Módulo | Parte o variante | Tipo | Qué dice su README |
| :--- | :--- | :--- | :--- |
| app1/01 | correcta y `--anti texto`, `tope`, `sin_historial`, `arbol_fijo` | Determinista | El criterio de parada y sus fallos se prueban sin modelo en `tests/test_app1_01_bucle_manual.py`; el modelo decide cuántas iteraciones hacen falta, no el mecanismo |
| app1/01 | `--anti texto_asistente` | Sin señal estable | La variabilidad es parte de la lección: según la ejecución el modelo puede no escribir texto junto a sus llamadas, y entonces no corta |
| app1/02 | `--parte busqueda` (correcta y `--anti sin_grep`) | Sin señal estable | Con un modelo capaz pueden salir casi iguales en un repositorio de este tamaño |
| app1/02 | `--parte incremental` (correcta y `--anti leer_todo`) | Sin señal estable | Igual: casi iguales; la explicación es conceptual |
| app1/02 | `--parte wrapper` (correcta y `--anti solo_nombre`) | Probabilística con control positivo | La correcta encuentra los 4 archivos y `solo_nombre` deja fuera 2 de 4; el comprobador es lo estable |
| app1/02 | `--parte edicion` | Probabilística con control positivo | El `Edit` falla con `is_error` («Found 2 matches») en cerca de la mitad de las ejecuciones |
| app1/03 | correcta | Probabilística con control positivo | Control: con descripciones buenas el agente acierta en todas las peticiones |
| app1/03 | `--anti minimas` | Probabilística con control positivo | La señal se ve con Haiku 4.5 (modelo de la medida); con el otro rol de modelo es inestable |
| app1/03 | `--anti palabra_clave` | Probabilística con control positivo | La señal se ve con Haiku 5.5: la regla del prompt gana a la descripción en las peticiones con la palabra |
| app1/03 | `--anti nombre_enganoso` | Sin señal estable | Sin señal: la descripción pesa más que el nombre |
| app1/04 | correcta | Probabilística con control positivo | Un solo reintento, del fallo transitorio, que se recupera |
| app1/04 | `--anti generico` | Probabilística con control positivo | Un reintento inútil por ejecución; depende del modelo (con el otro rol no hubo reintentos inútiles) |
| app1/04 | `--anti fallo_como_vacio` | Probabilística con control positivo | Acepta el histórico vacío sin reintentar, medido sobre el registro |
| app1/05 | `--parte scoping` (5 y 18 tools) | Sin señal estable | El acierto no baja con 18 tools; lo que sí sube es el coste |
| app1/05 | `--parte tool_choice` (`auto`, `any`, forzado) | Probabilística con control positivo | `auto` contesta con texto; `any` y la forzada empiezan siempre por una tool |
| app1/06 | `--parte conexion` | Determinista | Prefijos `mcp__<servidor>__` y token: el `.mcp.json` generado y los contadores se prueban sin modelo |
| app1/06 | `--parte recursos` (correcta y `--anti sin_recursos`) | Probabilística con control positivo | La correcta lee los resources sin explorar; sin ellos explora con muchas más llamadas y cuesta de 2,3 a 3,7 veces más |
| app1/06 | `--parte descripcion` (correcta y `--anti descripcion_minima`) | Sin señal estable | La señal que dice la guía no se vio: sin diferencia entre las dos |
| app2/01 | correcta (con puerta) | Determinista | Con la puerta, los pagos ejecutados son 0 por construcción |
| app2/01 | `--anti` (regla solo en el prompt) | Probabilística con control positivo | Se ve con el rol `enforcement`, que es el modelo de la medida: se salta la regla en 8 de 10 ejecuciones; con el modelo más reciente no se ve |
| app2/02 | correcta (con hooks) | Determinista | El hook normaliza y la frontera 500,00 pasa y 500,01 no; el modelo nunca ve el timestamp crudo |
| app2/02 | `--anti` (umbral y fechas solo en el prompt) | Sin medir | El README dice que el modelo puede cumplirlo pero es probabilístico; no recoge ninguna tasa |
| app2/03 | las cuatro `--config` | Determinista | La configuración fija lo que cada una deja pasar; es una comprobación operativa, no evaluable |
| app2/05 | correcta (case facts y handoff estructurado) | Probabilística con control positivo | El handoff llegó completo (una ejecución) |
| app2/05 | `--anti resumen` | Probabilística con control positivo | El resumen conservó el importe pero perdió la fecha de compra y el año de los plazos (una ejecución) |
| app2/05 | `--anti handoff_libre` | Determinista | Fallo estructural: con texto libre faltan los campos que la persona necesita y el código no puede comprobarlos |
| app2/06 | decisión de reanudar o empezar de nuevo | Determinista | La proporción de obsoletos la calcula el código (33 %, así que reanuda) |
| app2/06 | `--rama nueva` | Probabilística con control positivo | Es la rama que menos cuesta; la diferencia es pequeña y de una ejecución |
| app2/06 | `--rama fork` | Determinista | Cada rama tiene su propio `session_id` y no ve a la otra |
| app2/06 | `--rama reanudar` (con aviso de cambios) | Probabilística con control positivo | Reconsulta solo lo que cambió, sin repetir todas las consultas |
| app2/06 | `--anti --rama reanudar` (sin aviso) | Probabilística con control positivo | No hizo ninguna llamada y respondió con la foto vieja (una ejecución) |
| app2/07 | `updatedInput`, `--anti` y control | Determinista | No hay modelo ni coste: un desenlace, siempre el mismo |
| app3/01 | correcta, pregunta amplia | Probabilística con control positivo | Invoca a los dos analistas y cubre VPN y wifi |
| app3/01 | `--pregunta simple` | Probabilística con control positivo | Solo invoca a `kb_analyst` |
| app3/01 | `--anti estrecha` | Probabilística con control positivo | Todo sobre la VPN y la wifi no aparece; la señal fiable son las consultas delegadas, no el detector de palabras |
| app3/01 | `--anti sin_hallazgos` | Probabilística con control positivo | El sintetizador recibe 0 de 33 hallazgos y dice que no tiene datos |
| app3/01 | `--anti pipeline_completo` | Sin medir | Está en el ejercicio y en los comandos, pero el Paso 3 no recoge ninguna medida |
| app3/01 | `--anti procedimental` | Sin medir | Igual: está en el ejercicio y en los comandos, sin medida en el Paso 3 |
| app3/02 | `--parte paralelo` (paralelo y secuencial) | Probabilística con control positivo | Las tres llamadas salen en una respuesta frente a una por respuesta; la aceleración varía entre ejecuciones (×1,66 y ×1,37) |
| app3/02 | `--parte refinamiento` | Sin señal estable | No hubo brechas en la ronda 1 y el bucle no llegó a actuar |
| app3/02 | `--parte descomposicion`, cadena fija | Determinista | Tres pasos y cada uno recibe solo la salida del anterior; se prueba sin modelo |
| app3/02 | `--parte descomposicion`, adaptativa | Probabilística con control positivo | Delegó en dos rondas y las subtareas de la segunda salieron de los hallazgos de la primera |
| app3/02 | `--parte legacy` | Probabilística con control positivo | Descriptiva, sin variante de contraste: busca antes de leer los siete archivos y el plan menciona la dependencia escondida |
| app3/03 | correcta | Probabilística con control positivo | 0 fuera de rol, 2 delegaciones y las llamadas a `verify_fact` devueltas al coordinador |
| app3/03 | `--anti todas` | Sin señal estable | Sin señal: 0 fuera de rol en las 3 ejecuciones |
| app3/03 | `--anti fetch_url` | Probabilística con control positivo | La tool genérica abrió las 4 páginas que no son documentos en 2 de 3 ejecuciones |
| app3/03 | `--anti sin_verify` | Probabilística con control positivo | 0 llamadas a `verify_fact`; el sintetizador se invoca menos |
| app3/04 | correcta | Probabilística con control positivo | La fuente transitoria falló una vez y se recuperó con el reintento local en 3 de 3 |
| app3/04 | `--anti generico` | Sin señal estable | Sin efecto visible sobre el coordinador: hizo lo mismo que en la correcta |
| app3/04 | `--anti silenciar` | Probabilística con control positivo | Fallo tragado por el handler en 3 de 3; brecha anotada en 1 de 3 |
| app3/04 | `--anti abortar` | Probabilística con control positivo | `INVESTIGACIÓN ABORTADA` en 3 de 3, sin cifras ni brecha |
| app3/05 | `conflictos`, correcta | Probabilística con control positivo | Decisión del coordinador acertada en 9/9 pares y tabla en 3 de 3 |
| app3/05 | `--anti sin_procedencia` | Sin señal estable | La pérdida está en lo que devuelve el investigador, no en el informe final |
| app3/05 | `--anti promedio` | Sin señal estable | Fusionó en 1 de 3: señal del anti-patrón, pero no estable |
| app3/05 | `--anti formato_uniforme` | Probabilística con control positivo | Tabla en 0 de 3 frente a 3 de 3 en la correcta |
| app3/05 | `--anti inventar_explicacion` | Probabilística con control positivo | Control positivo con el rol `enforcement`: el borrador del sintetizador inventó la causa en 1 de 3; con el modelo por defecto no se ve |
| app3/05 | `--parte medio` (las cuatro formas del texto) | Sin señal estable | El resumen citó el 41 % en 12 de 12: sin señal de *lost in the middle* |
| app3/06 | correcta (tres fases) | Probabilística con control positivo | El contexto se mantiene por fase, nunca todo junto, y recoge 5 de 5 hechos |
| app3/06 | `--anti todo_en_contexto` | Probabilística con control positivo | La acumulación de contexto aparece; la degradación no |
| app3/06 | `--simular-caida` y reanudación | Determinista | Manifest y scratchpad se prueban sin modelo; la reanudación no repite consultas |
| app3/07 | `--parte forzada`, correcta | Probabilística con control positivo | Forma válida 12/12 y campos ausentes rellenados 1/21 |
| app3/07 | `--parte forzada --anti sin_nullable` | Probabilística con control positivo | Campos ausentes rellenados 21/21 y forma válida 6/12 |
| app3/07 | `--parte forzada --anti enum_cerrado` | Probabilística con control positivo | 2 de 12 con un tipo fuera del `enum` |
| app3/07 | `--parte estricto` | Probabilística con control positivo | Con `strict`, forma válida 12/12 y tipo correcto 9/12; idéntico en las tres repeticiones |
| app3/07 | `--parte tipo_desconocido` | Probabilística con control positivo | `any` y `auto` eligen la tool de su tipo en 12/12; forzada a factura, 5/12 |
| app3/07 | `--parte few_shot` | Probabilística con control positivo | Se ve con el rol `enforcement`, el modelo de la medida: de 5 o 6 fechas incorrectas sin ejemplos a 0 con ellos; con el modelo por defecto no hay señal |
| app3/07 | `--parte enriquecimiento` | Probabilística con control positivo | Con el primer turno forzado, la extracción va primero en 36/36 |
| app3/07 | `--parte enriquecimiento --anti auto_desde_inicio` | Sin señal estable | Consulta antes de extraer 0/12 con los dos modelos probados: sin señal |
| app3/08 | correcta | Probabilística con control positivo | Con el rol `enforcement`, los reintentos arreglan fechas y los conflictos se marcan sin reintentar |
| app3/08 | `--anti reintento_generico` | Probabilística con control positivo | 11, 10 y 11 reintentos, con solo 1, 1 y 3 útiles |
| app3/08 | `--anti insistir` | Probabilística con control positivo | Pedido inventado en las 3 repeticiones |
| app3/08 | validador (sin modelo) | Determinista | El validador y la decisión de reintento se prueban sin modelo |
| app3/09 | `--ventanas` | Determinista | No usa modelo; el resultado es fijo |
| app3/09 | `--enviar` | Probabilística con control positivo | Acierto del 100 % en la muestra síncrona y lote de 12 peticiones |
| app3/09 | `--batch-id` | Probabilística con control positivo | Los resultados llegan en otro orden; 11 ok y 1 truncado |
| app3/09 | `--batch-id --anti por_orden` | Probabilística con control positivo | 11 de 11 documentos reciben los datos de otro; por `custom_id`, ninguno |
| app3/09 | `--batch-id --reenviar` | Probabilística con control positivo | 4 trozos y 4 de 4 correctos; el re-troceo en cadena no se vio en vivo |
| app3/10 | `--parte poblacion` (correcta, `--anti precision_agregada`, `--anti confianza_global`) | Determinista | Sin modelo y con los mismos números en cada ejecución: global 97,7 % frente a 62,5 % del tipo raro; 6, 17 y 8 errores entre lo automatizado (0, 11 y 0 del tipo raro); la muestra estratificada estima una tasa de error del 10,8 % cruda y del 2,0 % ponderada, igual a la real |
| app3/10 | `--parte confianza_modelo` | Probabilística con control positivo | Se ve con Haiku 4.5 sin reglas de formato (modelo de la medida): los errores llegan con confianza alta (banda 0,97–1,00: 82,9 % de acierto declarando el 100 %); con Haiku 5.5 no hay errores que calibrar |
| app3/11 | `--parte orden` | Determinista | Sin modelo: construye la copia temporal, el diff y la orden de `claude -p`, y la imprime entera |
| app3/11 | `--parte revision` (correcta) | Probabilística con control positivo | Encuentra los cinco fallos sembrados en 5 de 5 y marca el comentario de `REINTENTOS` del cambio correcto en 3 de 5 (la puntuación da 5 de 5, pero 2 son el renombrado a `NOTIF_TIMEOUT`, un artefacto; ~0,02 $ por ejecución); frente a `--sin-categoria comment`, 0 de 5 |
| app3/11 | `--parte revision --anti conservador` | Sin señal estable | La señal de la guía (peor precisión que los criterios) no apareció: encuentra los cinco y marca el cambio correcto en 0 de 5, al revés de lo esperado, y la causa (la variante quita también el criterio de comentarios) está sin comprobar |
| app3/11 | `--parte revision --anti sin_ejemplos` | Sin señal estable | Sin diferencia con la correcta: B falta en 1 de 25 y marca el cambio correcto en 4 de 5 |
| app3/11 | `--parte revision --sin-categoria comment` | Probabilística con control positivo | Quitar solo la categoría quita la marca del comentario de `REINTENTOS`: 0 de 5 frente a 3 de 5 con la correcta (leyendo una marca por ejecución; la única marca que queda, 1 de 5, es el renombrado a `NOTIF_TIMEOUT`), y el fallo C se pierde en 1 de 5 |
| app3/11 | `--parte rerevision` (correcta y `--anti sin_previos`) | Probabilística con control positivo | Con los hallazgos previos, 0 repetidos; sin ellos, repite B, C y D en 3 de 3 (cifras de antes de las correcciones C4, no se volvió a medir) |
| app3/11 | `--parte tests` (correcta, `--anti sin_tests_existentes`, `--anti sin_estandares`) | Sin señal estable | 0 escenarios repetidos en las tres ramas, también sin los tests existentes, y ese 0 no es señal ni a favor ni en contra de 3.6-S4: solo 2 de los 5 escenarios existentes son los que el cambio rompe, y la clave (todos los números de `expected`) puede dejar de contar un duplicado real; las propuestas no se revisaron a mano. Sin los estándares salen más tests (9–12 frente a 7–8, en 5 de 5), una diferencia de cantidad en el sentido de 3.6-S5 |
| app3/12 | `--parte plan` | Determinista | Sin modelo: el reparto en pasadas, sus tools y la orden de la autorrevisión o de la pasada única |
| app3/12 | `--parte revision` (instancia nueva) | Sin señal estable | Encuentra los cinco en 5 de 5, pero sin diferencia frente a una sola pasada (`una_pasada`); que D y F salgan sobre todo por integración es en parte consecuencia del diseño |
| app3/12 | `--parte revision --anti autorrevision` | Sin señal estable | Sin diferencia con la instancia nueva (5 de 5): la sesión bifurcada encuentra A, B, C, D y F por archivo |
| app3/12 | `--parte revision --anti autorrevision_explicita` | Sin señal estable | Sin diferencia (5 de 5): la frase añadida no cambió lo encontrado |
| app3/12 | `--parte revision --anti una_pasada` | Sin señal estable | Sin diferencia: 24 de 25 con una sola pasada sobre un diff de 93 líneas, a unas 2 veces menos coste |

## Cómo se mantiene

- Un módulo nuevo añade sus filas al cerrarse; el test falla si le faltan.
- Una fila «Sin señal estable» debe estar respaldada por lo que dice el README de ese módulo («sin señal», «inestable», «sin diferencia», «casi iguales», «variabilidad», «no se vio en el acierto», «sin efecto visible» o «no llegó a actuar»). Una variante sin ninguna medida es «Sin medir», no «Sin señal estable».
- Si una parte «Sin medir» llega a medirse, se reclasifica según lo que salga y la medida se registra en su Paso 3.
- Es una clasificación de esta implementación con los modelos y versiones del Paso 3 de cada módulo; si cambian, puede cambiar.
