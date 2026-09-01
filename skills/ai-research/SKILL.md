---
name: ai-research
description: Úsalo cuando la respuesta vive fuera de este repositorio — "what does the state of the art say", "compare the options for", "find sources on", "is this still true", "what do the docs say about" — para traer evidencia con citas numeradas o dejar la claim marcada [unsourced], usando solo las tools que el cliente tiene: lo ausente se degrada y se nombra, nunca error. Not for respuestas que están en el árbol (/ai-explore) ni para diagnosticar un fallo (/ai-debug).
license: Apache-2.0
---

# ai-research

Evidencia de fuera del repositorio con citas numeradas o marcada `[unsourced]`, sobre la
escalera de tools que el cliente tiene: suelo local siempre, web solo si está configurada,
NotebookLM solo si `notebooklm doctor` pasa. Una tool ausente se nombra como
`degraded-tool` y se sigue — nunca bloquea. Cierra con tres direcciones citadas.

## Lo que trae la fuente

- Método completo: la escalera (local / web condicional / NotebookLM condicional), decir qué cambiaría con la respuesta, fuente primaria sobre blog, fecha todo, no resolver desacuerdos en silencio, `[unsourced]` que se queda, y las tres direcciones citadas del cierre → [ai-research-SKILL.md](ai-research-SKILL.md)
- Corpus de ruteo: qué frases llegan aquí y qué se rechaza (ruta en el árbol → /ai-explore, diagnóstico → /ai-debug, decidir qué construir → /ai-spec, hallazgo propio → /ai-note) → [corpus.md](corpus.md)

Fuente: ai-engineering v1 (propio), Apache-2.0.

## Lo que añade ai-engineering (la costura):

1. Salida: `.ai-engineering/research/NNN-{name}.html` con citas numeradas y branding §22
   (#0B1120 fondo / #00D4AA acento / #F8FAFB texto) — el informe debe parecerse al
   blueprint, no a un export. La carpeta es plana: `NNN` de tres dígitos, nunca subcarpeta.
2. Alimenta existence-check y prior-art de ai-architect: su evidencia es lo que un PR de
   arquitectura cita antes de construir algo que ya existe.
