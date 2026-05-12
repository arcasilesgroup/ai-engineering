# Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is
> the canonical multi-IDE entry point for "how AI works in this repo".
> Every IDE-native mirror (AGENTS.md, CLAUDE.md, GEMINI.md,
> .github/copilot-instructions.md) carries identical canonical payload
> — IDE-specific extras live in the fenced block at the bottom.

## 0. Bootstrap

Every session, the first action is:

1. Read [CONSTITUTION.md](CONSTITUTION.md) (project identity:
   Mission / Stakeholders / Vocabulary / Prohibitions / Compliance gates /
   Anti-goals / Boundaries / Escalation / Language / Lifecycle phase).
2. Read `.ai-engineering/manifest.yml` (configuration source of truth).
3. Query `.ai-engineering/state/state.db` `decisions` table (active
   decisions and risk posture).
4. No implementation without an approved spec — invoke `/ai-brainstorm`
   first when a task has no spec.

## 1. Think Before Coding (Karpathy §1)

Read the failing input, the existing code path, and the spec acceptance
gates BEFORE you change anything. The cheap edit is the wrong edit if
the constraints have not been internalised.

## 2. Simplicity First (Karpathy §2 + Boris core)

The fewest moving parts that satisfy the spec wins. If you can delete
code instead of adding it, prefer the deletion. No abstraction without
two concrete callers. No new module without a clear seam.

## 3. Surgical Changes (Karpathy §3 + Boris Minimal Impact)

Each commit changes one thing. When you touch a file, make the
minimum edit that satisfies the test. Drive-by refactors belong in
their own commit with their own justification.

## 4. Goal-Driven Execution (Karpathy §4 + Boris Verification Before Done)

Every task has an acceptance gate. Run the gate before you claim done.
Test output, lint output, gate output — all green or the task is not
done. "Would a staff engineer approve this?" is the bar.

## 5. Plan-Mode Default (Boris §1)

Enter plan mode for any non-trivial task (3+ steps or architectural
decisions). Stop and re-plan when something goes sideways instead of
pushing through. Reduce ambiguity upfront via `/ai-brainstorm`.

## 6. Subagent Strategy (Boris §2)

Offload research, exploration, and parallel analysis to subagents.
One task per subagent for focused execution. Never have one subagent
do two unrelated things. Each runs in its own context window — use
that.

## 7. Self-Improvement Loop (Boris §3)

After any user correction, update `.ai-engineering/LESSONS.md` with
the pattern. Iterate on lessons until the mistake rate drops. Read
lessons proactively at session start.

## 8. Demand Elegance (Boris §5)

Pause and ask "is there a more elegant way?" for non-trivial changes.
Skip for simple, obvious fixes. Clever is bad; simple and clear is
elegant.

## 9. Autonomous Bug Fixing (Boris §6)

When given a bug report, fix it. Don't ask for hand-holding. If you
see a bug while working on something else, fix it and mention it in
the commit.

## 10. Engineering Principles

The eight first-class principles below are non-negotiable. Every
SKILL.md `## Workflow` MUST cite at least one §10.x anchor in its
procedure so the principle the skill applies is traceable.

### §10.1 KISS

**Definition.** Keep It Simple, Stupid. The simplest design that
satisfies the requirement wins.

**Rules.**
1. No premature optimization. Profile first, optimize second.
2. No clever one-liners. Boring code reads faster.
3. No abstractions without two concrete callers.
4. Public API surface stays minimal — every export is a maintenance
   cost.

**Anti-patterns.**
- Generic "framework" code with one consumer.
- Single-call-site dependency injection layers.
- Nested ternaries.

**Example.** A function that takes a list and returns the sum is
`sum(items)`. Do not introduce a `Summable` protocol.

### §10.2 YAGNI

**Definition.** You Aren't Gonna Need It. Build for the spec in
front of you, not the spec you imagine.

**Rules.**
1. No "future-proofing" parameters without a current caller.
2. No optional flags without a current use case.
3. Delete dead code on sight; preserve it in git history, not the
   active tree.

**Anti-patterns.**
- "I might need this someday" parameters.
- Configuration knobs with one possible value.
- Empty extension points.

**Example.** A CLI command starts with positional arguments only.
Add `--flags` when a second caller needs them.

### §10.3 SOLID

**Definition.** Five OO principles: Single Responsibility, Open/Closed,
Liskov Substitution, Interface Segregation, Dependency Inversion.

