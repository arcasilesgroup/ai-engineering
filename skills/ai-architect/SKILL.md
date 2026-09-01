---
name: ai-architect
description: Úsalo antes de construir, a mitad de build o al acabar — "cómo abordo este proyecto", "elige el stack", "revisión de arquitectura", "check prior art" — para investigar comparables, costes de operación y opciones de stack, y recomendar el camino de mayor palanca, con deep-dive opcional de prior art en arXiv tras su gate.
license: MIT
---

# ai-architect — estrategia de proyecto y arquitectura (headstart)

Automatiza el loop de investigación que un ingeniero fuerte haría a mano: enmarcar el objetivo, inspeccionar evidencia existente, estudiar comparables creíbles, evaluar stack y arquitectura, recomendar el camino de mayor palanca. Tres modos: pre-build, corrección a mitad de build, revisión post-build. El deep-dive de prior art arXiv tiene gate propio y está off por defecto.

- Método completo: modos, intake, hard gates, workflow, costes, tradeoffs → [headstart-SKILL.md](headstart-SKILL.md)
- Loop de prior art arXiv (solo tras su gate) → [references/arxiv-prior-art.md](references/arxiv-prior-art.md)
- Config de agente OpenAI → [agents/openai.yaml](agents/openai.yaml)

Fuente: headstart (MIT, licencia declarada en su SKILL.md; sin fichero LICENSE en la fuente).

Lo que añade ai-engineering (la costura):

1. La propuesta de capas se expresa como diff de `.ai-engineering/arch.rules.json` en un PR — nunca auto-escribe.
2. Tiers de modelo del pin.
3. Existence-check + prior-art antes de construir.
