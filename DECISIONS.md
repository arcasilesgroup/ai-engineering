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
- Corrected 2026-11-23: `agy` joined the hosts with no prompt event, measured on 1.5.14. `docs/surface-capability-matrix.md` owns the current list, host by host, with its measurement dates.

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

## D-007: ai-eng merges its hooks into a settings file the person already has

Status: Accepted · Date: 2026-11-07 · Supersedes the 3.0.0 refusal (R38, "when the API cannot make that binding, refuse with a warning")

### Context

3.0.0 refused to write into any existing machine settings file (`~/.claude/settings.json`, `~/.codex/hooks.json`, `~/.copilot/hooks/ai-eng.json`), because the portable filesystem API cannot bind the last identity check and the rename into one operation. Almost everyone who already uses a host has that file, so at a workshop every first install on every OS ended with no hooks while `init` said governance was installed, and `uninstall` could not take the entries back out. The `first-install` CI job reproduces it against the published 3.0.0 on Windows, Linux and macOS.

### Decision

Merge our entries by marker and replace the file with `replaceMachineSettings`: stage a copy beside it (O_EXCL, never through a link, same permission bits), re-check that the file is still byte- and stat-identical to the one read, then rename over it. Still refused: a hard link with a second name, an alias of `machine.json`, a file that changed while staged, a layout the merge would have to reformat. A symlink to a dotfiles repo stays a link and its target is replaced.

### Consequences

- Existing users get hooks on the first run, and uninstall removes them.
- A write that lands between the last check and the rename is lost: in practice the host itself rewriting its settings at that instant. Whoever else can swap that file already owns the person's editor settings.

### Alternatives considered

- **Keep refusing:** no hooks for any existing user is the outcome the product exists to prevent. Rejected.
- **Write in place (2.6.0):** a crash mid-write leaves half a settings file. Rejected.

## D-008: On Windows, init removes npm's ai-eng.ps1

Status: Accepted · Date: 2026-11-07

### Context

`npm install -g` on Windows writes three shims for `ai-eng`: an extensionless one for Git Bash, `ai-eng.cmd` and `ai-eng.ps1`. PowerShell resolves a bare `ai-eng` to the `.ps1` first. The Restricted execution policy that a fresh Windows laptop ships with refuses to load it, and under `powershell -Command` it starts the program with no stdin, so a hook receives an empty payload. Cursor runs hooks in PowerShell, and its hook file lives in the repo, shared by every OS, with no per-OS key; a person typing `ai-eng init` in a PowerShell window hits the same refusal. The `first-install` CI job measured both on windows-latest.

### Decision

`installCanon` (init and update) removes `ai-eng.ps1` from the first PATH directory that holds one, but only when its text launches this package (`ai-engineering/bin/ai-eng.js`) and an `ai-eng.cmd` sits beside it. PowerShell then runs the `.cmd`, which works under any policy and passes stdin through.

### Consequences

- A bare `ai-eng` works in every Windows shell, for hooks and for people.
- npm writes the `.ps1` again on the next install or upgrade; the next init or update removes it again, and the README names the one command that does it.

### Alternatives considered

- **Tell Windows users to install with bun:** true but it does not fix the people who already ran the README's npm line. Rejected as the only answer.
- **Write `ai-eng.cmd` into the repo hook file:** breaks every macOS and Linux teammate. Rejected.

## D-009: `ai-eng update` installs a newer ai-eng, then syncs

Status: Accepted · Date: 2026-11-19

### Context

3.0 removed the `upgrade` verb because it split one job into two commands, and `update` became "sync from the installed binary, zero network". A person who types `ai-eng update` still expects to end on the newest ai-eng, and the old binary can only sync the files it carries. The version notice only showed at the end of `init` and `doctor`, and the agent never heard about a new release at all.

### Decision

One verb. `ai-eng update` reads the registry once (3 s, remembered for 24 h whether it answered or not). When a newer version exists it asks, installs it with the package manager that installed ai-eng (`bun add -g` or `npm install -g`), checks that the `ai-eng` on PATH is the new one, and runs it to do the sync. The sync itself is still offline. With no terminal and no `--yes` it installs nothing and prints the command. Every human verb ends with the version lines, and a `SessionStart` hook (Claude Code, Codex) hands the same lines to the agent from the cache, with no network.

### Consequences

- `update` makes one registry request per run, and the notices one a day at most; offline, both behave exactly as before.
- Trust in the downloaded package stays with bun or npm: ai-eng never downloads or verifies a binary itself.
- An agent is told to ask the person before installing, because it changes ai-eng for every repo on the machine.

### Alternatives considered

- **Bring the `upgrade` verb back:** the two-step split 3.0 removed. Rejected.
- **Download the release binary ourselves:** a second trust path to maintain. Rejected.

## D-010: One task is one lane, and every lane leaves by one of three doors

Status: Accepted · Date: 2026-11-19

### Context

