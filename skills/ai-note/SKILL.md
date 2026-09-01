---
name: ai-note
description: Úsalo cuando un hallazgo costó tiempo real — un comportamiento no obvio, una trampa de integración, un workaround y por qué hace falta — para guardarlo como hallazgo persistente del equipo, sellado con commit y patrones de ficheros para poder detectar su putrefacción, y para buscar notas anteriores. Not for decisiones de proyecto (/ai-spec) ni para documentación que alguien lee para aprender el sistema (/ai-write).
license: Apache-2.0
---

# ai-note

Guarda lo que costó descubrir: un hallazgo sellado con commit y con los ficheros que
describe, en tres partes (qué esperabas, qué pasó, qué hacer), con la evidencia que permite
re-verificarlo. La barra son treinta minutos; una nota falsa es peor que ninguna.

## Lo que trae la fuente

- Método completo: la barra de treinta minutos, el header que hace la nota checkable (`found` / `commit` / `describes` / `still_true_when`), las tres partes y ninguna más, señalar la evidencia, qué eliminaría la necesidad de un workaround, búsqueda con `git grep` sobre las notas, borrar en un commit que diga por qué → [ai-note-SKILL.md](ai-note-SKILL.md)
- Corpus de ruteo: frases que disparan el skill («save this», «lo perdimos una tarde»…) y las que rechaza (decisión → /ai-spec, onboarding → /ai-explore, mirar si el vendor lo arregló → /ai-research, diagnóstico → /ai-debug, PR → /ai-ship) → [corpus.md](corpus.md)

Fuente: ai-engineering v1 (propio), Apache-2.0.

## Lo que añade ai-engineering (la costura):

1. Escribe bloque en DECISIONS.md o lo entrega a ai-write — NO crea archivo propio: el
   método viaja íntegro, pero la salida vive donde alguien la releerá, no en un
   `docs/notes/` que nadie vuelve a abrir. Un hallazgo sin casa en DECISIONS/docs es un
   hallazgo que nadie releerá.
