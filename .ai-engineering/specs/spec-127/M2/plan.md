---
total: 27
completed: 0
---

# Plan: sub-003 M2 — Description CSO pass + Examples + Integration

## Pipeline: full
## Phases: 8
## Tasks: 27 (build: 22, verify: 5)

## Architecture

**Pattern**: Domain-only edits. Skill/agent description rubric is a content-shape
contract over markdown — hexagonal "domain". Mirrors (`.github/`, `.codex/`,
`.gemini/`) are infrastructure, regenerated mechanically once per milestone.

**Justification**: D-127-08 sets ten-rule bar; sub-002 ships rubric as Python
validator; this milestone drives existing skills + agents through that
validator until exit code zero.

## Design

Skipped — content-shape pass over existing markdown.

## Decomposition Note

Each wave = one ai-build invocation processing 5 skills end-to-end. Per batch:
read SKILL.md → rewrite description CSO → append `## Examples` (≥2) → append
`## Integration` → re-run `skill_lint --check` on those 5 → commit.

### Phase 0: Wave A setup + first batch (Grade D + bottom-5)

**Gate**: 5/10 Wave-A skills ≥B; 0 D in this batch.

- [ ] T-3.1.A1: Wave A batch 1 — rewrite description (CSO third-person, ≥3
  trigger phrases, negative scoping), append `## Examples` (≥2), append
  `## Integration`, on: ai-entropy-gc, ai-instinct, ai-mcp-sentinel, ai-canvas,
  ai-eval (agent: build)
- [ ] T-3.1.V1: `skill_lint --check` on those 5 — expect zero D, zero C
  (agent: verify)

### Phase 1: Wave A batch 2

**Gate**: All 10 Wave-A skills ≥B; zero D remaining anywhere in 50.

- [ ] T-3.1.A2: Wave A batch 2 — same edits, on: ai-run, ai-platform-audit,
  ai-governance, ai-skill-evolve, ai-constitution (agent: build)
- [ ] T-3.1.V2: `skill_lint --check` over all 10 Wave-A — zero D, zero C
  (agent: verify)

### Phase 2: Wave B (Grade C cluster)

**Gate**: 6 Grade-C skills ≥B; full 50 reports zero D, ≤2 C.

- [ ] T-3.2.A1: Wave B batch 1 — same edits, on: ai-cleanup, ai-pipeline,
  ai-board-discover, ai-board-sync, ai-support (agent: build)
- [ ] T-3.2.A2: Wave B batch 2 — same edits, on: ai-resolve-conflicts (single
  skill — cluster size 6 after dedup with Wave A) (agent: build)
- [ ] T-3.2.V1: `skill_lint --check` over full 50 — zero D, ≤2 C (agent: verify)

### Phase 3: Wave C (Grade B → A polish)

**Gate**: 14 Grade-B skills upgraded to A.

- [ ] T-3.3.A1: Wave C batch 1 — append `## Examples` + `## Integration`,
  tighten triggers, on: ai-verify, ai-test, ai-review, ai-write, ai-docs
  (agent: build)
- [ ] T-3.3.A2: Wave C batch 2 — on: ai-board-sync, ai-research, ai-start,
  ai-commit, ai-pr (agent: build)
- [ ] T-3.3.A3: Wave C batch 3 — on: ai-debug, ai-standup, ai-learn, ai-explain
  (4 skills) (agent: build)
- [ ] T-3.3.V1: `skill_lint --check` — zero D, zero C, ≥75 % A (agent: verify)

### Phase 4: Wave D (Grade A polish)

**Gate**: 28 Grade-A skills carry `## Examples` + `## Integration`;
descriptions left intact.

- [ ] T-3.4.A1: Wave D batch 1 — on: ai-plan, ai-prompt, ai-design,
  ai-animation, ai-postmortem (agent: build)
- [ ] T-3.4.A2: Wave D batch 2 — on: ai-autopilot, ai-brainstorm, ai-code,
  ai-create, ai-dispatch (agent: build)
