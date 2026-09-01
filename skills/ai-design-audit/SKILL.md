---
name: ai-design-audit
description: Trigger for auditing a rendered web UI for visual defects with measurements rather than opinions — misaligned rows, ragged card interiors, touch targets, rendered contrast over gradients and images, text printing over text, Gestalt proximity, divider lines that should be space, type-scale drift — measured in a real browser across widths, and proved unchanged afterwards.
license: UNLICENSED
---

# ai-design-audit

Una stylesheet es una afirmación; el pixel pintado es la evidencia. Mide lo segundo:
contraste renderizado sobre degradados, filas cuyas tarjetas no arrancan alineadas, glifos
que se imprimen sobre glifos, proximidad que agrupa lo que no debe. Sirve el output
construido y apunta el audit ahí — un dev server mide una página que nadie visita.

## Lo que trae la fuente

- Método completo: las 6 pasadas (`geometry contrast collision proximity type interior`), el loop medir → juzgar → arreglar → probar con baseline, cómo leer el output (falsos positivos que parecen defectos), patrones de fix que no mueven un glifo, y lo que los números no ven → [ai-design-audit-SKILL.md](ai-design-audit-SKILL.md)
- Auditor medido: 886 líneas que corren en un browser real a varias anchuras → [scripts/audit.mjs](scripts/audit.mjs)
- Cómo juzgar cada pasada y sus falsos positivos → [references/reading.md](references/reading.md) · patrones de fix que cambian un gap sin mover un glifo → [references/fixes.md](references/fixes.md)
- Manifiesto de interfaz del agente (display, prompt por defecto) → [agents/openai.yaml](agents/openai.yaml)

Fuente: skill instalado de la comunidad, sin licencia (contactado, issue H4) — integrado
con atribución mientras llega.

## Lo que añade ai-engineering (la costura):

1. Gate anti-slop ejecutable que ai-design rutea — nunca bundleado, apuntando a lo
   instalado en runtime.
2. Resultado: `.ai-engineering/design/audits/NNN-{name}.html` — medidas, no opiniones; el
   NNN no se reescribe.
3. Formato de salida: gates (CHECK / EXPECT / EVIDENCE).
