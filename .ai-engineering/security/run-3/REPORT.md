# Security review · worktree lifecycle awareness

This review examined AI Engineering's lifecycle commands and approval gates,
plus Copilotline's read-only lifecycle statusline reader. The feature adds no
network, authentication, or database surface. The strongest issue is that
checkpoint JSON can assert its own gates passed: the hook enforces ordering and
shape, but not human approval provenance. A repository-instruction injection
can therefore lead an active agent to merge unreviewed code into local `main`.
Two lower-impact local issues were also confirmed: terminal-control injection
through ignored filenames during cleanup, and the reserved slug `constructor`
crashing later worktree creation. No remote push was demonstrated.

**Baseline:** Git worktree commands and Copilot CLI's custom statusline hook.
Both operate locally as the invoking user. AI Engineering's prior
`.ai-engineering/security/run-1` has open findings in receipts/doctor, policy,
shell handling, symlink policy, and self-protect. Those unrelated findings were
not repeated. `run-2` had architecture notes only and no findings ledger.

## Findings

| # | Severity | Finding | Impact |
|---|---|---|---|
| 1 | HIGH | Editable checkpoint state self-approves the workflow | Agent can bypass required human review and merge unreviewed code into local `main`. |
| 2 | LOW | Ignored filenames inject terminal control bytes | Cleanup output can overwrite or forge terminal rows. |
| 3 | LOW | `constructor` slug blocks subsequent worktree creation | Recoverable local denial of worktree creation until that worktree is removed. |

### 1. Editable checkpoint state self-approves the workflow

**Files:** `scripts/checkpoint-gate.py:150-172, 277-292`;
`.github/hooks/ai-eng.json:8-17`; `skills/ai-orchestrator/SKILL.md:213-220`.

**Attack:** A repository contributor adds `AGENTS.md` instructions for the
coding agent to skip the checkpoint-review question, edit the feature plan so
all gates and the checkpoint status read `passed`, skip app review, then merge
`feat/<slug>` into local `main`. The installed PreToolUse hook sends checkpoint
JSON writes through `check_plan`, but the function checks only field
consistency and ordering. It accepts self-asserted `passed` fields without test
receipts or a human-issued approval event. The Stop hook also trusts those
stored values.

**Impact:** The documented human review boundary is bypassed; unreviewed code
lands in local `main`. This audit did not push to or modify a remote repository.

**Recommendation:** Require approval provenance that ordinary repository
instructions and checkpoint-file edits cannot forge. Verify that event before
accepting plan approval, app review, or merge.

### 2. Ignored filenames inject terminal control bytes

**Files:** `src/shared-worktree.ts:416-432, 670, 689-699`;
`src/commands/worktree.ts:34, 51`.

**Attack:** A contributor creates an ignored filename containing a newline and
ANSI cursor/erase sequence. After the branch is merged, the maintainer invokes
`ai-eng worktree rm <slug>`. Git returns the raw path through `status -z`;
`worktreeRm` joins it into the success message, and `worktreeMain` writes that
string directly to stdout.

**Impact:** The terminal can display forged or overwritten rows during cleanup.
The command does not execute the filename, and Git's merge check still applies.

**Recommendation:** Sanitize or JSON-quote filenames before rendering them;
preserve raw paths only for filesystem operations.

### 3. The `constructor` slug blocks later worktree creation

**Files:** `src/commands/worktree.ts:19-24`;
`src/shared-worktree.ts:194-195, 315-322, 553-558, 570`.

**Attack:** Run `ai-eng worktree new constructor` with no declared files, then
run `ai-eng worktree new followup`. The first call leaves the ordinary
declarations object without an own `constructor` property. The next call reads
the inherited `Object.prototype.constructor` function and calls `.filter()` on
it, throwing a TypeError.

**Impact:** Later local worktree creation in that checkout fails until the
reserved-slug worktree is removed. The issue is local and recoverable.

**Recommendation:** Use `Object.hasOwn` when reading declaration keys or use a
null-prototype map.

## Rejected candidate

- **Oversized checkpoint declaration causes `worktree list` to crash:** rejected.
  The actual listing path does not read declarations; the scratch reproduction
  did not crash `worktree list`, and creation completed.

## Hardening notes

- Copilotline reads local lifecycle records and renders numeric counts only; it
  does not perform lifecycle actions. Its quota/account network path is outside
  this audit.
- A separate AI Engineering `run-1` finding about attacker-controlled
  `core.fsmonitor` and Git subprocess execution predates this feature. The
  current review did not count that Git-config behavior as a new lifecycle
  finding.
- No access to OpenAI is needed by these local lifecycle paths; any NN policy
  blocking OpenAI calls remains respected.

## Positive controls

- Git subprocesses in the lifecycle manager are passed as argument arrays, not
  interpolated into shell command strings.
- Worktree removal checks ancestry into local `main` unless a user explicitly
  requests `--force`.
- Lifecycle transitions validate slug, state, live path/branch and review
  revision; writes are serialized and atomically replaced.
- Copilotline treats missing, malformed, stale, duplicate, unreadable or
  branch-mismatched evidence as unknown/unavailable and does not print record
  contents.

**Coverage note:** This was one focused run. Additional audits can cover other
code paths; the unrelated open findings from run-1 remain open.
