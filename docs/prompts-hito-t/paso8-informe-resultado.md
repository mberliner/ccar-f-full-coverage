# Paso 8 · Informe de la prueba de usabilidad

Resultado de aplicar `paso8-prueba-usuario.md` con una participante real. Sin propuestas de arreglo: la corrección se hace en otra sesión.

```
Perfil: Python ninguna · terminal mucha · agentes algo · API key sí
Caso 1 (app1/05, ligero): 1.1 con ayuda (2) · 1.2 parcial, sin ayuda · 1.3 no · valoración 1/7 · tiempo no cronometrado
Caso 2 (app3/02 paralelo): 2.1 éxito · 2.2 éxito · 2.3 parcial · valoración 2/7 · tiempo no cronometrado
Autonomía (cierre, 5): 2/7
```

## Problemas de usabilidad, por gravedad

**Bloquea**
- `README.md` raíz, «Cómo se usa» y `app1_agente_unico/README.md`, `## 05` · No hay forma de saber por dónde empezar. Abrió primero el `.py` del módulo. Cita: «sin leerlo todo no entiendo qué hacer». Ayuda: **sí**, dos veces (a «Por dónde empezar» y a «Cómo se usa»).

**Frena**
- `README.md` raíz, «Por dónde empezar» · Dijo que no existía: estaba mirando el README de `app1`. El título no la llevó a la sección. Ayuda: no (comprobado en el repositorio).
- `README.md` raíz, «Cómo se usa» · No la leyó porque está encima de «Por dónde empezar». Al leerla, no define «módulo». Cita: «no dice que es un módulo pero hay que elegirlo». Ayuda: no.
- `app1/README.md`, `## 05`, «El ejercicio» · Cita: «no tengo un planteo claro de la situación completa». Se preguntó si necesitaba los módulos 1 a 4. No encontró la consigna al principio. Ayuda: no.
- `app1/README.md`, `## 05` · No quedó claro qué es ejecución ligera. En 1.2 predijo sin saber que no debía ejecutar; en 1.3 ejecutó `--parte tool_choice --repeat 6` con modelo. Ayuda: no.
- `README.md` raíz, «Primeros pasos» y «Flujo de trabajo para añadir un módulo» · Le parecieron un exceso con el entorno ya montado. Cita: «un exceso si ya está hecho aquí en este PC». Ayuda: no.
- `app1/README.md`, `## 05` y `app3/README.md`, `## 02` · Confusión al contrastar. Pensaba abrir «la respuesta» y no el «Resultado de referencia». En 1.3 eligió B sin abrir ningún bloque. En el caso 2 abrió solo la respuesta. Ayuda: no.

**Molesta**
- «Cómo se usa», paso 3 · Cita: «no dice cómo ejecutarlo sin `--anti`». Ayuda: no.
- README raíz y de las apps · Términos que no entendió o tuvo que buscar: «modo» (lo resolvió buscando la palabra en el README), «predicciones (¿de qué?)», «cabecera del módulo», «responder la pregunta (¿dónde?)», «verificar concepto (¿para qué?)».
- No mencionó `FALLOS.md` en ningún momento al hablar de qué hacer con una predicción fallida.
- `app3/README.md`, `## 02` · No consultó «Qué observar» ni el coste. Cita: «el budget no es significativo». Sin problema de credencial (ya configurada).

## Lo que funcionó

- Buscar la palabra «modo» en el README le resolvió el término.
- Tras el caso 1 fue directa a la app 3, sección `## 02`.
- Entendió coordinador, subagente y respuesta del coordinador.
- Predijo un patrón y no una cifra exacta («no se acelera ×3»).
- Eligió el comando correcto sin `--anti`.
- Su ×1.99 le pareció normal, sin sospechar un fallo.
- Valoró bien el «resultado de referencia» plegado: «eso está bien».

## Respuestas del cierre

1. **Lo más confuso:** «no tener un contexto general de qué estamos haciendo; debería ser narrado por un asistente y no leído a trompicones».
2. **Momentos sin saber qué hacer:** «muchos momentos, en el 1 casi todo el tiempo».
3. **Términos:** «modo».
4. **Texto que da la respuesta antes de tiempo:** no.
5. **Autonomía (1 = no podría, 7 = podría sola):** 2/7.