No successful path cleaned up after itself: merged PRs left local branches (`git branch --merged` misses squash and rebase merges), a 54-day stash outlived its branch, and a dead worktree from another host was never pruned. Two sessions sharing a folder depended on an agent noticing the other one, which it cannot.

### Decision

A lane is a branch, its folder and its PR, and its state is computed from git and the forge each time, never stored. `ai-eng work` shows the board; `tidy` removes only a provably landed lane (the forge merged that exact tip, or the base holds it and its remote branch is gone), `park` records a reason and a date in git config, `drop` keeps the tip in `refs/archive/`. The owner's four calls were taken at the proposed defaults: a second session is detected rather than forcing every agent into a worktree, at most 3 active lanes (`[work] max_active`), an orphan after 3 days (`[work] orphan_days`), and cleanup only when provable. A `no-stash` guard denies creating a stash; a session start shows one line about the lanes that need a decision. `ai-git-cleanup` is removed: `tidy` does its job with the right merge test.

### Consequences

- A merged branch disappears in the step that confirms the merge (`/ai-pr`), not weeks later.
- `ai-eng worktree merge` still keeps the folder after a local merge: its retry and race protection need the checkout, so `ai-eng worktree rm` closes that lane.
- The per-folder lease that would make a second session's first write move to a worktree is not built yet; rule 2 is still the agent's to follow.

### Alternatives considered

- **Every agent always in a worktree:** simpler to explain, heavier for the one-session case. Rejected for now.
- **A lanes file:** a second source of truth that drifts from git. Rejected.

## D-011: A folder is held by the session writing in it, for 15 minutes

Status: Accepted · Date: 2026-11-19

### Context

D-010 left lane rule 2 (one folder, one writer) to the agent, which cannot see another session. Two sessions in one checkout is how one session's `git add -A` took another's 34 files.

### Decision

A `lease` guard holds a folder for the session that writes in it: a file edit, or a git command that writes the index, a ref or the tree. Another session's write there is denied and sent to a worktree. The hold lives in the folder's own git directory, lapses after 15 minutes without a write (`[work] lease_minutes`), ends with the holder's `SessionEnd` where the host sends one (Claude Code), and `ai-eng work release` frees it by hand. A host that sends no session id is never judged.

### Consequences

- Reading, testing and building stay free for every session: only writes are held.
- After closing a session on a host with no SessionEnd, the next session waits up to 15 minutes or runs `ai-eng work release`.

### Alternatives considered

- **Every agent always in a worktree:** no hold to wait on, more friction for one session. Rejected by the owner.
- **A shorter or longer window:** 5 minutes lets a pause lose the folder; 60 blocks for nothing. The owner chose 15.

## D-012: init installs the machine side without asking

Status: Accepted · Date: 2026-11-20

### Context

`ai-eng init` asked twice before writing outside the repo: once to install the global canon on a machine without it, and once to add the guard hook to the home-scoped carriers (Claude Code, Pi, Codex, Copilot, OpenCode). A "no" to either left a repo that called itself governed with no guards running in those tools. `update` and `config --add` already wrote the same files without a question, and the carrier merge keeps every setting of the person's own.

### Decision

`init` installs or repairs the canon and writes the home carriers of the picked surfaces every time, with no question. It still asks before creating a git repository in a bare folder and before overwriting an AGENTS.md that is already there: those touch the person's own files.

### Consequences

- A governed repo always has its guards running in the tools it declares.
- A second `init` writes nothing twice: the carrier merge is by marker, and an up-to-date carrier is reported unchanged.

### Alternatives considered

- **Keep the questions with Yes as the default:** one Enter each, and a "no" still produced a repo governed by nothing. Rejected.

## D-013: The binary carries its payload folders as they are

Status: Accepted · Date: 2026-11-20

### Context

Three generated files were committed so the payload could ride inside the binary: `src/assets.ts` (one import per skill and template file), `scripts/.embed/` (`.txt` copies of skill scripts tsc would otherwise resolve) and `skills/.chain-bundle/` (the compiled chain, parked under `skills/` so the walk picked it up). Each change to a skill or to the chain meant regenerating and committing them, a test existed only to catch them stale, and the code skipped dot entries under `skills/` in five places to step around the bundle.

### Decision

`bun build --compile --asset <folder>` embeds `skills/`, `agents/`, `templates/` and `generated/` at their own relative paths, and `src/embed.ts` reads them by path: beside the binary's entry inside Bun's embedded filesystem when compiled, one level above `src/` from source. The tracked files are the one source of truth. The chain bundle is built into the ignored `generated/` folder by every compile, every `bun test` and every `npm pack`, and is never committed. Approved by the owner on 2026-11-20.

### Consequences

- Editing a skill or template needs no regeneration step; nothing generated is in git.
- The payload root cannot come from `import.meta.dir`: `--bytecode` freezes it to the build machine's path. It comes from `Bun.main` when the binary carries embedded files.
- The prepack script must stay silent on stdout, because the release job parses `npm pack --json`.

