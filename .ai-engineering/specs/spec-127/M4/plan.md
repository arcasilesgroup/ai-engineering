---
total: 23
completed: 0
---

# Plan: sub-005 M4 — Renames + Mergers

## Pipeline: full
## Phases: 6
## Tasks: 23 (build: 21, verify: 2)

## Architecture

**Pattern**: Pure rename + delete (no aliases per D-127-04). Mirror sync at
end of each rename batch.

**Justification**: D-127-10 final counts (46 skills, 23 agents); D-127-11
`/ai-build` canonical gateway; D-127-12 `/ai-autopilot` single wrapper.
Single commit per rename keeps each rollback unit clean.

## Design

Skipped — file moves + frontmatter edits.

## Phase classification: full

12+ renames, 4 deletions, 3 mergers, mirror regen, count test, CHANGELOG.
Touches 4 IDE surfaces.

### Phase 0: Pre-flight

**Gate**: rename source dirs all present; sub-003 status shipped.

- [ ] T-5.0: Verify sub-003 status `shipped`; confirm rename source dirs all
  present at `.claude/skills/` (agent: verify)

### Phase 1: Skill renames (one commit per rename per D-127-04)

**Gate**: 8 skill dirs renamed; mirrors stay in sync between commits.

- [ ] T-5.1: `git mv .claude/skills/ai-dispatch .claude/skills/ai-build`;
  update SKILL.md `name:`, `.claude/settings.json`, agent pair
  `.claude/agents/ai-build.md` (rename from `ai-dispatch.md`); regen mirrors;
  commit `refactor(skills): rename /ai-dispatch → /ai-build (D-127-11)`
  (agent: build)
- [ ] T-5.2: `ai-canvas` → `ai-visual` (D-127-05); description rewrite per
  D-127-05 (agent: build)
- [ ] T-5.3: `ai-market` → `ai-gtm` (agent: build)
- [ ] T-5.4: `ai-mcp-sentinel` → `ai-mcp-audit` (agent: build)
- [ ] T-5.5: `ai-entropy-gc` → `ai-simplify-sweep` (agent: build)
- [ ] T-5.6: `ai-instinct` → `ai-observe` (agent: build)
- [ ] T-5.7: `ai-skill-evolve` → `ai-skill-tune` (agent: build)
- [ ] T-5.8: `ai-platform-audit` → `ai-ide-audit` (agent: build)

### Phase 2: Skill mergers

**Gate**: 3 mergers complete; functionality preserved via mode flags /
subcommands.

- [ ] T-5.9: Delete `.claude/skills/ai-run/`; add `--backlog` flag to
  `/ai-autopilot` SKILL.md body (D-127-12); update `ai-autopilot` agent to
  accept `--source <github|ado|local>` (agent: build)
- [ ] T-5.10: Merge `ai-board-discover` + `ai-board-sync` →
  `.claude/skills/ai-board/SKILL.md` with `<discover|sync>` subcommands
  (agent: build)
- [ ] T-5.11: Merge `/ai-release-gate` → `/ai-verify --release` mode flag;
  delete `.claude/skills/ai-release-gate/` (agent: build)

### Phase 3: Agent renames + deletions

**Gate**: agent count = 23; orphans removed; renames live.

- [ ] T-5.12: `git mv .claude/agents/review-context-explorer.md
  reviewer-context.md`; update frontmatter `name:`; update dispatch refs in
  `.claude/skills/ai-review/SKILL.md` (agent: build)
- [ ] T-5.13: `review-finding-validator.md` → `reviewer-validator.md`
  (agent: build)
- [ ] T-5.14: Delete `.claude/agents/ai-run-orchestrator.md`; update
  `ai-autopilot` agent to absorb (agent: build)
- [ ] T-5.15: Delete `.claude/agents/reviewer-design.md`; merge design-system
  rules into `reviewer-frontend.md` body (agent: build)

### Phase 4: `/ai-help` matchback + mirror regen

**Gate**: `/ai-help` suggests new names; mirrors regenerated.

- [ ] T-5.16: Update `.claude/skills/ai-help/SKILL.md` — add matchback-suggest
  lookup table `{legacy: new}` (≤30 LOC addition) (agent: build)
- [ ] T-5.17: Run `python .ai-engineering/scripts/sync_command_mirrors.py`;
  verify `.github/`, `.codex/`, `.gemini/` regenerated proportionally
  (agent: build)

### Phase 5: Count parity (TDD pair) + CHANGELOG

**Gate**: skill count = 46, agent count = 23 across all 4 mirror trees.

- [ ] T-5.18: Failing test `tests/mirrors/test_count_parity.py` asserting
  skill count = 46 + agent count = 23 across `.claude/`, `.github/`, `.codex/`,
  `.gemini/` (agent: build)
- [ ] T-5.19: Verify `tests/mirrors/test_count_parity.py` green. **DO NOT
  modify test_count_parity.py from T-5.18.** (agent: verify)
- [ ] T-5.20: Update `CHANGELOG.md` with rename table + deletion list (M4
  section) (agent: build)

## Phase Dependency Graph

```
P0 ──→ P1 (8 renames, sequential commits) ──→ P2 (mergers) ──→ P3 (agent ops) ──→ P4 (help + mirrors) ──→ P5 (count parity + CHANGELOG)
```

P1 commits sequential per D-127-04 (one rename per commit). P3 may parallelize
internally.

## TDD Pairing

| RED                          | GREEN     | Constraint                                              |
| ---------------------------- | --------- | ------------------------------------------------------- |
| T-5.18 (count parity test)   | T-5.19    | DO NOT modify `tests/mirrors/test_count_parity.py`       |

## Hot-path budget

No impact — markdown + dir renames only.

## Done Conditions

- [ ] 8 skill renames live across all 4 IDE surfaces; legacy names deleted
- [ ] 3 mergers complete (`/ai-run` → `--backlog`, `ai-board-*` → subcommands,
  `release-gate` → `--release`)
- [ ] 2 agent renames live; 2 agent deletions complete
- [ ] `/ai-help` matchback-suggest active
- [ ] Mirrors regenerated; `tests/mirrors/test_count_parity.py` green
  (skill = 46, agent = 23)
- [ ] CHANGELOG.md M4 section shipped

## Self-Report
[EMPTY -- populated by Phase 4]
