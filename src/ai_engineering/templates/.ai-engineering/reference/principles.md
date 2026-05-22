# Engineering Principles

> Canonical home for the eight first-class engineering principles
> (§10.1–§10.8) plus the "Operating Mindset" companion list
> (§1–§9 Karpathy / Boris one-liners). Extracted from the IDE
> mirrors (`AGENTS.md` / `CLAUDE.md` /
> `.github/copilot-instructions.md`) by spec-134 sub-005 so the
> mirrors stay lean while the §10.x anchors remain stable.
>
> Applies §10.4 (DRY) — one canonical source — and §10.1 (KISS) —
> the mirrors point here; this file owns the prose.

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

## Operating Mindset (§1–§9 companion)

The nine Karpathy / Boris one-liners that frame the §10 principles.
The mirrors carry only the condensed list (name + tagline); the
prose below is the lossless companion — read this when the mirrors'
condensed bullets need expansion.

### §1 Think Before Coding (Karpathy §1)

Read the failing input, the existing code path, and the spec acceptance
gates BEFORE you change anything. The cheap edit is the wrong edit if
the constraints have not been internalised.

### §2 Simplicity First (Karpathy §2 + Boris core)

The fewest moving parts that satisfy the spec wins. If you can delete
code instead of adding it, prefer the deletion. No abstraction without
two concrete callers. No new module without a clear seam.

### §3 Surgical Changes (Karpathy §3 + Boris Minimal Impact)

Each commit changes one thing. When you touch a file, make the
minimum edit that satisfies the test. Drive-by refactors belong in
their own commit with their own justification.

### §4 Goal-Driven Execution (Karpathy §4 + Boris Verification Before Done)

Every task has an acceptance gate. Run the gate before you claim done.
Test output, lint output, gate output — all green or the task is not
done. "Would a staff engineer approve this?" is the bar.

### §5 Plan-Mode Default (Boris §1)

Enter plan mode for any non-trivial task (3+ steps or architectural
decisions). Stop and re-plan when something goes sideways instead of
pushing through. Reduce ambiguity upfront via `/ai-brainstorm`.

### §6 Subagent Strategy (Boris §2)

Offload research, exploration, and parallel analysis to subagents.
One task per subagent for focused execution. Never have one subagent
do two unrelated things. Each runs in its own context window — use
that.

### §7 Self-Improvement Loop (Boris §3)

After any user correction, update `.ai-engineering/LESSONS.md` with
the pattern. Iterate on lessons until the mistake rate drops. Read
lessons proactively at session start.

### §8 Demand Elegance (Boris §5)

Pause and ask "is there a more elegant way?" for non-trivial changes.
Skip for simple, obvious fixes. Clever is bad; simple and clear is
elegant.

### §9 Autonomous Bug Fixing (Boris §6)

When given a bug report, fix it. Don't ask for hand-holding. If you
see a bug while working on something else, fix it and mention it in
the commit.

## Related

- `AGENTS.md` / `CLAUDE.md` / `.github/copilot-instructions.md`
  carry the canonical chain and surface index; they point here for
  full principle prose.
- `CONSTITUTION.md` owns project identity only (mission, stakeholders,
  prohibitions); AI-behaviour headers live here, not there.
- `docs/mirror-authoring.md` — per-file authoring contract.
- `docs/surface-axioms.md` — Surface / No-Twin axioms.
