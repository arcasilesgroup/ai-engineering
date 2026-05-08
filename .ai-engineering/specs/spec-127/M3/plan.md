---
total: 11
completed: 0
---

# Plan: sub-004 M3 — Progressive-disclosure slim-down

## Pipeline: standard
## Phases: 4
## Tasks: 11 (build: 8, verify: 3)

## Architecture

**Pattern**: Progressive disclosure. Skills body stays small; detail moves to
`references/` one level deep. No nested refs.

**Justification**: D-127-08 ≤120 line internal target preserves headroom under
Anthropic's 500-line hard ceiling. Brief §22 split contract prevents
duplication between skill + agent pair files.

## Design

Skipped — refactor of existing markdown.

## Phase classification: standard

5 slim-downs + 1 lint check expansion + 1 no-nested-ref test + 1 split-contract
pass + final verify.

### Phase 0: Pre-flight + identify

**Gate**: top-5 over-length confirmed at current line counts; sub-003 state
shipped (Examples + Integration sections present).

- [ ] T-4.1: Verify dependency — `sub-003` status `shipped` in manifest;
  confirm current line counts: ai-animation 228, ai-video-editing 194,
  ai-governance 182, ai-platform-audit 181, ai-skill-evolve 179 (agent: verify)

### Phase 1: Per-skill slim-down (one task per skill)

**Gate**: each SKILL.md ≤120 lines after slim; content equivalence preserved
(manual review checklist); `references/` directory present per skill.

- [ ] T-4.2: Slim `ai-animation/SKILL.md` 228 → ≤120; move easing-curves,
  accessibility, stagger-and-debug to `references/<topic>.md` (agent: build)
- [ ] T-4.3: Slim `ai-video-editing/SKILL.md` 194 → ≤120; new `references/`
  for layer details, ffmpeg tables, social presets (agent: build)
- [ ] T-4.4: Slim `ai-governance/SKILL.md` 182 → ≤120; move detail to
  `references/` (agent: build)
- [ ] T-4.5: Slim `ai-platform-audit/SKILL.md` 181 → ≤120; expand existing
  `references/report-template.md` precedent (agent: build)
- [ ] T-4.6: Slim `ai-skill-evolve/SKILL.md` 179 → ≤120; move grading rubric
  + optimizer phase tables to `references/` (agent: build)

### Phase 2: Skill/agent split contract (brief §22)

**Gate**: 5 pair-file skills declare dispatch threshold once; no duplication
between skill + agent.

- [ ] T-4.7: Apply split contract to pair files — `ai-autopilot`,
  `ai-verify`, `ai-review`, `ai-plan`, `ai-guide`. Declare dispatch threshold
  in skill body; pair agent reads via reference. Reduce duplication
  (agent: build)

### Phase 3: No-nested-refs guard (TDD pair)

**Gate**: `tools/skill_lint/checks/no_nested_refs.py` exists; test green;
`skill_lint --check` asserts all SKILL.md ≤120 lines.

- [ ] T-4.8.RED: Failing test `tests/conformance/test_no_nested_refs.py`
  asserts no `references/<file>.md` contains a link to another `references/`
  file (agent: build)
- [ ] T-4.9: Implement `tools/skill_lint/checks/no_nested_refs.py` — markdown
  AST walk; export `check_no_nested_refs(skill_dir) -> RubricResult`. **DO
  NOT modify `tests/conformance/test_no_nested_refs.py` from T-4.8.**
  (agent: build)
- [ ] T-4.10: Verify `pytest tests/conformance/test_no_nested_refs.py` green;
  run `skill_lint --check` — assert all SKILL.md ≤120 lines (agent: verify)
- [ ] T-4.11: Final lint sweep — re-run `skill_lint --check` over the 5
  slimmed skills + audit content equivalence; mark sub-004 ready-for-review
  (agent: verify)

## Phase Dependency Graph

```
P0 ──→ P1 (5 slim-downs, parallelizable) ──→ P2 (split contract) ──→ P3 (RED→GREEN no-nested-refs + final verify)
```

P1 tasks may run in parallel — different files, no shared state.

## TDD Pairing

| RED                               | GREEN                       | Constraint                                              |
| --------------------------------- | --------------------------- | ------------------------------------------------------- |
| T-4.8 (no-nested-refs test)       | T-4.9 (checker impl)        | DO NOT modify `tests/conformance/test_no_nested_refs.py` |

## Hot-path budget

No impact (markdown only).

## Done Conditions

- [ ] All 5 over-length SKILL.md ≤120 lines
- [ ] `references/<topic>.md` ships under each slimmed skill, one level deep
- [ ] No nested ref→ref (`tests/conformance/test_no_nested_refs.py` green)
- [ ] Skill/agent split contract applied to 5 pair-files
- [ ] `skill_lint --check` asserts all 50 SKILL.md ≤120 lines
- [ ] Content equivalence preserved (manual review)

## Self-Report
[EMPTY -- populated by Phase 4]
