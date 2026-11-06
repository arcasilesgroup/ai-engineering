# DECISIONS.md

One standing decision per block. Read the one that covers an area before changing it. To reverse a decision, add a new block that supersedes it. Do not edit the old block.

## D-001: ai-engineering governs this repo

Status: Accepted · Date: 2026-09-15

### Context

A repo with no contract leaves every agent to invent its own rules. The same decision, made the same way every time, belongs in code.

### Decision

{ai} Engineering 2.2.0 is installed here: global skill canon, local receipts, git floor on.

### Consequences

- Init, doctor, and the chain are the contract.
- A machine without the canon is not governed.

### Alternatives considered

- **Per-repo copies of the skills:** they drift. Rejected.

## D-002: Governance improves by observability, not by more stoppers

Status: Accepted · Date: 2026-09-20

### Context

The policy guard finished the command-scope half of least agency. Least agency without a record of what was denied is blind. Evidence is in research/001.

### Decision

The next milestone takes research/001 R1 (richer gc aggregate: per guard, tool, and surface, plus a daily series and a baseline-deviation warning) and R2 (a cross-session deny ledger that is signal only, never a verdict). R3, an OTLP alias, stays off unless there is real demand.

### Consequences

- Receipts keep the signal the 30-day sweep used to throw away.
- A repeated deny is reported. It does not become an automatic block.

### Alternatives considered

- **More stoppers:** they hide the pattern. Rejected.

## D-003: Observability ships as signal inside the gc

Status: Accepted · Date: 2026-09-21

### Context

Receipts already carried the story. The 30-day sweep deleted it.

### Decision

R1 and R2 are built: a richer summary.json, a denies.json ledger, and a deviation warning at 3x. R3 (OTLP) and the injection fold-miss stay out until real demand. If after 90 days the ledger recorded zero repeats and doctor flagged zero deviations on this repo, the layer is removed.

### Consequences

- Doctor can say what is being denied, and how often.
- A layer that never fires does not stay as ceremony.

### Alternatives considered

- **Ship OTLP now:** no consumer asked. Rejected.

## D-004: The prompt is the one leak surface gitleaks cannot see

Status: Accepted · Date: 2026-09-22

### Context

Gitleaks sees shaped keys in commits. The floor already blocks those. A secret a person types enters the transcript before any commit exists. After the turn ends, reverting does not take the bytes out of the history.

### Decision

The spoken-secret guard blocks a prompt that carries a low-entropy credential, with advice, and never echoes the value. It runs on UserPromptSubmit where the host exposes that event (Claude Code, Codex). It stays off, with the cause named, where the host ignores the output or has no prompt event (Copilot, Cursor, Oh My Pi, OpenCode, Pi).

### Consequences

- The only window that works is the turn the secret is typed.
- Hosts without a prompt hook are named, not pretended.

### Alternatives considered

- **Scan the transcript later:** the bytes are already stored. Rejected.

## D-005: Bound checkpoint workers to a small deliverable

Status: Accepted · Date: 2026-10-27

### Context

Found during floating-core CP4 on 2026-10-27: the tests-first worker ran for over 7,000 seconds and remained active after 23 tool calls, but had not produced a test file or reported a blocker. The worktree showed only the orchestrator's checkpoint-status edit. The current feature commit was `de296ccc` (CP3 review gate passed). This describes `.ai-engineering/workflow/checkpoints/floating-core.json` CP4, `.ai-engineering/workflow/test-plans/floating-core.json` CP4 cases, and the tests-first steps in `skills/ai-orchestrator/SKILL.md`. It is still true when a checkpoint's test task combines many independent contracts and the worker has no early, checkable deliverable.

Evidence: the worker status reported 7,064 seconds elapsed, 23 tool calls, and no completed turn; `git status --short` showed no CP4 test files.

### Decision

Split broad checkpoint test-writing into bounded deliverables with a clear first artifact and an explicit blocker report. Keep every acceptance case, security check, and required gate; reduce scope by slicing the work, never by dropping coverage or bypassing governance.

### Consequences

- A stalled investigation becomes visible before it consumes a long session.
- More handoffs may be needed, but each has a verifiable result.
- Required coverage and gates remain intact.

### Alternatives considered

- **One comprehensive test-writing assignment:** it obscures stalled scope and delays the first useful result. Rejected.

## D-006: Bound focused checks and verify stalls in a fresh task

Status: Accepted · Date: 2026-10-29

### Context

During floating-core CP17 documentation verification, `cp17-docs-test-check` was still running after 20,496 seconds and 19 tool calls for one focused Bun test. A STOP message was delivered; after another 180 seconds it remained running. No force-cancel was available. This records the observed state and does not infer a runner root cause or claim that the old task stopped. The worktree had only the intended `FILEMAP.md` and `tests/docs-lint.spec.ts` edits.

found: A fresh task ran `bun test ./tests/docs-lint.spec.ts` in 196 ms: 2 passed, 1 failed on stale command references.

commit: `4b9cb17d` (`test(floating-core): CP17 documentation contracts`).

files: `tests/docs-lint.spec.ts`, `FILEMAP.md`, and the CP17 verify entry in `.ai-engineering/workflow/checkpoints/floating-core.json`.

still_true_when: a focused-check task remains active after STOP and no force-cancel is available; a fresh task can run the exact command and provide independent evidence.

### Decision

Give focused-check tasks an explicit time bound and checkable stop condition. If a task remains active after STOP and cannot be force-cancelled, run the exact command in a fresh bounded task; keep the original marked running unless a tool confirms it stopped.

### Consequences

- A focused check can produce independent evidence without waiting indefinitely on an unresponsive task.
- The original task's execution state remains unknown until the runner confirms termination.

### Alternatives considered

- **Treat STOP as proof of termination:** the task still reported running afterward. Rejected.
- **Wait indefinitely for the original task:** no new check result or confirmed stop was available. Rejected.