**Rules.**
1. One reason to change per class / module (SRP).
2. Open to extension, closed to modification (OCP).
3. Subtypes substitute base types without surprises (LSP).
4. Many small interfaces beat one large interface (ISP).
5. Depend on abstractions, not concretions (DIP).

**Anti-patterns.**
- God classes that own unrelated concerns.
- `if isinstance` branches on subtypes (LSP smell).
- Wide interfaces with `NotImplementedError` stubs.

**Example.** A `Reader` reads bytes; a `Parser` parses them. Do not
fuse them into a `ReaderParser` because both run in sequence.

### §10.4 DRY

**Definition.** Don't Repeat Yourself. Every piece of knowledge has
one canonical home.

**Rules.**
1. Three copies of the same fact = extract a constant.
2. Three copies of the same logic = extract a function.
3. Cross-IDE mirrors are generated, never hand-edited.

**Anti-patterns.**
- Hand-maintained tables in two files.
- Copy-paste error handlers.
- Shadow definitions of canonical constants.

**Example.** Skill counts live in `manifest.yml`. Markdown mirrors
substitute the count at sync time; they never hard-code it twice.

### §10.5 TDD

**Definition.** Test-Driven Development. RED (failing test) → GREEN
(minimal code) → REFACTOR (stay green).

**Rules.**
1. Write the failing test FIRST. It must fail for the expected
   reason before any production code lands.
2. Write the minimum code to make the test pass — no more.
3. Refactor with all tests still green; this is the only time
   structural change ships without behaviour change.
4. Never weaken a test to make implementation easier; if the test
   is wrong, escalate.

**Anti-patterns.**
- Writing tests after the fact to "cover" code.
- Skipping the REFACTOR step.
- Modifying tests to chase implementation.

**Example.** Before adding a `Cache` class, write
`test_cache_get_returns_none_when_miss` and watch it fail with
`NameError: name 'Cache' is not defined`.

### §10.6 SDD

**Definition.** Spec-Driven Development. Every implementation traces
back to an approved spec under `.ai-engineering/specs/spec.md`.

**Rules.**
1. No implementation without an approved spec.
2. Trivial changes (typo / comment-only / single-line) may use a
   condensed spec; the spec still exists.
3. Spec decisions are immutable once approved — amendments go
   through `/ai-brainstorm` again.
4. Plan tasks reference the decision they implement.

**Anti-patterns.**
- "Drive-by" feature additions inside an unrelated PR.
- Implementing what the spec did not approve.
- Hand-editing `_history.md` instead of running
  `spec_lifecycle.py mark_shipped`.

**Example.** Adding a new CLI subcommand requires a spec section
listing acceptance gates and a `D-<spec>-<NN>` decision row.

### §10.7 Clean Code

**Definition.** Code reads like prose. Names tell the story; bodies
do one thing well.

**Rules.**
1. Functions ≤30 lines; cyclomatic complexity ≤8.
2. Names are precise (`active_users` not `data`).
3. Public functions carry docstrings: contract, args, returns,
   raises.
4. Comments explain "why", not "what" — the code already shows
   what.

**Anti-patterns.**
- Single-letter loop variables outside trivial scope.
- Functions with five-argument signatures.
- Magic numbers without named constants.

**Example.** `def transfer(source_account, target_account, amount)`
beats `def x(a, b, c)` every time.

### §10.8 Hexagonal Architecture

**Definition.** Pure domain logic at the centre; adapters at the
edges; ports in between. Dependencies always point inward.

**Rules.**
1. Domain has zero infrastructure imports (no `requests`, no
   `psycopg`, no `boto3`).
2. Application orchestrates use-cases against ports.
3. Adapters implement ports; tests substitute in-memory adapters.
4. The hexagonal seam is enforced by an import test.

**Anti-patterns.**
- Domain modules calling `httpx.post(...)` directly.
- Adapters leaking domain types up the call chain backwards.
- Ports defined inside infrastructure modules.

**Example.** A `Repository` port lives in `domain/`; a
`PostgresRepository` adapter lives in `infrastructure/db/`.
`pytest tests/architecture/test_layer_isolation.py` proves the
direction.

## 11. Canonical Chain

The active spec workflow is:

**/ai-brainstorm → /ai-plan → /ai-build → /ai-pr**

- `/ai-brainstorm` produces an approved spec at
  `.ai-engineering/specs/spec.md`.
- `/ai-plan` produces an exhaustive patch-ready plan at
  `.ai-engineering/specs/plan.md`.