### Alternatives considered

- **Keep the generated registry, move the bundle out of `skills/`:** fixes the misplaced folder and keeps two committed generated files. Rejected.

## D-014: Layer rules are proposed by a skill, for the language's own tool

Status: Accepted · Date: 2026-11-20

### Context

`init` wrote the same empty `.ai-engineering/arch.rules.json` into every repo, and nothing outside this repository ever read it: the only reader was ai-engineering's own `tests/arch.spec.ts`. `doctor` reported "active" once a `src/` folder existed, with no rule in the file, and "bootstrap mode" for ever in a repo whose code is not under `src/`. The AGENTS.md template promised an arch test the project did not have.

### Decision

`init` no longer writes `arch.rules.json`. Layer rules belong to the standard tool of the language (dependency-cruiser, import-linter, depguard in golangci-lint), and `/ai-config-to-project` proposes them from the real dependency graph, the stack's guidelines and the project's own documents; the person applies them. `doctor` recognises those tools, says nothing is wrong in a repo with no code yet, and points a repo with code and no rules at the skill. `update` retires the seeded file while it is untouched and keeps one a person edited. Approved by the owner on 2026-11-20.

### Consequences

- No deterministic layer engine to maintain inside ai-eng; each language keeps its own.
- A JavaScript project's `arch` script runs in the ai-eng check workflow; other languages run their tool in a CI step of their own.
- This repository keeps `tests/arch.spec.ts` and its non-empty `arch.rules.json`, which `doctor` still counts as rules.

### Alternatives considered

- **A new arch verb in the CLI, with scanners per language and a `--suggest` mode:** deterministic, and a second implementation of what each language's tool already does, with the judgement of choosing layers still missing. Rejected by the owner.

## D-015: One refresh skill, verify lanes inside ai-verify, lanes that close themselves

Status: Accepted · Date: 2026-11-20

### Context

Two skills kept one repository's guidance in line with its tree: `ai-agents-md` for the instruction files and `ai-config-to-project` for the governance files, and the second ended in an `adapt apply` verb that always refused because a hash an agent writes cannot prove a person approved anything. Twelve verification skills without the `ai-` prefix are the tiers `ai-verify` routes to, installed as top-level skills. And a landed branch stays on the board until someone runs `ai-eng work tidy`: a squash merge without `gh`, or a merge done in the forge's web page, is never seen as landed.

### Decision

The owner approved the plan on 2026-11-20:

1. `ai-agents-md` and `ai-config-to-project` become one manual skill, `ai-refresh-project`, and the `adapt` verb is deleted with its hash ritual.
2. The twelve unprefixed verification skills move inside `ai-verify` as its lanes, unmerged and unpruned; a later verify study decides what survives.
3. Claude Code reads AGENTS.md when there is no CLAUDE.md, so no `@AGENTS.md` bridge is added.
4. When a session opens, a branch whose landing is proven is deleted without asking: its tip is kept in `refs/archive/` first, a worktree with uncommitted changes is never touched, and the session is told in one line.

### Consequences

- Refreshing a project is one door, run by name, with every governance change on a page the person applies.
- The skills list shrinks by thirteen entries without losing a lane's content.
- The board shows only work that is still open.

### Alternatives considered

- **Warn at session start and leave deleting to `ai-eng work tidy`:** nothing goes without a command, and landed branches pile up until someone remembers. Rejected by the owner.

## D-016: One resumed builder, one review

Status: Accepted · Date: 2026-11-22 · Supersedes the handoff-multiplication consequence of D-005

### Context

Across 15 orchestrator sessions the archive shows 469 checkpoint launches. 42% repeat a stage already launched. OMP's child workers spent 28.6 active hours; 10.5 of those hours are the repeat. Review averaged 19 minutes of reading. The behavior gate averaged 3.7 minutes and almost never edited. A fresh agent re-reads the repo, including the 1,934-line learnings log, before it writes. D-005 still holds that a checkpoint must produce a checkable artifact and must not drop acceptance cases. The separate test, behavior, and debate agents were the handoffs, not the coverage.

### Decision

One builder is resumed for tests, implementation, verify, and the single fix. Its verify receipt is the behavior gate. One new reviewer judges the diff for one round; a blocker or major gets one fix and one re-check, then the run stops. The parent ends the turn when the checkpoint passes. Rules are pasted into the prompt. Security runs only when the diff touches auth, SQL, migrations, or workflows.

### Consequences

- A checkpoint costs one builder context plus one short review, and resume does not re-read the tree.
- A failed fix stops for a person instead of relaunching the stage.
- Acceptance cases, the checkpoint file, the commit, and the human app review stay.

### Alternatives considered

- **Keep a fresh agent per gate and a four-round debate:** measured at about 3.3 times the launches of one builder plus one review. Rejected.
- **Drop the reviewer:** the builder would mark its own homework. Rejected.
