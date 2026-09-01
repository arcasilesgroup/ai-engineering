---
name: ai-plan
description: Úsalo cuando la idea ya está alineada pero el camino no se ve — "work out what we're building", "aclara qué es done" — respondiendo una pregunta a la vez y convirtiendo cada respuesta en un check, para terminar con una answer-key escrita que define "done and right", no solo un plan.
license: MIT
---

# ai-plan — de preguntas a checks ejecutables (wayfinder)

El output no es un plan de construcción: es una answer-key, el estándar escrito para juzgar si lo terminado salió bien, con la lista honesta de lo que nadie ha decidido. Grilling, research y prototype como tipos de pregunta; cada respuesta produce un check binario.

- Método completo: mapa, tipos de pregunta, checks, fog, out-of-scope → [wayfinder-SKILL.md](wayfinder-SKILL.md)
- Interrogación de grilling → [commands/grill.md](commands/grill.md)
- Prototipado reactivo → [commands/prototype.md](commands/prototype.md)
- Emisión de la answer key → [commands/to-bar.md](commands/to-bar.md)
- Config de agente OpenAI → [agents/openai.yaml](agents/openai.yaml)

Fuente: wayfinder, adaptado de Matt Pocock — https://github.com/mattpocock/skills (MIT; la adaptación answer-key no es parte de su diseño y no cuenta con su endoso).

Lo que añade ai-engineering (la costura):

1. Los checks salen en formato gates de unlazy con nombre `spec.html` (QUÉ) + `plan.html` (CÓMO: pasos→gates, dependencias, Jobs).
2. ≤30 gates por hito. «Check que no corre = FAIL».
3. `ai-eng spec open` reclama el slot antes de escribir.
