# Adoption Sub-Spec S4 — Skill Consolidation + Architecture Thinking Integration

**Discovery Date**: 2026-04-24
**Context**: Diagnóstico ai-engineering v4 adoption. 47 skills con 40-60% restatement de framework rules. `/ai-design` opt-in only (no se enruta desde plan/brainstorm). Architecture thinking **0 hits** en toda la base de skills. Usuario quiere: wirear `/ai-design` siempre, integrar architecture-patterns de `https://skills.sh/wshobson/agents/architecture-patterns`, pasar `skill-creator` (Anthropic) eval sobre cada skill. Backlog post-S1.
**Spec**: backlog — pendiente spec formal

## Problem

Cinco issues entrelazados:

1. **Duplicación orchestrators**: `dispatch/autopilot/run` repiten ~35% del kernel build-verify-review-pr.
2. **ai-commit ⊂ ai-pr al 50%**: PR inline-duplica todo el protocolo commit en lugar de delegar.
3. **`/ai-design` opt-in only**: no se enruta desde plan/brainstorm cuando el spec tiene UI.
4. **Architecture thinking ausente**: 0 hits para "architecture-patterns", "pattern library", "architecture patterns" en 47 SKILL.md.
5. **Verbosity 40-60%** en top 5 skills, restatement de reglas ya en CLAUDE.md.

Orphans: `/ai-analyze-permissions` (0 inbound), `/ai-video-editing` (0 inbound).

## Findings

### Counts verified
- 47 skills, 10 agents (+16 specialists) — concuerda con CLAUDE.md.

### High fan-in nodes
`/ai-pr` (44 refs), `/ai-dispatch` (39), `/ai-docs` (37), `/ai-verify` (29), `/ai-governance` (28).

### Duplicación hotspots
| Par | Overlap | Consolidación |
|---|---|---|
| ai-commit ⊂ ai-pr | 50% | `/ai-pr` → `calls: /ai-commit` en lugar de re-inline |
| dispatch/autopilot/run | 35% | extraer `handlers/execution-kernel.md` compartido |
| verify vs review | 40% | boundary explícito en description ("evidence" vs "narrative") |
| brainstorm ↔ plan | 25% mutual ref | romper circular: plan delega sólo si hay unknowns |
| note vs write vs docs | 20% | bajo riesgo; ya bien separados |
| explain vs guide | 30% | routing check por intent |

### Verbosity top 5
| Skill | Líneas | % restatement |
|---|---|---|
| ai-animation | 243 | ~55% |
| ai-skill-evolve | 213 | ~60% |
| ai-pr | 221 | ~50% |
| ai-video-editing | 200 | ~65% |
| ai-instinct | 179 | ~45% |

### `/ai-design` inbound
- Llamado por: usuario directo, ai-animation (mención), ai-canvas (mención)
- NO llamado por: ai-brainstorm, ai-plan, ai-dispatch, ai-autopilot, ai-run
- Keyword "design" 0 hits en process steps de brainstorm/plan

### Architecture thinking
- 0 hits "architecture-patterns", "pattern library", "architecture patterns" en 47 SKILL.md
- Único touchpoint: `verifier-architecture.md` post-hoc (después de build)
- No existe `.ai-engineering/{contexts}/architecture-patterns_PLACEHOLDER`

## Code Examples

### 1. Execution kernel compartido
```markdown
# .claude/{skills}/_shared/execution-kernel_PLACEHOLDER (nuevo o dentro de ai-dispatch/handlers/)

## Kernel: dispatch agent per task → build-verify-review loop → artifact collection → board sync

Importado por:
- ai-dispatch/SKILL.md step 3+
- ai-autopilot/SKILL.md wave execution
- ai-run/SKILL.md backlog executor
```

### 2. Wire `/ai-design` into `/ai-plan`
```markdown
# .claude/{skills}/ai-plan/handlers/design-routing_PLACEHOLDER (nuevo)

Detectar UI/frontend por keywords: "page", "component", "screen", "dashboard",
"form", "modal", "design system", "color palette".

Si detectado → route through /ai-design BEFORE task decomposition.
Output: design-intent.md referenced in plan.md under "Design" section.
Task graph incluye design tasks.
Else → skip routing.
```

### 3. Architecture patterns context
```markdown
# .ai-engineering/{contexts}/architecture-patterns_PLACEHOLDER (nuevo)

Curated de https://skills.sh/wshobson/agents/architecture-patterns.
Patterns: layered, hexagonal, CQRS, event-sourcing, ports-and-adapters,
clean-architecture, pipes-and-filters, repository, unit-of-work, ...

# .claude/skills/ai-plan/SKILL.md step nuevo (antes de task decomposition):
"Read {contexts}/architecture-patterns_PLACEHOLDER. Identify fitting pattern.
Record in plan.md under '## Architecture' with justification.
If none applicable → note 'ad-hoc' with explanation."
```

### 4. skill-creator eval loop
```bash
# scripts/skill-audit.sh (nuevo)
for skill in .claude/skills/ai-*/SKILL.md; do
  ai-eng skill eval "$skill" \
    --creator-ref "$(which skill-creator || echo anthropic-skill-creator)" \
    --threshold 80 \
    --json >> audit-report.json
done
# Output: skills < threshold → refactor candidates
# Dimensiones: triggering-accuracy, boundary-clarity, verbosity, wire-integrity
```

### 5. Restatement cleanup pattern
```markdown
# Antes (ai-commit/SKILL.md:16)
"NEVER uses --no-verify on any git command (respects CLAUDE.md Don't)."

# Después
"Honors CLAUDE.md Don't rules (binding)."

# Ahorro ~8-10 líneas × 47 skills = ~400 líneas
```

## Pitfalls

- Shared handler debe mirrorse a Claude/Copilot/Codex/Gemini — verificar `scripts/sync_command_mirrors.py` lo copia.
- `/ai-design` routing auto puede dar false-positive en specs non-UI → keyword allowlist + override flag `--skip-design`.
- Architecture-patterns context puede inflar prompts. Estrategia: **NO cargar siempre**; solo cuando `plan.md` lo referencia explícitamente.
- skill-creator threshold ≥80% — skills legacy probablemente no pasan al inicio. Strategy: warning-only en primera iteración, hard-gate cuando >90% skills cumplen.
- NO consolidar verify/review sin medir — el user ya entiende la boundary actual; cambiar routing puede confundir.
- Verbose cleanup NO debe borrar guidance único — solo duplicación de CLAUDE.md / Don't rules.

## Related

- Diagnóstico Wave 1 Agent A4 en brainstorm 2026-04-24.
- External ref: `https://skills.sh/wshobson/agents/architecture-patterns` (WebFetch pendiente al escribir spec).
- Skill local disponible: `skill-creator` (Anthropic) — ver SKILL en la lista de skills.
- Transversal con S2/S3/S5.
- Files candidatos:
  - `.claude/skills/ai-dispatch/`, `ai-autopilot/`, `ai-run/` — extraer kernel
  - `.claude/skills/ai-plan/SKILL.md`, `ai-brainstorm/SKILL.md` — design routing + architecture step
  - `.ai-engineering/{contexts}/architecture-patterns_PLACEHOLDER` (nuevo)
  - 47× `.claude/skills/ai-*/SKILL.md` (restatement cleanup via skill-creator eval)
  - `scripts/skill-audit.sh` (nuevo)
  - `scripts/sync_command_mirrors.py` (asegurar handlers compartidos se mirrorian)
