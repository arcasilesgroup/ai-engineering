# Plan: spec-067 Auto-optimize brainstorm input via ai-prompt preprocessing

## Pipeline: hotfix
## Phases: 2
## Tasks: 4 (build: 3, verify: 1)

---

### Phase 1: Build canonical files
**Gate**: Handler exists, SKILL.md has step 1.5, both follow existing patterns.

- [x] T-1.1: Create `handlers/prompt-enhance.md` (agent: build) -- DONE
  - Create `.claude/skills/ai-brainstorm/handlers/prompt-enhance.md`
  - Define quality evaluation criteria: detect vague markers in ES ("mejorar", "optimizar", "arreglar", "limpiar") and EN ("improve", "optimize", "fix", "clean up"), plus absence of measurable criteria
  - Apply ai-prompt technique #1 (Be Explicit Over Implicit): transform vague terms into precise, measurable descriptions
  - Apply ai-prompt technique #5 (Positive Framing): state what to build, not what to avoid
  - Skip logic: if input has no vague markers AND contains specific/measurable terms, output "Input ya optimo, continuando..." and proceed
  - Preserve breadth of intentionally exploratory inputs (do not narrow scope, only clarify terms)
  - Display format: show `**Input original:**` / `**Input optimizado:**` then auto-continue
  - Follow existing handler structure (same as `interrogate.md` and `spec-review.md`: Purpose, Procedure with steps, Exit Criteria)
  - **Done when**: Handler file exists with all criteria (AC1, AC2, AC3, AC4, AC5)

- [x] T-1.2: Update brainstorm SKILL.md (agent: build, blocked by T-1.1) -- DONE
  - Add step 1.5 "Enhance input" between step 1 "Load context" and step 2 "Interrogate":
    ```
    1.5. **Enhance input** -- follow `handlers/prompt-enhance.md` to evaluate and optimize user input
    ```
  - Add row to Quick Reference table between "Load context" and "Interrogate":
    ```
    | Enhance input | Input quality checked | Optimized input (or original if already specific) |
    ```
  - Update Integration section "Calls" to include `handlers/prompt-enhance.md`
  - Do NOT change any other behavior or steps
  - **Done when**: SKILL.md has step 1.5, table row, and handler reference (AC6, AC7, AC8)

### Phase 2: Sync mirrors + verify
**Gate**: All 3 mirrors reflect canonical changes. No regressions.

- [x] T-2.1: Run mirror sync (agent: build, blocked by T-1.2) -- DONE
  - Run `python scripts/sync_command_mirrors.py`
  - This auto-syncs:
    - `.github/prompts/ai-brainstorm.prompt.md` (flattens handler inline)
    - `.agents/skills/brainstorm/SKILL.md` (copies SKILL.md)
    - `.agents/skills/brainstorm/handlers/prompt-enhance.md` (copies handler)
  - **Done when**: All 3 mirrors exist and reflect changes (AC13, AC14, AC15)

- [x] T-2.2: Verify correctness (agent: verify, blocked by T-2.1) -- DONE (11/11 AC PASS)
  - Verify `.github/prompts/ai-brainstorm.prompt.md` contains "Enhance input" section with handler content flattened inline
  - Verify `.agents/skills/brainstorm/SKILL.md` contains step 1.5
  - Verify `.agents/skills/brainstorm/handlers/prompt-enhance.md` exists and matches canonical
  - Verify canonical SKILL.md step order: 1 → 1.5 → 2 → 3 → 4 → 5 → 6
  - Verify handler has skip logic, before/after display, both ES+EN markers
  - Spot-check: no behavioral AC can be CI-tested (AC9-AC12 are LLM-behavioral, verified by manual invocation)
  - **Done when**: All mirrors correct, canonical structure validated (AC13-AC15)

---

## Agent Assignments Summary

| Agent | Tasks | Purpose |
|-------|-------|---------|
| build | 3 | Create handler, update SKILL.md, run sync |
| verify | 1 | Validate mirrors and canonical structure |

## Dependencies

```
T-1.1 → T-1.2 → T-2.1 → T-2.2
```

Fully sequential — each task depends on the previous.

## Files Modified

| File | Phase | Action |
|------|-------|--------|
| `.claude/skills/ai-brainstorm/handlers/prompt-enhance.md` | 1 | create |
| `.claude/skills/ai-brainstorm/SKILL.md` | 1 | modify (step 1.5, table, integration) |
| `.github/prompts/ai-brainstorm.prompt.md` | 2 | sync (auto) |
| `.agents/skills/brainstorm/SKILL.md` | 2 | sync (auto) |
| `.agents/skills/brainstorm/handlers/prompt-enhance.md` | 2 | sync (auto) |