- `/ai-build` executes the plan (multi-stack implementation gateway,
  D-127-11). For specs with ≥3 concerns or ≥10 file changes,
  `/ai-autopilot` wraps the chain.
- `/ai-pr` runs the final quality loop (verify + review + commit
  pipeline internally) and opens the PR.

`/ai-commit` is preserved as a standalone off-chain skill for WIP
checkpoints. It does NOT appear in the canonical chain (D-131-07).

## 12. Surface Index

## Skills (48)

Canonical skills and agents live under `.claude/`; mirror surfaces under
`.codex/`, `.gemini/`, and `.github/` are byte-equivalent regenerations
written by `scripts/sync_mirrors/core.py`. Invoke a skill via
`/ai-<name>` in the IDE agent surface — never via a synthetic terminal
equivalent.

## Agents (9)

The 9 first-class agents are listed in
`.ai-engineering/manifest.yml` under `agents.registry` and documented at
`.claude/agents/ai-<name>.md`. Each runs in its own context window —
offload research and parallel analysis to them.

## Source of Truth

| Surface | Where |
|---------|-------|
| Skills (48) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (9) | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/contexts/knowledge-placement.md` |
| Hook scripts | `.ai-engineering/scripts/hooks/` |
| CLI | `ai-eng <command>` |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Decisions | `.ai-engineering/state/state.db` `decisions` table |
| Config | `.ai-engineering/manifest.yml` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |

## 13. Hard Rules

The non-negotiable rules below apply to every commit, push, and
risk-acceptance decision.

1. **Secrets gate.** `gitleaks protect --staged` on every commit;
   `semgrep --config .semgrep.yml` + `pip-audit` on every push.
   Findings BLOCK at CRITICAL / HIGH / MEDIUM; LOW warns. Risk
   acceptance flows through the ledger
   (`ai-eng risk accept --finding-id …`), never inline.
2. **No suppression.** No `# noqa`, `# nosec`, `// @ts-ignore`,
   `// nolint`, `# pragma: no cover`, `// NOSONAR`. Refactor or
   risk-accept. Spec-128 sub-d ships the repo-wide gate.
3. **No backwards-compat shims** for renamed files, deleted files,
   or migrated content. Hard rename, hard delete, hard migration.
   CHANGELOG documents the breakage.
4. **Anonymous content.** No PII, no machine paths, no operator
   names in any committed file (specs, CHANGELOG, docs, telemetry).
   Use placeholders (`$HOME/.local/bin`, `$(which …)`) when
   machine-relative references are needed.
5. **Single-round fail-loud quality loop.** `/ai-build`,
   `/ai-autopilot` Phase 5, and `/ai-pr` run one final-quality-loop
   round on the full changeset. Blockers STOP and escalate — no
   auto-retry.
6. **Conventional Commits.** `<type>(<scope>): <subject>` in
   imperative mood. Body explains "why", not "what". Never
   `--no-verify`.

## 14. Strict Content Contracts (per-file authoring reference)

The four IDE mirrors are byte-equivalent in canonical payload (this
file). Each mirror appends an IDE-extras fence with content unique to
that IDE. **Authoring contract** (brief §2.3 verbatim):

| File | MUST contain | MUST NOT contain |
|------|--------------|------------------|
| `<repo>/AGENTS.md` | Full canonical payload (§§0-13), no IDE-extras block. | Any `@AGENTS.md` import. Any IDE-specific runtime knobs. |
| `<repo>/CLAUDE.md` | Full canonical payload + IDE-extras with Hot-Path Discipline, Hooks Configuration, Runtime layer hooks, Token Efficiency, Engram doc pointer, Audit observability. | `@AGENTS.md` import. Cross-IDE skill list. |
| `<repo>/GEMINI.md` | Full canonical payload + IDE-extras with Gemini Hooks Wiring table + Surface Pointers. | `@AGENTS.md` import. Cross-IDE skill list. |
| `<repo>/.github/copilot-instructions.md` | Full canonical payload + IDE-extras with Copilot Hooks Wiring table. | Any `See AGENTS.md` cross-reference (D-131-14). |
| `<repo>/.gemini/GEMINI.md` | (DELETED per D-131-03 — Gemini CLI does not read in-repo `.gemini/`.) | The file itself. |
| `<repo>/.codex/AGENTS.md` | (DOES NOT EXIST — Codex reads root AGENTS.md natively.) | The file itself. |
| `<repo>/.github/instructions/*` | (DELETED per spec-128 D-128-07 — copilot-instructions.md covers it.) | The directory itself. |
| `<repo>/.agent/rules/*` | (NOT USED — framework targets Claude / Codex / Gemini / Copilot natively.) | The directory itself. |
| `<repo>/CONSTITUTION.md` | Project-identity only (10 sections: Mission / Stakeholders / Vocabulary / Prohibitions / Compliance gates / Anti-goals / Boundaries / Escalation / Language / Lifecycle phase). | Any AI-behaviour header (KISS / YAGNI / SOLID / DRY / TDD / SDD / Clean Code / Hexagonal Architecture / Simplicity First / Plan-Mode Default / Surgical Changes / Goal-Driven Execution / Subagent Strategy / Self-Improvement Loop / Demand Elegance / Autonomous Bug Fixing / Think Before Coding). |
| `<repo>/README.md` | Install, value-prop, links to AGENTS.md + CONSTITUTION.md. | Skill list. Agent list. Chain duplication. |
| `<repo>/CONTRIBUTING.md` | Dev setup, PR process, test commands, repo layout. | Duplication of canonical content. |
| `<repo>/docs/getting-started.md` | 3-minute path: install → `/ai-start` → first `/ai-brainstorm` → first PR. | Internals. Skill list. |

