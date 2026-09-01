---
name: ai-proof
description: Úsalo cuando el trabajo vuelve a mitad de hacer, cuando el agente reporta "done" antes de estar done, o en runs largos que se estancan al 80% — descompone el trabajo en un Depth Tree de hojas con gates ejecutables y prueba la completitud con un ledger, nunca con promesas. Trigger for "unlazy", "tree N", "gates" o "do not stop until it is done".
license: MIT
---

# ai-proof — disciplina anti-pereza v2 (unlazy)

Prueba de completitud mediante gates en ficheros y checks ejecutables: el agente no promete que acabó, lo demuestra contra un ledger. Método central: el Depth Tree de Leonxlnx, que descompone el trabajo en hojas que cada una termina contra sus propios gates.

- Método v2 y regla cero (gates antes del trabajo) → [unlazy-SKILL.md](unlazy-SKILL.md)
- Decomposición en árbol y estructura de hojas → [references/method.md](references/method.md)
- Modo orquestado: subagents por hoja, verificación en jerarquía → [references/orchestration.md](references/orchestration.md)
- Formato de gates para hojas y nodos internos → [references/gates.md](references/gates.md)
- Economía de tokens: disciplina casi gratis → [references/token-economy.md](references/token-economy.md)
- Plantillas: plan por hojas, gates de hoja, gates de nodo → [templates/PLAN.md](templates/PLAN.md), [templates/gates-leaf.md](templates/gates-leaf.md), [templates/gates-node.md](templates/gates-node.md)
- Chequeo ejecutable de gates → [scripts/gate-check.mjs](scripts/gate-check.mjs)
- Stop hook de Claude Code (instalación opt-in) → [scripts/install-hooks.mjs](scripts/install-hooks.mjs), [scripts/stop-hook.mjs](scripts/stop-hook.mjs)

Fuente: unlazy v2.1.0 por Leonxlnx — https://github.com/Leonxlnx/unlazy (MIT).

Lo que añade ai-engineering (la costura):

1. El fichero de gates del hito se llama `.ai-engineering/spec.html` (no GATES.md) porque es el contrato que verifica la CI.
2. Correrlos: `ai-eng spec run` = envoltorio de scripts/gate-check.mjs + exit≠0 si un check no pudo ejecutarse + receipt por corrida.
3. Quién verifica: tier `verify` del pin (§09.4); quién juzga en orchestrated: tier `decide`.
4. stop-hook.mjs solo en Pi/Zed — el loop guard cubre ese fallo en las 3 core.
