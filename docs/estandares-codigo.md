# Estándares de código

Importado por `CLAUDE.md`. Se aplica a todo el proyecto; lo específico de un tipo de archivo vive en `.claude/rules/`.

## Idioma y nombres

- Comentarios en español e identificadores en inglés.

## Cabeceras

- **Módulo de app:** `CONCEPTO [TS x.y-Kn/Sn]` · `QUÉ DICE LA GUÍA` · `POR QUÉ IMPORTA` · `ANTI-PATRÓN / TRAMPA DEL EXAMEN`.
- **Infraestructura** (`harness/`, `datos/`, `.claude/hooks/`, tests): `PROPÓSITO` · `POR QUÉ EXISTE` · `QUÉ NO HACE`.
- Cada acción no trivial lleva un comentario que explica qué hace y por qué.

## Regla «una vez»

- Cada viñeta tiene un único marcador `INTRODUCE` en el destino que asigna `CONCEPTOS.md`. Después, solo `USA`.
- En Python va como `#`; en Markdown, como comentario HTML; en frontmatter, como comentario YAML.
- Un `USA` solo vale sobre una viñeta ya introducida. Mientras no lo esté, se cita en prosa («ver TS 1.4-K1») y se convierte en el mismo cambio que la introduce.
- Al añadir un `INTRODUCE`, en el mismo cambio se marca ☑ la fila de `CONCEPTOS.md` y se actualiza su contador. Lo comprueba `tests/test_una_vez.py`.

## Perímetro de la guía

- Solo los mecanismos que nombra la Exam Guide v1.0. Lo más nuevo, como mucho, en un comentario `EN PRODUCCIÓN (no evaluable)`.
- La lista de exclusión es `tests/perimetro_excluido.yaml` y la comprueba `tests/test_perimetro.py`.
- `claude-agent-sdk` está fijado en `pyproject.toml` y solo se actualiza de forma deliberada.

## Ejecución con modelo

- `ClaudeAgentOptions` se construye con `harness/options.py`, que aplica el aislamiento (`setting_sources=[]`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `ENABLE_CLAUDEAI_MCP_SERVERS=false`) y exige `max_budget_usd`.
- Las opciones quedan visibles en el módulo.
- `max_turns` es solo una red de seguridad, nunca el mecanismo de parada.

## Datos

- Siempre sintéticos.
- `datos/sinteticos/` solo se cambia editando y ejecutando `datos/generar_sinteticos.py`. Un hook bloquea la edición directa.
- No se copia texto de la guía oficial ni preguntas reales del examen.
