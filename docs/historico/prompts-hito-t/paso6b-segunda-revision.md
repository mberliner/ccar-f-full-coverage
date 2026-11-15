Eres una instancia independiente, sin contexto previo. No edites nada: informa hallazgos por gravedad, con archivo y línea.

1. **Pasada de correcciones del Hito T.** En este repositorio revisa `git diff` de `app*/README.md`, `docs/glosario.md`, `README.md` y `plantillas/modulo/README.md` contra las reglas 1–5 de «Incorporación de quien llega de cero» (roadmap §13, en `claude-cert-ccar-f/docs/roadmap-apps-demo-ccar-f.md`, el repositorio de estudio). Comprueba en especial:
   - que en cada módulo «Predice antes de ejecutar» va antes de «Ejecutar», y que «Qué observar» nombra la señal sin dar el resultado, con lo medido plegado en un `<details>` «Resultado de referencia»;
   - que solo `app2/01` y `app3/02` (parte `paralelo`) se marcan como de ejecución obligatoria y el resto como ligera, con el sentido del glosario (ligera = sin ejecutar);
   - que el contexto («Antes de empezar», «El ejercicio», la línea de «Ejecutar») no adelanta lo que se pide predecir, y que ninguna predicción pregunta algo que el contexto ya responde;
   - que no cambia ninguna cifra medida (compara los números del diff).
2. **Roadmap, que nadie ha revisado.** Lee §4.1, §10 (fila T), §13 (regla 5) y §14 (líneas del 2026-10-30 y 2026-10-31) del roadmap: coherencia entre secciones, sin rutas absolutas ni nombres propios, y si la regla 5 encaja con `plantillas/modulo/README.md` (ver la entrada `→ roadmap (§13, regla 5)` en `docs/hallazgos.md`).
3. **Lectura en frío.** Lee solo `README.md` (raíz), `docs/glosario.md` y la sección `## 01` de `app2_agente_con_control/README.md`. ¿Podrías responder las predicciones sin ayuda y sin conocer el resultado? Di qué te falta.
