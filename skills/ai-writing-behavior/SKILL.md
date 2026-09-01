---
name: ai-writing-behavior
description: Úsalo cuando un fallo recurrente en trayectorias merece criterio — para autorar, revisar, partir, agrupar o calibrar specs de comportamiento (BEHAVIOR.md) que capturan conducta recurrente y juzgable, o para traducir fallos de traza y guía de runtime en behaviors duraderos. Not for puntuar una trayectoria ya terminada ni para escribir un prompt de runtime.
license: Apache-2.0
---

# ai-writing-behavior

Autoría del formato Agent Behavior (BEHAVIOR.md): el spec más pequeño y durable que deja
distinguir conducta aceptable de inaceptable sobre trayectorias reales. Criterio para
jueces y evals, no prompt de runtime.

## Lo que trae la fuente

- Método íntegro: partir de evidencia de traza, decidir si el comportamiento merece spec (set escaso de alto impacto, no inventario de instrucciones), elegir la unidad (agrupar/split), escribir el spec para un frío lector con la trayectoria, y mantener la conducta observada separada de la instrucción → [writing-agent-behavior-SKILL.md](writing-agent-behavior-SKILL.md)
- Spec del formato embebida — el contrato completo de BEHAVIOR.md, autocontenida, sin red → [references/agent-behavior-specification.md](references/agent-behavior-specification.md)
- Decidir qué guardar → [references/deciding-what-to-save.md](references/deciding-what-to-save.md) · calibrar contra trayectorias positive / negative / outside-scope / lucky-correct → [references/calibrating-with-trajectories.md](references/calibrating-with-trajectories.md)

Fuente: braintrustdata/agentbehavior (Braintrust + Basis), Apache-2.0 —
https://github.com/braintrustdata/agentbehavior

## Lo que añade ai-engineering (la costura):

1. Salida: `.agents/behaviors/<name>/BEHAVIOR.md` — en la RAÍZ, no en `.ai-engineering/`
   (lo lee medio mundo: revisores humanos, jueces de eval, otras herramientas; ai-eng solo
   valida). Bajo demanda (19.º skill del canon).
2. En eval observacional el agente evaluado está ciego al spec: enseñárselo antes mediría
   obediencia, no conducta.
3. spec.html pregunta «¿se cumplió el hito?» (binario, CI); BEHAVIOR.md pregunta «¿se
   comportó bien el agente?» (puntuado 0–1, tendencial, jamás gate).
