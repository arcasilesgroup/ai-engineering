# Adversarial review — viewer-audit#3

## Goal
At 320px seven journey dots (diameters 27/32/37/37/42/42/47) fit the content row with connector min-width 4px and no document sideways scroll; .tech>summary has padding-block 13px (≥44px hit); tech details marked data-region tech-details; labels match the prototype; planted viewer stays identical.

## Acceptance
- At 320 with a seven-step plan, documentElement.scrollWidth equals clientWidth; journey connectors may be 4px.
- Technical details summary hit box is at least 44px tall via padding-block 13px.
- Dot diameters remain 27/32/37/42/47; planted viewer identical to template.

## changed_files
- templates/viewer.html.tpl
- .ai-engineering/workflow/checkpoints/viewer.html
- tests/viewer-audit.spec.ts

## verify
- bun test tests/viewer-audit.spec.ts
- bun run typecheck
- bun run lint

## Thread

### Coordinator note (2026-09-26)
Adversarial-reviewer / fixer Task calls blocked by Cursor usage limits. Coordinator ran verify + acceptance spot-check instead of a debate.

**Evidence:** 22/22 viewer-audit tests; typecheck/lint clean for this change set; `cmp` template === planted; CSS has `min-width:4px`, `padding-block:13px`, `data-region="tech-details"`; diameter comment restored next to `SIZES`.

**VERDICT: PASS** (degraded path — no multi-round adversarial debate)
