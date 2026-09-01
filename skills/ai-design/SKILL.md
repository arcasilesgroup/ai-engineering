---
name: ai-design
description: Úsalo al inicio de cualquier petición de build, redesign, estilo, animación, review o explicación de una interfaz — "build a page", "make this look good", "add motion" — para elegir el lead correcto entre las skills de diseño instaladas, adjuntar consultores por parte nombrada, secuenciar fases, resolver conflictos y correr los gates de cierre.
license: MIT
---

# ai-design — orquestador de routing de diseño (design-orchestrator)

El controlador de tráfico: no diseña. Decide quién lidera, quién aconseja, en qué orden y quién gana una discrepancia, y entrega. Elige exactamente un Lead por restricción dominante de la petición, no por vocabulario, y resuelve pares confusos con discriminadores explícitos.

- Router completo: 3 hechos, constraint→lead, fast path, consultores, ingredientes, fases, gates → [design-orchestrator-SKILL.md](design-orchestrator-SKILL.md)
- Qué es cada skill: el modelo de routing real → [references/skill-purposes.md](references/skill-purposes.md)
- Qué parte de cada skill abrir una vez elegida → [references/routing-table.md](references/routing-table.md)
- Reglas de precedencia y tiebreakers → [references/conflicts.md](references/conflicts.md)
- Planes trabajados para las doce formas de petición comunes → [references/plans.md](references/plans.md)

Fuente: design-orchestrator de la colección claude-design-skills (attributed; sin licencia — issue H4).

Lo que añade ai-engineering (la costura):

1. La routing-table apunta a lo instalado en runtime; nunca bundlea.
2. Escribe `.ai-engineering/design/direction.html` ANTES de código.
3. El gate anti-slop es ai-slop-detector ruteado, no bundleado.
4. Escalera de conflictos propia intacta.
