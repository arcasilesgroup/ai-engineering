---
name: ai-goal
description: Úsalo cuando el usuario quiere construir en bucle autónomo — "loop this feature", "run these overnight", "write the goal for this" — fijando el contrato del loop: qué consume, qué gates cierra, cuándo para y qué reporta, sin reimplementar nunca el bucle en sí.
license: MIT
---

# ai-goal — el contrato del bucle (Loop Engineering)

El bucle NO se reimplementa: lo corre el goal nativo de la superficie. Esta skill fija el contrato del bucle a partir de tres skills fuente que cubren el método completo: setup de feature con dos paradas humanas (mock y aprobación), condición de goal para un feature, y batch en cola nocturna.

- Setup del feature: carpeta, mock aprobado, spec re-entrante → [new-feature/SKILL.md](new-feature/SKILL.md)
- La condición `/goal` para un feature: pointer, reporting clause, met condition → [goal-writer/SKILL.md](goal-writer/SKILL.md)
- Cola de varios features con subagent builder + adversary verificador → [feature-batch/SKILL.md](feature-batch/SKILL.md)
- El batch usa el agente verificador adversary (frío, sin herramientas de edición) → [agents/adversary.md](agents/adversary.md)
- Fuente: Loop-Engineering, repo de demo Loop Salon; método del bucle en sus skills `.agents/skills/` (attributed — sin autor ni URL declarados en la fuente; candidato issue H4). Otra copia en Downloads, `loop-engineering-2/`, contiene solo ai-slop-detector (ruta por ai-design, no método de bucle).

Lo que añade ai-engineering (la costura):

1. El bucle NO se reimplementa: lo corre el goal nativo de la superficie. ai-goal fija el contrato.
2. Consume plan.html, cierra gates de spec.html con receipt.
3. Las 3 paradas del §5.1 como condiciones de salida: contrato aprobado / loop guard / destructivo+presupuesto.
4. Presupuesto de config.toml.
5. Reporte = ai-visual-recap.
6. Criterio «suficiente» = ponytail/KISS.
