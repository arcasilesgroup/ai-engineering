# Create Spec

## Purpose

Definitive procedure for creating a new spec before non-trivial work begins. Ensures every significant change is tracked through the spec lifecycle (spec.md → plan.md → tasks.md → done.md), starts on a dedicated branch, and integrates with the governance content system.

## Trigger

- Command: agent invokes create-spec skill or user requests a new spec.
- Context: non-trivial work is about to begin — new feature, refactor, architectural change, governance content expansion, or any change touching >3 files.
- Fallback: `_active.md` points to a completed spec (has `done.md`) or no active spec exists, and a non-trivial change is requested.

## Non-Trivial Heuristic

A change is **non-trivial** when ANY of these apply:

- Touches more than 3 files.
- Introduces a new feature or capability.
- Refactors existing architecture or patterns.
- Changes governance content (standards, skills, agents).
- Modifies framework-contract or core standards.
- Requires multi-step implementation across sessions.

A change is **trivial** (spec exempt) when ALL of these apply:

- Typo or formatting fix.
- Single-line change.
- Dependency version bump without breaking changes.
- Comment or documentation minor correction.

## Procedure

### Phase 1: Branch

1. **Create a dedicated branch** — every non-trivial change starts on its own branch, never on main/master.
   - Branch naming convention:
     - `feat/<slug>` — new features, capabilities, governance content.
     - `bug/<slug>` — bug fixes requiring investigation.
     - `hotfix/<slug>` — urgent production fixes.
     - `spec-NNN/<slug>` — spec-driven work (alternative to feat/).
   - Branch from the default branch (main/master) unless continuing from an existing integration branch.
   - Verify clean git state before branching: `git status` must show clean working tree or stash first.
   - Push branch to origin immediately or after first commit depending on team preference.

### Phase 2: Classify

2. **Determine the next spec number** — scan `context/specs/` for existing directories.
   - Pattern: `NNN-<slug>` where NNN is zero-padded 3-digit sequential number.
   - Next number = highest existing + 1.

3. **Choose a slug** — kebab-case, 2-4 words, descriptive of the work scope.
   - Examples: `cross-ref-hardening`, `governance-enforcement`, `python-rewrite`.

### Phase 3: Scaffold

4. **Create the spec directory** — `context/specs/NNN-<slug>/`.

5. **Create spec.md** — the WHAT document.
   - Required sections:

     ```
     ---
     id: "NNN"
     slug: "<slug>"
     status: "in-progress"
     created: "YYYY-MM-DD"
     ---

     # Spec NNN — <Title>
     ## Problem
     ## Solution
     ## Scope
       ### In Scope
       ### Out of Scope
     ## Acceptance Criteria
     ## Decisions
     ```

   - Problem: concrete description of what is wrong or missing.
   - Solution: what will be built/changed to fix it.
   - Scope: explicit in/out boundaries.
   - Acceptance Criteria: numbered, verifiable conditions.
   - Decisions: table with ID, Decision, Rationale columns.

6. **Create plan.md** — the HOW document.
   - Required sections:

     ```
     ---
     spec: "NNN"
     approach: "serial-phases|parallel-phases|mixed"
     ---

     # Plan — <Title>
     ## Architecture
       ### New Files
       ### Modified Files
       ### Mirror Copies
     ## File Structure
     ## Session Map
     ## Patterns
     ```

   - Architecture: tables listing new/modified files with purpose.
   - Session Map: phase-by-phase breakdown with size estimates (S/M/L).
   - Patterns: execution conventions for this spec.

7. **Create tasks.md** — the DO document.
   - Required structure:

     ```
     ---
     spec: "NNN"
     total: <count>
     completed: 0
     last_session: "YYYY-MM-DD"
     next_session: "Phase 0 — Scaffold"
     ---

     # Tasks — <Title>
     ## Phase N: <Name> [Size]
     - [ ] N.M <Task description>
     ```

   - Frontmatter tracks progress metadata.
   - Phases numbered from 0 (scaffold is always Phase 0).
   - Tasks use checkbox format: `- [ ] N.M Description`.
   - Size annotation: `[S]`, `[M]`, `[L]` after phase name.

### Phase 4: Activate

8. **Update `_active.md`** — point to the new spec.
   - Update frontmatter: `active: "NNN-<slug>"`, `updated: "YYYY-MM-DD"`.
   - Update body: link to new spec's `spec.md`.
   - Update Quick Resume: all links point to new spec directory.

### Phase 5: Cross-Reference

9. **Update `product-contract.md`** — set Active Spec to the new spec.
   - Update the "Active Spec" section to reference the new spec.
   - Update read sequence links.

### Phase 6: Commit

10. **Atomic commit** — commit the scaffold as a single atomic commit.
    - Message format: `spec-NNN: Phase 0 — scaffold spec files and activate`.
    - Include: spec.md, plan.md, tasks.md, _active.md.
    - Do NOT include product-contract.md in scaffold commit if other phases will update it too.

### Phase 7: Execute

11. **Work through tasks phase by phase** — follow the task list in order.
    - Each phase produces one atomic commit: `spec-NNN: Phase N — <description>`.
    - Mark tasks `[x]` as they complete.
    - Update `tasks.md` frontmatter after each phase: `completed`, `last_session`, `next_session`.
    - Record decisions in `decision-store.json` as they arise.

### Phase 8: Close

12. **Verify acceptance criteria** — all criteria in spec.md must pass.

13. **Create `done.md`** — the DONE document.
    - Summary of what was delivered.
    - Final verification results.
    - Any deferred items or follow-up specs.

14. **Update tasks.md frontmatter** — set `completed` = `total`, `next_session` = "CLOSED".

15. **Update `_active.md`** — if no follow-up spec, revert to previous or leave pointing to completed spec.

16. **Create PR** — merge the feature branch back to default branch.
    - PR title: `spec-NNN: <Title>`.
    - PR body: summary from done.md, list of changes, verification checklist.

## Output Contract

- Feature branch created from default branch.
- Spec directory with spec.md, plan.md, tasks.md.
- `_active.md` pointing to new spec.
- Atomic commits per phase throughout execution.
- `done.md` at closure.
- PR for merge back to default branch.

## Governance Notes

- Non-trivial changes without an active spec are governance violations.
- Spec creation is Phase 0 of any non-trivial work — it happens BEFORE implementation begins.
- The branch-first step ensures no work happens on protected branches.
- Spec numbers are sequential and never reused.
- Agents must check `_active.md` at session start — if it points to a completed spec and non-trivial work is requested, invoke create-spec first.
- Trivial changes (typos, formatting, single-line fixes) are exempt from spec-first requirement.

## References

- `standards/framework/core.md` — governance structure, spec-first enforcement, session contract.
- `context/product/framework-contract.md` — agentic model, session contract, branch strategy.
- `skills/govern/create-skill.md` — registration procedure for new skills.
- `skills/govern/create-agent.md` — registration procedure for new agents.
- `skills/docs/prompt-design.md` — content authoring quality.
- `skills/workflows/pr.md` — PR creation at spec closure.
