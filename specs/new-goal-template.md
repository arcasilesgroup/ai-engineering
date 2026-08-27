# Template de prompt inicial — ai-engineering (spec 037 / B-037-3)

Copia y pega este bloque como tu primer prompt de un goal nuevo. `validate_intake` comprueba
que las tres partes están: **Goal**, **Constraints**, **Acceptance**. Una petición libre y
bien formada que las nombre también sirve; este es el formato de referencia.

---

**Goal:** [una frase: qué quieres conseguir — el resultado, no cómo]

**Constraints:** [qué no puede romperse, dependencias prohibidas, límites, deadlines]

**Acceptance:** [cómo sabremos que está hecho — criterio observable, test, comando]

---

## Ejemplo (este ejemplo la valida end to end)

**Goal:** add rate limiting to the public API.

**Constraints:** must not break existing clients; no new dependency.

**Acceptance:** tests pass and the quota header is set.