- [ ] T-3.4.A3: Wave D batch 3 — on: ai-guide, ai-market, ai-media, ai-note,
  ai-release-gate (agent: build)
- [ ] T-3.4.A4: Wave D batch 4 — on: ai-schema, ai-security, ai-slides,
  ai-sprint, ai-video-editing (agent: build)
- [ ] T-3.4.A5: Wave D batch 5 — on: ai-analyze-permissions + 4 post-Wave-A
  re-grade polish targets (agent: build)
- [ ] T-3.4.A6: Wave D batch 6 — final 5 post-Wave-A re-grade polish targets
  (agent: build)
- [ ] T-3.4.V1: `skill_lint --check` over all 50 — zero D, zero C, ≥95 % A
  (agent: verify)

### Phase 5: Agent rubric pass

**Gate**: All 26 agent files satisfy parallel rubric.

- [ ] T-3.7.A1: Agent batch 1 — frontmatter CSO + tools + model + dispatch
  comment, on: ai-autopilot, ai-build, ai-explore, ai-guard, ai-guide
  (agent: build)
- [ ] T-3.7.A2: Agent batch 2 — on: ai-plan, ai-review, ai-run-orchestrator
  (flag for M4 deletion), ai-simplify, ai-verify (agent: build)
- [ ] T-3.7.A3: Agent batch 3 — on: review-context-explorer,
  review-finding-validator, reviewer-architecture, reviewer-backend,
  reviewer-compatibility (agent: build)
- [ ] T-3.7.A4: Agent batch 4 — on: reviewer-correctness, reviewer-design
  (flag for M4 deletion), reviewer-frontend, reviewer-maintainability,
  reviewer-performance (agent: build)
- [ ] T-3.7.A5: Agent batch 5 — on: reviewer-security, reviewer-testing,
  verifier-architecture, verifier-feature, verifier-governance,
  verify-deterministic (6) (agent: build)

### Phase 6: Examples + Integration audit

**Gate**: every skill (50) has `## Examples` (≥2) and `## Integration`.

- [ ] T-3.5.V1: `tools/skill_lint --check --section Examples` over all 50 —
  50/50 with ≥2 example blocks (agent: verify)
- [ ] T-3.6.V1: `tools/skill_lint --check --section Integration` over all 50 —
  50/50 with adjacent-skill links (agent: verify)

### Phase 7: Final gate + mirror sync

**Gate**: M2 done conditions met; mirrors regenerated; conformance tests green.

- [ ] T-3.8: Final `skill_lint --check` + parallel agent rubric — zero D, ≤2 C,
  agent rubric all green (agent: verify)
- [ ] T-3.9: `pytest tests/conformance/test_skills_rubric.py
  test_agents_rubric.py` green (agent: verify)
- [ ] T-3.M: Run `python .ai-engineering/scripts/sync_command_mirrors.py`;
  verify proportional churn across `.github/`, `.codex/`, `.gemini/` (agent: build)

## Phase Dependency Graph

```
P0 (Wave A1) ──→ P1 (Wave A2) ──→ P2 (Wave B) ──→ P3 (Wave C) ──→ P4 (Wave D) ──→
P5 (Agents)  ──→ P6 (Audit)  ──→ P7 (Final + mirrors)
```

Waves sequential — each wave's `skill_lint` gate must shift the grade
distribution (D→C→B→A) before next runs.

## Done Conditions

- [ ] `tools/skill_lint --check` exit 0 over all 50 SKILL.md (zero D, ≤2 C)
- [ ] Every skill has `## Examples` (≥2) and `## Integration`
- [ ] All 26 agent files pass parallel rubric
- [ ] `pytest tests/conformance/` green
- [ ] Mirrors regenerated and parity retained
- [ ] No hot-path regression

## Self-Report
[EMPTY -- populated by Phase 4 of /ai-autopilot]
