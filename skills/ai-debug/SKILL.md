---
name: ai-debug
description: Úsalo cuando algo se rompe o dejó de funcionar — "it's not working", "this used to work", "I'm getting an error", "CI is failing", "why is X happening", "I have conflicts", "the rebase failed" — para reproducir el fallo, nombrar la causa a file:line y escribir el check que falla por ella antes de tocar nada. Not for añadir cobertura a código que funciona (/ai-review) ni para explorar un área desconocida (/ai-explore).
license: Apache-2.0
---

# ai-debug

Encuentra la causa raíz de un comportamiento roto y la nombra a `file:line`, luego escribe
el check que falla por esa razón antes de cambiar nada. También resuelve conflictos de
merge y rebase por intención, no tomando partido.

## Lo que trae la fuente

- Método completo: reproducir antes de adivinar, leer la salida fallida completa (el primer error es el real), causa que se puede señalar (`file:line` + una frase de por qué), el check antes del fix, arreglar donde pasan todos los callers, la regla de las dos intentos, conflictos leídos por intención (lockfiles se regeneran, migraciones se ordenan) → [ai-debug-SKILL.md](ai-debug-SKILL.md)
- Corpus de ruteo: frases que disparan el skill y las que rechaza (cobertura de tests → /ai-review, tour de código → /ai-explore, diseñar el fix → /ai-plan, evidencia externa → /ai-research, guardar el hallazgo → /ai-note, abrir PR → /ai-ship) → [corpus.md](corpus.md)

Fuente: ai-engineering v1 (propio), Apache-2.0.

## Lo que añade ai-engineering (la costura):

1. El fix no es «hecho» sin el test que lo reproduce y pasa.
2. Bajo demanda: se instala solo si el proyecto lo declara en `config.toml`; el pin de
   modelos y el formato de gates son las únicas uniones.
