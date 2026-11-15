Tanda D de la entrega 3: pase de textos de `app2/04` y `app1/07` (Opus 5.5). Trabajas en la rama `entrega-3d`, que ya tiene el código, los tests, los datos y los registros hechos por Sonnet 5.5 (240/240, `pytest` en verde, sin fusionar). No cambies código ni datos: si un texto exige un cambio de código, anótalo al final y no lo hagas.

Lee primero `CLAUDE.md`, `docs/estandares-codigo.md`, `docs/estandares-flujo.md`, `docs/diseno-entrega-3.md` (tanda D), `NOTAS.md` (casilla de la tanda D), `docs/hallazgos.md` (sección «tanda D»), `app1_agente_unico/CLAUDE.md`, `app2_agente_con_control/CLAUDE.md`, `plantillas/modulo/README.md` y, como modelo de un módulo ya pasado por Opus, `app3_sistema_multiagente/10_confianza_y_revision.py` y su sección del README.

**Qué hay que hacer**

1. **Cabeceras** de `app2_agente_con_control/04_few_shot_y_escalamiento.py` y `app1_agente_unico/07_recorte_de_contexto.py`. Son borradores de Sonnet. `QUÉ DICE LA GUÍA` se escribe contra el texto de la guía (`claude-cert-ccar-f/fuentes/claude-certified-architect-foundations-exam-guide.md`, en el repositorio de estudio; el resumen en español está en `claude-cert-ccar-f/docs/resumen-guia-examen-ccar-f.md`): TS 4.2 K1–K3 y S1 y TS 5.2 K1–K4 y S1–S5 en `04`; TS 5.1 K3 y S3 en `07`. Parafraseado, nunca copiado, con cada K/S en su sitio. Separa los hechos de la guía, lo que la medida no respalda, las inferencias propias y el producto observado.
2. **README**: las secciones `## 04` de `app2` y `## 07` de `app1`. Revisa «Antes de empezar», «Predice antes de ejecutar», el Paso 3 y las preguntas contra las reglas 1 a 5 de «Incorporación de quien llega de cero» (roadmap §13): el contexto no adelanta resultados, las predicciones son por patrón y no por valor, y no preguntan lo que el contexto ya responde.
3. **Preguntas tipo examen:**
   - `04` es denso (13 viñetas): lleva la de respuesta única y la multiple-response, con «**Selecciona dos**», una opción más que las que se eligen y como máximo cuatro, cada opción juzgable sola y la respuesta justificando cada una.
   - Opciones de longitud y registro parejos, y la correcta que no sea la más larga. Posiciones actuales: `app1` 01–06 es B, C, D, A, B, C y `07` es D; `app2` 01–03 y 05–07 es C, B, B, B, B, B y `04` es A (única) y A y C (multiple-response). Cambia la posición de la correcta si hace falta, sin dejar la pregunta peor.
   - La respuesta de examen es la de la guía, no la que sigue lo medido.
4. **Glosario** (`docs/glosario.md`): revisa los términos que Sonnet añadió (criterio de escalamiento, vacío de política, proxy, recorte, tokens de entrada) y añade solo los que la tanda introduce y falten.

**Lo que salió distinto de lo esperado: no se maquilla ni se convierte en respuesta de examen**

- **Los ejemplos no aportan con Haiku 5.5** (`04`): `sin_ejemplos` sale igual que la correcta (55/55 las dos). Con Haiku 4.5 sí hay diferencia (27/33 frente a 32/33), con una muestra pequeña. La guía (4.2-K1) dice que few-shot es la técnica más eficaz cuando las instrucciones solas dan resultados inconsistentes; aquí las instrucciones no eran inconsistentes. Va en el Paso 3 como `Producto observado (no evaluable)`, diciendo que no cambia la respuesta de examen. No se enfrentan los dos modelos en una misma fila (`tests/test_sin_comparacion_de_modelos.py`): cada fila es la señal de su modelo.
- **`confianza`** (`04`): la confianza declarada separa poco aciertos de fallos (60,6 frente a 50,3, ambas bajo el umbral de 70), con n pequeño y sin repetir. No lo presentes como una demostración de 5.2-K3: la señal de la variante es la tasa de acierto por tipo.
- **El proxy de sentimiento es una inferencia propia:** la lista de palabras la inventó el proyecto. La guía dice que el sentimiento es poco fiable, no que esa lista falle así. La cabecera ya lo dice; mantenlo.
- **La clasificación de «no escala»** incluye pedir un identificador y responder otra cosa, sin distinguirlos. Debe constar como límite en el README.
- **La comprobación de la respuesta de `07`** mira el primer equipo nombrado. Constan en `docs/hallazgos.md` las dos correcciones que hubo.

**Reglas de siempre**
- Regla «una vez»: no muevas ni dupliques ningún `INTRODUCE`; `USA` solo sobre viñetas ya introducidas.
- Textos agnósticos en los documentos versionados: rutas relativas, sin nombres de personas, cuentas ni perfiles.
- Cifras: copia las de `docs/hallazgos.md` y `NOTAS.md`; no calcules otras. Si una cifra no coincide entre los tres sitios (README, hallazgos y NOTAS), no elijas: anótalo al final.
- Carriles de contenido: los rótulos `Producto observado (no evaluable)` y `EN PRODUCCIÓN (no evaluable)` se escriben exactamente así. Nada fuera del perímetro (`tests/perimetro_excluido.yaml`).
- Sin modelo: no ejecutes nada que llame a la API. `uv run pytest -q` en verde y `uv run python datos/generar_sinteticos.py --check` limpio antes de cada commit.

**Commits y cierre**
- Un commit por módulo (cabecera, README y glosario de ese módulo) y uno para `NOTAS.md` y `docs/hallazgos.md`.
- `NOTAS.md`: marca el pase de textos como hecho y deja pendientes la revisión independiente (`docs/prompts-entrega-3/d-revision.md`), sus correcciones, la fusión y el roadmap origen.
- Informe final: commits, qué viñetas quedaron mejor o peor respaldadas por la guía, discrepancias de cifras y cambios de código que los textos piden y no hiciste.
