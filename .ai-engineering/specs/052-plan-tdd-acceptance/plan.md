---
spec: "052"
approach: "serial-phases"
---

# Plan — Interrogación Profunda, TDD Two-Agent, Acceptance Criteria

## Architecture

### Modified Files

| File | Change | Agent |
|------|--------|-------|
| `agents/plan.md` | Add Interrogation Phase section + behavior rules | build |
| `agents/verify.md` | Add TDD RED Phase mode + Implementation Contract output | build |
| `agents/build.md` | Add TDD GREEN Protocol + Iron Law reference | build |
| `skills/test/SKILL.md` | Full rewrite: multi-stack TDD, fakes, flaky guide | build |
| `skills/spec/SKILL.md` | Add executable AC table to scaffold template | build |
| `skills/plan/SKILL.md` | Add PLAN-R5 Interrogation shared rule | build |

### Post-Implementation

| Action | Command |
|--------|---------|
| Sync mirrors | `python scripts/sync_command_mirrors.py` |
| Sync templates | `rsync -a .ai-engineering/agents/ src/ai_engineering/templates/.ai-engineering/agents/` etc. |
| Verify integrity | `uv run pytest tests/unit/test_real_project_integrity.py -v` |

## Session Map

### Phase 1: Plan Agent — Interrogation Phase [M]

**Agent**: build

Modify `agents/plan.md` to add Interrogation Phase BEFORE the existing pipeline:

```
Current:  classify → discover → spec → STOP
After:    INTERROGATE → classify → discover → spec → STOP
```

Content to add:
- Interrogation Phase section with 7 steps (explore, ask, challenge, map, challenge assumptions, second-order, surface constraints)
- Gate: "Do not proceed until zero UNKNOWNs remain"
- Integration with existing Pipeline Strategy Pattern

Also modify `skills/plan/SKILL.md`:
- Add `PLAN-R5 (Interrogation)` shared rule
- Reference codebase exploration as mandatory step

### Phase 2: Acceptance Criteria in Spec Scaffold [S]

**Agent**: build

Modify `skills/spec/SKILL.md`:
- Change AC section from prose to table format
- Add `Verification Command` and `Expected` columns
- Add examples showing executable ACs

### Phase 3: TDD Two-Agent Protocol [L]

**Agent**: build

**3.1: Verify Agent — TDD RED Phase**

Modify `agents/verify.md`:
- Add "tdd" mode to modes table
- Add TDD RED Phase workflow (behavior contract → write tests → verify RED → Implementation Contract)
- Define Implementation Contract output format
- Rule: verify writes tests but NEVER production code in TDD mode

**3.2: Build Agent — TDD GREEN Protocol**

Modify `agents/build.md`:
- Add TDD Protocol section
- Rule: when Implementation Contract exists, DO NOT modify test files
- Rule: implement minimal code (GREEN), then REFACTOR
- Iron Law: "If tests are wrong, escalate to user. NEVER weaken tests."

### Phase 4: Test Skill Rewrite [L]

**Agent**: build

Full rewrite of `skills/test/SKILL.md` as comprehensive multi-stack testing skill:

**Structure**:
1. Philosophy (confidence > coverage)
2. Modes (plan, run, gap, tdd)
3. TDD Cycle (Iron Law + RED-GREEN-REFACTOR)
4. AAA Pattern (non-negotiable)
5. Naming Convention (`test_<unit>_<scenario>_<expected>`)
6. Fakes Over Mocks (Protocol-based)
7. Stack-Specific Sections (Python, TypeScript, .NET, React, Next.js, Node, NestJS, Rust, Go, Java)
8. Test Categories (unit, integration, e2e)
9. Coverage Strategy (80% core, branch coverage)
10. Rationalization Table (from superpowers/tdd)
11. Flaky Test Diagnostic (6 categories)
12. Verification Checklist

**Target**: ~400 lines (under 500 limit per Anthropic pattern)

### Phase 5: Sync + Validate [S]

**Agent**: build

1. Run `python scripts/sync_command_mirrors.py` — sync all 5 mirror surfaces
2. Sync templates: `rsync` canonical → templates
3. Run all 10 acceptance criteria from spec.md
4. Run full test suite

## Patterns

- One commit per phase: `spec-052: Phase N — description`
- Agent files modified BEFORE skill files (agents reference skills)
- Test skill written LAST (depends on TDD protocol being defined first)
- Sync as final phase to catch all accumulated changes
