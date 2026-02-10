# PR Creation

## Purpose

Craft well-structured pull requests with clear titles, descriptive bodies, breaking change documentation, and review checklists. Ensures PRs are reviewable, traceable, and merge-ready.

## Trigger

- Command: agent invokes pr-creation skill or as part of `/pr` workflow.
- Context: preparing code changes for review and merge.

## Procedure

1. **Title** — concise, descriptive, prefixed with type.
   - Format: `type(scope): description` or `spec-NNN: Task X.Y — description`.
   - Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`.
   - Max 72 characters.

2. **Description** — structured body with context.
   - **What**: summarize the changes in 2-3 sentences.
   - **Why**: link to spec, task, or issue. Explain the motivation.
   - **How**: key implementation decisions and trade-offs.
   - **Breaking changes**: list any API or behavior changes that affect consumers.

3. **Checklist** — self-review before requesting review.
   - [ ] Code follows `standards/framework/stacks/python.md`.
   - [ ] Tests added/updated for new behavior.
   - [ ] `ruff check` and `ruff format --check` pass.
   - [ ] `ty check src/` passes.
   - [ ] `pytest` passes with coverage ≥80%.
   - [ ] No secrets in committed code.
   - [ ] Breaking changes documented (if any).

4. **Labels and metadata** — tag appropriately.
   - Size labels if applicable (S/M/L/XL).
   - Area labels (state, installer, hooks, doctor, etc.).
   - Link to spec task if part of governed workflow.

5. **Review assignment** — identify reviewers.
   - Auto-assign if CODEOWNERS configured.
   - Tag relevant domain experts for complex changes.

## Output Contract

- PR created with structured title and description.
- Checklist completed and visible in PR body.
- Auto-complete enabled with squash merge and branch deletion.
- PR URL displayed for tracking.

## Governance Notes

- All PRs must pass quality gates before merge (pre-push checks).
- Auto-complete with squash merge and branch deletion is mandatory.
- Never merge to protected branches directly.
- Breaking changes require explicit documentation in PR description.

## References

- `skills/workflows/pr.md` — full `/pr` workflow procedure.
- `skills/swe/changelog-documentation.md` — changelog entry formatting for PRs.
- `standards/framework/quality/core.md` — PR quality gates.
- `standards/framework/core.md` — command governance.
- `standards/framework/stacks/python.md` — Python checks in PR checklist.
