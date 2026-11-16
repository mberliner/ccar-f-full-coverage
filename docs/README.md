# Documentos del proyecto

Índice de `docs/`, en tres grupos según para qué se abre cada documento. El orden de estudio del curso está en el [`README.md`](../README.md) de la raíz.

## Estudio

Para quien practica el curso.

- [`glosario.md`](glosario.md): qué es cada término propio del repositorio y del ejercicio, para quien llega de cero.
- [`credenciales-y-modos.md`](credenciales-y-modos.md): qué credencial pide cada módulo, si se hace leyendo (ligera) o ejecutando (obligatoria) y qué demuestra cada camino.
- [`tipos-de-senal.md`](tipos-de-senal.md): qué partes de cada módulo enseñan el mecanismo al ejecutarlas y cuáles solo se explican; se consulta antes de decidir qué ejecutar.
- [`simulaciones-por-escenario.md`](simulaciones-por-escenario.md): cómo se practican varias preguntas sobre un contexto compartido, como en el examen, y el estado de los seis casos de `simulaciones/`.
- [`repaso/`](repaso/): una hoja por dominio (D1 a D5) con viñeta, idea, trampa y módulo, para un vistazo rápido. Están generadas: no se editan a mano.
- [`hooks/`](hooks/): ayuda rápida de los hooks `PreToolUse` y `PostToolUse` (TS 1.5) y sus escenarios con código ejecutable (`hooks_escenarios.py`, autocomprobación sin modelo). Documentos autónomos y portables: no usan el arnés del proyecto.

## Construcción

Para quien mantiene o amplía el proyecto.

- [`estandares-codigo.md`](estandares-codigo.md): idioma, cabeceras, regla «una vez», perímetro de la guía, carriles de contenido, ejecución con modelo y datos.
- [`estandares-flujo.md`](estandares-flujo.md): cómo se construye (plan mode, tests primero, git), registro entre sesiones, ejercicios de evaluación y revisión.
- [`hallazgos.md`](hallazgos.md): notas de producto con fecha y versión, medidas por módulo y los asuntos abiertos.
- [`precedencia-y-nombres.md`](precedencia-y-nombres.md): qué definición gana cuando dos comparten nombre y cómo se combinan las fuentes que se acumulan.
- [`plan-pruebas-precedencia.md`](plan-pruebas-precedencia.md): las pruebas propias cuyos resultados respaldan `precedencia-y-nombres.md`.

## Histórico

- [`historico/`](historico/): diseños de las entregas 1 a 3 y del Hito T, los prompts con que se ejecutaron, el encargo del asistente narrador y la auditoría de coherencia. Son registros congelados: las rutas `docs/…` de su interior son anteriores al traslado a esta carpeta y no se han reescrito.
