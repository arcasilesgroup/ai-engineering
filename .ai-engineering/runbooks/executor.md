---
name: executor
schedule: "0 * * * *"
environment: worktree
layer: executor
owner: operate
requires: [gh, uv, git, ruff, ty, gitleaks]
---

# Issue Executor

## Prompt

Pick the highest-priority `agent-ready` issue, create a governed spec, execute the plan through the execute agent, and deliver a PR with auto-merge enabled. Persist full execution context for audit and session recovery.

### Phase 0 — Issue Selection

1. Fetch candidates: `gh issue list --label agent-ready --state open --json number,title,labels,body --limit 10`.
2. Sort by priority: `p1-critical` > `p2-high` > `p3-normal`, then by creation date (oldest first).
3. Pick the top issue. Skip if:
   - Already has a linked PR (check for branch reference in comments).
   - Labeled `blocked`, `in-progress`, or `agent-blocked`.
4. Add label `in-progress` to the selected issue.

### Phase 1 — Branch + Spec Scaffold

5. Create a feature branch from default: `agent/<issue-number>-<slug>`.
6. Read the issue body for acceptance criteria, labels, and linked context.
7. **Classify pipeline** from the issue:
   - `p1-critical` or `bug` label → `hotfix` pipeline.
   - Single-file / typo scope → `trivial` pipeline.
   - 3-5 files or enhancement → `standard` pipeline.
   - >5 files or new capability → `full` pipeline.
8. **Create spec scaffold** — invoke the spec skill procedure:
   - Determine next spec number: scan `context/specs/` for highest `NNN` + 1.
   - Create `context/specs/NNN-<slug>/spec.md` — populate Problem from issue body, Solution from analysis, Acceptance Criteria from issue, Decisions table empty.
   - Create `context/specs/NNN-<slug>/plan.md` — architecture (new/modified files), session map (phases with size estimates), agent assignments.
   - Create `context/specs/NNN-<slug>/tasks.md` — checkbox tasks grouped by phase, frontmatter with `total`, `completed: 0`, `last_session`, `next_session`.
   - Update `context/specs/_active.md` → point to the new spec.
   - Atomic commit: `spec-NNN: Phase 0 — scaffold spec for #<issue-number>`.

### Phase 2 — Execution (Execute Agent Protocol)

9. **Activate execute agent** — read the approved plan and dispatch work:
   - Read `plan.md` for phase ordering and agent assignments.
   - Partition tasks: independent tasks in parallel, dependent tasks serialized.
   - Dispatch the build agent for implementation following all standards in `.ai-engineering/standards/`.
   - After EACH task completion:
     - Mark `[x]` in `tasks.md`.
     - Update `tasks.md` frontmatter: increment `completed`, update `last_session`.
     - Save checkpoint: `ai-eng checkpoint save`.
   - If `.ai-engineering/` content modified: run integrity-check.
10. **Record decisions** as they arise: `ai-eng decision record` (dual-write to `decision-store.json` + `audit-log.ndjson`).

### Phase 3 — Quality Gates

11. Run full quality gates:
    - `uv run ruff check src/ tests/`
    - `uv run ruff format --check src/ tests/`
    - `uv run ty check src/`
    - `uv run pytest`
    - `gitleaks detect --source .`
12. If gates fail:
    - Diagnose failure, attempt fix (max 3 iterations per gate).
    - After each fix attempt: re-run the failing gate, save checkpoint.
    - If a gate still fails after 3 attempts: escalate (see Phase 5 — Failure).

### Phase 4 — Deliver

13. **Create `done.md`** in the spec directory:
    - Summary of what was delivered.
    - Final gate verification results.
    - Deferred items or follow-up specs (if any).
14. Update `tasks.md` frontmatter: `completed` = `total`, `next_session` = "CLOSED".
15. Final commit: `spec-NNN: close — implemented #<issue-number>`.
16. Push branch to origin.
17. Create PR:
    - Title: `spec-NNN: <title> (fixes #<issue-number>)`.
    - Body: summary from `done.md`, acceptance criteria checklist, link to spec.
    - `gh pr create --title "spec-NNN: <title> (fixes #<number>)" --body "<body>"`.
18. Enable auto-merge: `gh pr merge <pr-number> --auto --squash --delete-branch`.
19. **Persist execution summary** — emit signal to `audit-log.ndjson`:
    - `type: "executor-run"`, `issue`, `spec`, `branch`, `pr`, `status: "delivered"`, `timestamp`.
    - Save final checkpoint: `ai-eng checkpoint save`.

### Phase 5 — Failure Handling

20. If gates fail after 3 fix attempts OR implementation cannot proceed:
    - Post a comment on the issue with:
      - What was attempted (phases completed, tasks done).
      - Specific failure details (gate output, error messages).
      - Spec location for context: `context/specs/NNN-<slug>/`.
    - Remove `in-progress` label, add `agent-blocked`.
    - Update `tasks.md` frontmatter: `next_session` = "BLOCKED — <reason>".
    - Persist failure context: `ai-eng checkpoint save` + emit signal `status: "blocked"`.

## Context

- **Agents**: execute (orchestration), build (implementation).
- **Skills**: spec (scaffold), commit (governed commits), pr (governed PR), quality (gates), debug (failure diagnosis).
- **Reads**: `.ai-engineering/standards/` for code standards, `context/specs/_active.md` for active spec state.
- **Writes**: `context/specs/NNN-<slug>/` (spec lifecycle), `state/session-checkpoint.json`, `state/decision-store.json`, `state/audit-log.ndjson`.

## Persistence Contract

Every executor run produces a traceable trail:

| Artifact | Location | Written |
|----------|----------|---------|
| Spec scaffold | `context/specs/NNN-<slug>/spec.md` | Phase 1 |
| Execution plan | `context/specs/NNN-<slug>/plan.md` | Phase 1 |
| Task tracker | `context/specs/NNN-<slug>/tasks.md` | Phase 1, updated every task |
| Decisions | `state/decision-store.json` | As needed during execution |
| Session checkpoint | `state/session-checkpoint.json` | After every task + on failure |
| Audit log | `state/audit-log.ndjson` | Decisions + final summary |
| Done report | `context/specs/NNN-<slug>/done.md` | Phase 4 (on success) |

This ensures:
- **Resumability**: interrupted runs can be recovered via `ai-eng checkpoint load`.
- **Auditability**: every decision and action is traceable.
- **Context transfer**: subsequent agents or humans can read the spec to understand what was done and why.

## Safety

- Only ONE issue per run. Do not batch.
- Branch MUST be `agent/<issue-number>-<slug>` — never commit to main.
- If tests fail after 3 fix attempts, stop and label `agent-blocked`.
- Do NOT disable or bypass any gate.
- Do NOT use `--no-verify` on any git command.
- Do NOT modify test assertions to make tests pass (fix the code, not the tests).
- Auto-merge requires CI to pass — GitHub handles the merge, not the agent.
- Maximum 100 lines changed per run. If the issue requires more, label `too-large` and skip.
- Parallel governance content modifications are prohibited — serialize them.
- Spec numbers are sequential and never reused.