This table is the authoring reference. Mechanically-checkable rows
are enforced by `tools/skill_lint/checks/md_mirror.py`:

- sha256 equivalence across the four mirrors (canonical payload
  bytes, fence stripped).
- No `@AGENTS.md` import in any mirror.
- No `.gemini/GEMINI.md` orphan on disk.
- No `.codex/AGENTS.md` orphan on disk.
- No forbidden AI-behaviour header in CONSTITUTION.md.

## 15. IDE-Extras Escape Hatch (R-1.1 / R-131-02 mitigation)

Each IDE mirror MAY append a fenced block carrying content unique to
that IDE (Hot-Path tuning for Claude Code, Hooks Wiring table for
Gemini / Copilot, etc.). The fence is recognised by `md_mirror.py`
and stripped before the sha256 equivalence check.

```
<!-- ide-extras:start -->
…IDE-specific content (hot-path budgets, hooks wiring,
runtime tunables)…
<!-- ide-extras:end -->
```

The block is OPTIONAL — `AGENTS.md` carries no extras (it is the base
mirror). All other mirrors carry at most one fence block.
## 16. Surface Axioms (spec-133 D-133-04)

The **Surface Axiom** + **No-Twin Axiom** are first-class design
rules. The skill/CLI confusion (B17 root) is eliminated at the
design layer, not just the lint layer.

### A1 — Surface Axiom (when may a capability expose `ai-eng <verb>`?)

A capability MAY expose a `ai-eng <verb>` CLI iff ALL THREE hold:

1. **Scriptable from shell / CI** — there is a credible non-interactive
   use case that does NOT require a human in the loop.
2. **Deterministic happy-path** — the default-args invocation completes
   without any AI judgment (the engine is a state machine, not a model).
3. **Structured-machine-readable output** — `--json` returns a stable
   envelope (`{ok, command, code, data, meta}`); exit codes follow
   `_exit_codes.py` category map (0/1/2/78).

If any condition fails, the capability lives only as a `/ai-<name>`
skill. `/ai-start` is a deterministic logo + reminder (A1.c fails:
no structured data) — correctly remains skill-only.

### A2 — No-Twin Axiom (when does the same verb name appear in both surfaces?)

A capability has **one canonical surface per role**. Skill = chat
entry; CLI = shell entry. The same verb name appears in BOTH iff

1. **Same engine** — both surfaces dispatch the same Python code path
   (skill orchestrator invokes the CLI under the hood OR both wrap a
   shared service in `core/`).
2. **Identical contract** — `--json` shape, exit codes, and side-effects
   are byte-equivalent.

Otherwise the verbs MUST be distinct. `/ai-cleanup` (LLM-orchestrated)
and `ai-eng cleanup` (deterministic 7-mode CLI) are distinct verbs by
A2 because the engines differ — the skill calls the CLI but adds AI
judgment on top.

### Enforcement

- `tests/architecture/test_surface_parity.py` asserts no orphan twin
  surfaces (any name that appears in both `.claude/skills/<name>/` and
  `cli_factory.py` registrations must have identical contracts or be
  documented as A2-distinct in `docs/cli-reference.md`).
- `cli_ui_skill_ref.skill_ref(name)` renders every chat-only command
  unambiguously when printed from the CLI (D-133-22).


<!-- ide-extras:start -->
<!-- ide-extras:end -->
