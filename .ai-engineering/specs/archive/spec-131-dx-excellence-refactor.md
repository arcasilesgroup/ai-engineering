---
spec: spec-131
slug: dx-excellence-refactor
title: spec-131 — DX Excellence Refactor — Trimmed (M2 + M4-residual + M5 + M6-residual + M7 + M1-residual + S7 spec-lint)
status: approved
approved_at: 2026-05-11
approved_by: operator
effort: large
branch: spec-128/context-overrides-refactor
pr: arcasilesgroup/ai-engineering#509
target_dispatch: /ai-autopilot
source_brief: .ai-engineering/specs/drafts/dx-excellence-refactor-brief.md
chains_after: spec-129 (operator-marked complete 2026-05-11; lifecycle mark_shipped pending PR merge)
---

## Summary

> **North Star (brief §0)**: a first-time engineer types `/ai-start`, sees one
> canonical chain, and reaches a merged PR without ever asking "which command?".
> Every skill self-describes. Every script is deterministic before the LLM
> thinks. Every IDE behaves identically. Every governance file owns one job and
> one job only. **Every sub-spec wave below re-anchors to this North Star
> before any code lands.**

The framework's developer experience fails on six axes — naming, markdown canon,
deterministic preprocessor coverage, twin flows, model/dispatch economics, and
hook robustness — surfaced by an audited operator brief
([brief](./drafts/dx-excellence-refactor-brief.md), 592 lines, evidence-anchored).
Roughly half of the original M1–M7 roadmap (full M1 renames, M3 preprocessor
library, M6 no-suppression gate, `_history.md` rotation) already shipped via
spec-127, spec-128, and spec-129. This spec captures the **residual,
non-duplicated work** that genuinely moves the DX bar: byte-equivalent markdown
mirrors with a project-identity CONSTITUTION; a single end-of-implementation
quality loop replacing per-task verify+review (≈90 % gate-run reduction); a
patch-ready `/ai-plan` that lets `/ai-build` run on a cheap model tier;
sub-agent-aware hook lanes that stop blocking legitimate read-only probes; and
the docs / onboarding surface that ties the chain together. The work ships
inside the current branch (`spec-128/context-overrides-refactor`) and the
active PR ([#509](https://github.com/arcasilesgroup/ai-engineering/pull/509)) —
no new branch and no new PR are opened. Spec-129's work-stream is
operator-marked complete (2026-05-11); its spec body is archived at
`.ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md` and
this spec now occupies the canonical `.ai-engineering/specs/spec.md` slot.

## Goals

> Sub-specs are introduced as `S<n>-…` so `/ai-autopilot` Phase 1 can decompose
> them into parallel waves. Acceptance criteria use `❑` to match the brief
> convention.

### S1 — Markdown Canon Reset (Mirror Strategy + Project-Identity CONSTITUTION)

- ❑ A single `templates/project/CANONICAL.md` template carries the canonical
  "how AI works in this repo" payload (TOC per brief §2.3) including §10
  first-class engineering principles (KISS / YAGNI / SOLID / DRY / TDD / SDD /
  Clean Code / Hexagonal Architecture) with definition + concrete rules +
  anti-patterns + example each.
- ❑ `<repo>/AGENTS.md`, `<repo>/CLAUDE.md`, `<repo>/GEMINI.md`,
  `<repo>/.github/copilot-instructions.md` are **byte-equivalent** mirrors of
  CANONICAL.md (frontmatter / IDE banner aside). No `@AGENTS.md` import. No
  symlinks. No cross-references.
- ❑ `<repo>/.gemini/GEMINI.md` deleted (dead path — Gemini CLI does not read
  in-repo `.gemini/`).
- ❑ `<repo>/.codex/AGENTS.md` not created (Codex reads root AGENTS.md
  natively).
- ❑ `tools/skill_lint/md_mirror.py` checks: (a) sha256 equivalence of the four
  mirrors' canonical payload; (b) no `@AGENTS.md` import in CLAUDE.md;
  (c) no orphan `.gemini/GEMINI.md`; (d) no orphan `.codex/AGENTS.md`;
  (e) CONSTITUTION.md does not contain canonical AI-behaviour headers
  (`Simplicity First`, `Plan-Mode Default`, `KISS`, etc.).
- ❑ `tools/skill_lint/principles.py` checks every SKILL.md `## Workflow`
  cites at least one `§10.x` principle anchor.
- ❑ `/ai-constitution` skill is refactored: interview-driven, produces a
  **project-identity** CONSTITUTION.md (Mission, Stakeholders, Vocabulary,
  Prohibitions, Compliance gates, Anti-goals, Boundaries, Escalation,
  Language, Lifecycle phase). All AI-behaviour content currently in
  CONSTITUTION.md is migrated into CANONICAL.md before lint enforcement.
- ❑ `scripts/sync_mirrors/core.py` surfaces 5.5 / 7 / 7.5 / copilot are
  refactored to read CANONICAL.md and emit byte-equivalent payload. The
  cross-ref line at `core.py:1103` ("See [AGENTS.md](../AGENTS.md) …") is
  removed. The in-repo `.gemini/GEMINI.md` write is dropped.
  `python scripts/sync_command_mirrors.py --check` is idempotent (running it
  twice produces no diff). No new sync entry point.
- ❑ `/ai-ide-audit` extended to assert the mirror contract per IDE
  (Claude / Codex / Gemini / Copilot / Antigravity).
- ❑ Functional verification: Claude `/memory`, Gemini CLI, Codex CLI,
  Antigravity v1.20.3+, and Copilot each load the full canonical payload from
  the repo root without manual configuration.
- ❑ The **strict content contracts table from brief §2.3** (per-file
  MUST contain / MUST NOT contain for AGENTS / CLAUDE / GEMINI /
  `.github/copilot-instructions.md` / `.gemini/GEMINI.md` /
  `.codex/AGENTS.md` / `.github/instructions/*` / `.agent/rules/*` /
  CONSTITUTION / README / CONTRIBUTING / `docs/getting-started.md`) is
  transcribed into CANONICAL.md as an authoring reference and enforced
  by `md_mirror.py` where mechanically checkable.

### S2 — Single Quality Loop + Chain Doc Reset (M4-residual)

- ❑ `/ai-build` SKILL.md: zero references to per-task verify+review inside the
  task loop. A single final-quality-loop phase exists before `/ai-pr`
  (verify + review dispatched once on the full changeset). Clean → `/ai-pr`.
  Blockers → STOP + escalate to operator (no auto-retry).
- ❑ `/ai-autopilot` SKILL.md: Phase 4 contains zero per-task verify+review
  references; Phase 5 is **single-round** ("round<3 → fix and re-assess"
  language removed). Verify + review + guard dispatched once in parallel on
  full changeset. Clean → Phase 6. Blockers → STOP + escalate.
- ❑ Canonical chain in AGENTS / CLAUDE / GEMINI / copilot-instructions reads
  `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr` — `/ai-commit` is not
  mentioned in the chain. `/ai-commit` SKILL.md is preserved verbatim as a
  standalone off-chain skill for WIP-only invocations.
- ❑ `/ai-build`, `/ai-autopilot`, `/ai-pr` continue to live as separate skills
  with separate contracts (SRP §10.3). No fusion. `/ai-autopilot` Phase 4
  still delegates to `/ai-build` agents.
- ❑ `/ai-cleanup` SKILL.md adds an explicit step that rotates `_history.md`
  for shipped specs (verification only — the rotation is already implemented
  by `.ai-engineering/scripts/spec_lifecycle.py mark_shipped`).
- ❑ A shared `--consolidate-spec` action wired into `/ai-cleanup`, `/ai-pr`,
  and `/ai-brainstorm`: delete finalised spec file, append a row to
  `_history.md`, leave the slot ready.
- ❑ Telemetry on the dogfood corpus shows ≈90 % drop in `verify_dispatch` and
  `review_dispatch` event counts per spec versus the pre-trim baseline.

### S3 — Models, Effort, and Dispatch Economics (M5)

- ❑ Every `.claude/skills/ai-*/SKILL.md` (and its 3 mirrors) declares
  `effort: cheap|mid|high` and `model_tier: haiku|sonnet|opus` in
  frontmatter.
- ❑ A new lint `tools/skill_lint/effort.py` (or extension of an existing
  lint) enforces the frontmatter contract and fails CI on any skill missing
  the declaration.
- ❑ `/ai-plan` SKILL.md upgraded to **exhaustive patch-ready mode**: plan
  output includes concrete patch hunks per task whenever a deterministic
  edit is possible. The output template carries a "Principles applied" line
  per task referencing §10.x anchors.
- ❑ `/ai-build` reads the plan and dispatches the cheap tier when patch
  hunks are present (deterministic execution), the mid tier when judgment
  is required, and escalates to high tier on operator demand only.
- ❑ Dispatch decisions are logged to the audit chain
  (`framework-events.ndjson`) with `model_tier` and `effort` fields so token
  economics can be reported by `ai-eng audit tokens --by skill`.
- ❑ **M5 sub-brainstorm artefact**: per brief §2.6, the cheap/mid/high
  tier mapping per skill is captured as a structured policy artefact
  (`docs/model-dispatch-policy.md` or equivalent) that lists every
  skill and its tier assignment with rationale. The mapping is
  consumed by the `effort.py` lint to verify the declared
  frontmatter matches the policy.

### S4 — Hooks & Robustness Residual (M6-residual)

- ❑ `_lib/hook_context.py` gains `agent_kind` (main vs subagent) by
  inspecting `transcript_path` / parent-session linkage. Sub-agents are
  distinguished from the main thread at every hook invocation.
- ❑ A **sub-agent policy lane** in `prompt-injection-guard.py`: a positive
  allow-list for read-only commands (`rg`, `grep`, `find`, `ls`, `cat`
  without redirect) is evaluated before the IOC pattern loop. Sub-agent
  read-only probes no longer trigger integrity-mode denials.
- ❑ Integrity failures surface to **stderr** with a one-line reason +
  remediation. A distinct exit code (3=integrity, 2=injection) lets callers
  branch on the cause. The empty-stderr regression (root cause:
  `_lib/hook-common.py:526-529`) is fixed and covered by a regression test.
- ❑ A **trusted-script lane**: scripts hash-pinned in `hooks-manifest.json`
  and invoked as a single argv bypass RTK rewriting and IOC re-evaluation
  of internal subprocesses. `session_bootstrap.py` is registered on this
  lane; same pattern is documented for future preprocessors.
- ❑ `.claude/settings.json:19` `Bash(*--no-verify*)` substring glob is
  replaced with a token-aware shlex matcher (no false positives on
  unrelated env-var prefixes or argv positions).
- ❑ Claude Code `UserPromptSubmit` hook detects missing `node` and falls
  back gracefully (silent skip + structured warning) rather than emitting
  `/bin/sh: node: command not found`.
- ❑ Engram tool-prefix references throughout the codebase
  (`mcp__engram__*` → `mcp__plugin_engram_engram__*`) are reconciled. Hook
  emissions, ToolSearch hints, and bootstrap docs use the canonical
  prefix.

### S5 — Docs, Evangelism, and Cross-IDE Audit Extension (M7)

- ❑ `docs/getting-started.md` exists: 3-minute path (install → `/ai-start`
  → first `/ai-brainstorm` → first PR) per brief §2.7. No ceremony, no
  internals.
- ❑ `README.md` rewritten: install, value-prop, links to AGENTS.md and
  CONSTITUTION.md. No skill list, no agent list, no chain duplication
  (those live in CANONICAL.md → AGENTS.md).
- ❑ `CONTRIBUTING.md` updated: dev setup, PR process, test commands, repo
  layout in one paragraph. No duplication of canonical content.
- ❑ `tests/docs/test_links.py` passes (every reference link resolves).
- ❑ `CHANGELOG.md` summarises every breaking rename, mirror split,
  CONSTITUTION rescope, and gate-loop trim shipped by this spec. No
  backwards-compat shims.
- ❑ `/ai-ide-audit` IDE matrix extended to include **Antigravity** with
  per-IDE assertions (native path + mirror contract + lint pass).

### S6 — Naming Lint + PowerShell Parity Residual (M1-residual) + DRY Reconciliation

- ❑ `tools/skill_lint/naming.py` enforces the 5 rules from brief §2.5
  (R1 `ai-` prefix · R2 verb-noun + banned metaphor list ·
  R3 paired lifecycle verbs · R4 kebab-case ·
  R5 `.sh` ↔ `.ps1` sibling parity). Wired into pre-commit.
- ❑ `.ai-engineering/scripts/scheduled/simplify-sweep.ps1` exists and is
  tested against the same fixtures as the `.sh` sibling.
- ❑ `_lib/copilot-common.ps1` parity verified (file already present —
  asserts only).
- ✅ Superseded by operator authorization 2026-05-12 — rename `ai-skill-tune` → `ai-skill-improve` (see D-131-09b).
- ❑ `copilot-instinct-extract.sh` / `copilot-instinct-observe.sh` /
  `copilot-strategic-compact.sh` / `copilot-mcp-health.sh` /
  `copilot-skill.sh` / `copilot-error.sh` / `copilot-agent.sh` renames are
  **deferred** to a follow-up spec (not in scope here; see Non-Goals).
- ❑ **DRY fix (brief §1 row 14)**: `/ai-brainstorm`'s
  `handlers/prompt-enhance.md` no longer reimplements 2 of `/ai-prompt`'s
  7 techniques inline. The handler delegates to `/ai-prompt` (single
  source of truth). Same change mirrored in `.github/skills/ai-brainstorm/`
  + `.codex/` + `.gemini/`. Lint check (extension of `naming.py` or new
  `dry.py`) flags duplicated technique catalogues.
- ❑ **Description disambiguation (brief §1 row 15)**: `/ai-research`
  and `/ai-explore` SKILL.md descriptions are rewritten to make the
  tier distinction explicit (`/ai-research` = external evidence with
  citations, 4-tier escalation; `/ai-explore` = codebase-only,
  read-only). The "When to Use" sections cite each other as the
  off-ramp. Tier mechanism doc updated in `/ai-research` references.

### S7 — Spec.md Schema Validator + Frontmatter Lint

- ❑ `tools/spec_lint/` package exists (parallel to `tools/skill_lint/`) with
  `cli.py` + `checks/` modules: `frontmatter.py`, `sections.py`,
  `decisions.py`, `non_goals.py`, `references.py`.
- ❑ `frontmatter.py` enforces the four required fields from
  `.ai-engineering/contexts/spec-schema.md` (`spec` / `title` / `status` /
  `effort`) and validates enum values (`status` ∈ {draft, approved,
  in-progress, done}; `effort` ∈ {trivial, small, medium, large}). Allows
  declared extras (`branch`, `pr`, `slug`, `target_dispatch`,
  `source_brief`, `chains_after`) via an explicit allow-list; unknown keys
  surface as advisory warnings, not blockers (preserve operator
  ergonomics).
- ❑ `sections.py` enforces the five required sections (`## Summary`,
  `## Goals`, `## Non-Goals`, `## Decisions`, `## Risks`) by exact
  level-2 heading match.
- ❑ `decisions.py` enforces (a) each `## Decisions` entry starts with a
  decision ID `D-<spec-id>-<NN>` where `<spec-id>` matches the frontmatter
  `spec:` value (numeric `D-NNN-NN` when the spec id is numeric;
  slug-derived form allowed otherwise), and (b) each entry carries a
  `*Rationale*:` line. Bullet-form (`- **D-NNN-NN — …**`) and
  level-3-heading form (`### D-NNN-NN — …`) both accepted.
- ❑ `non_goals.py` fails when `## Non-Goals` is empty.
- ❑ `references.py` validates prefix convention (`pr:`, `work-item:`,
  `doc:`, `research:`) and `pr:` shape (`<owner>/<repo>#<n>` or full
  URL).
- ❑ `tools/spec_lint/cli.py` runs all checks; `python -m spec_lint` exits
  non-zero on blockers, zero on advisory warnings only.
- ❑ `tests/unit/test_spec_lint.py` covers each check positive +
  negative + fixture; `tests/integration/test_spec_lint_e2e.py` runs the
  CLI against `.ai-engineering/specs/spec.md` (self-validation) and
  against `.ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md`
  (legacy compatibility).
- ❑ `tools/spec_lint` wired into pre-commit (`.pre-commit-hooks.yaml` +
  `.git/hooks/pre-commit` source) — hot-path budget ≤500 ms per
  invocation.
- ❑ `.ai-engineering/contexts/spec-schema.md` updated to (a) document
  the declared extras allow-list, (b) accept both bullet and heading
  decision-entry forms explicitly, (c) link to `tools/spec_lint` as
  the enforcement surface.
- ❑ CI gate added (`.github/workflows/spec_lint.yml` or extension of
  an existing workflow) runs `python -m spec_lint` on PRs that modify
  `.ai-engineering/specs/spec.md`.

### Cross-cutting

- ❑ All work lands in branch `spec-128/context-overrides-refactor` and the
  existing PR [#509](https://github.com/arcasilesgroup/ai-engineering/pull/509).
- ❑ Sub-specs S1–S7 ship as independent waves coordinated by
  `/ai-autopilot` Phase 1 decomposition. Dependencies: S1 → none;
  S2 → none; S3 ← S1 (frontmatter contract leverages §10 anchors); S4 → none;
  S5 ← S1 (links into canonical content) ← S2 (chain doc) ← S4 (trusted-script
  lane referenced in docs); S6 → none; S7 → none (independent — but
  S7 self-validates the rest of this spec after merge).
- ❑ Every SKILL.md author or modification respects the spec-127 layout
  contract (`## Quick start` / `## Workflow` / `## Examples` /
  `## Integration` — ≤120 lines).
- ❑ **Every sub-spec wave re-anchors to the §0 North Star** (per brief
  §6 hand-off checklist) before code lands: the deep-plan emitted by
  `/ai-plan` for each S1–S7 wave begins with a one-paragraph "How this
  wave moves the North Star" preamble; `/ai-autopilot` Phase 5
  quality loop fails the wave if the preamble is missing.
- ❑ Spec activation: `/ai-autopilot` reads `.ai-engineering/specs/spec.md`
  per the standard contract. The previous occupant
  (spec-129 `Skills + Agents Excellence Refactor — Pragmatic Scope`,
  operator-marked complete 2026-05-11) is archived adjacent at
  `.ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md`
  for traceability; `spec_lifecycle.py mark_shipped` is run for spec-129
  once PR #509 merges.

## Non-Goals

1. **No new branch** opened. **No new PR** opened. All work goes to
   `spec-128/context-overrides-refactor` and PR #509 (operator constraint).
2. ~~No re-rename of `ai-skill-tune` to `ai-skill-improve`~~ — **superseded
   2026-05-12 by operator authorization (D-131-09b)**; the rename is
   approved under the DX excellence brief M1 (self-describing-verb
   rationale).
3. **No renames of `copilot-instinct-*.sh` / `copilot-strategic-*.sh` /
   `copilot-mcp-health.sh` / `copilot-skill.sh` / `copilot-error.sh` /
   `copilot-agent.sh`** — deferred to a follow-up; spec-129 intentionally
   skipped them.
4. **No re-implementation of the deterministic preprocessor library** —
   spec-129 (commit `95906a21`) already shipped `manifest_reader.py`,
   `git_activity.py`, `markdown_render.py` under
   `.ai-engineering/scripts/skills/skill_scripts_lib/`. Sub-specs that
   *consume* the library are still allowed.
5. **No re-implementation of `_history.md` rotation** — already shipped via
   `.ai-engineering/scripts/spec_lifecycle.py mark_shipped`.
6. **No re-implementation of the `no_suppression` security gate** — spec-127
   (commit `87f55be7`) already shipped it.
7. **No new IDE adapter** beyond Claude / Codex / Gemini / Copilot /
   Antigravity (audit-only).
8. **No skill marketplace, no plugin store, no remote skill fetch.**
9. **No new agent persona.** Renames apply, removals apply, additions do
   not.
10. **No backwards-compatibility shims** for renamed files, deleted files,
    or migrated content — hard rename, hard delete, hard migration, CHANGELOG
    documents the breakage.
11. **No CONSTITUTION auto-generation** of AI-behaviour articles — the
    refactor moves all AI-behaviour out of CONSTITUTION.md and into
    CANONICAL.md.
12. **No `keyring` change** — operator was offline at the time of
    observation; lockfile already hash-pins; no bug. Source brief §1 row 17
    (informational only).
13. **No multi-round retry inside the new quality loop** — fail-loud only.
    Multi-round retries are explicitly out of scope.
14. **No re-execution of spec-129's work-stream.** Operator marked it
    complete 2026-05-11; its spec body is preserved at
    `.ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md`
    for traceability and `spec_lifecycle.py mark_shipped` runs after
    PR #509 merges.

## Decisions

- **D-131-01 — Trim scope to non-duplicated residual.** Drop full M1 (renames
  already executed in spec-129), full M3 (preprocessor library shipped in
  spec-129), M6 no-suppression gate (shipped in spec-127), and `_history.md`
  rotation (shipped via `spec_lifecycle.py`). Retain M2, M4-residual, M5,
  M7, M6-residual, and M1-residual.
  *Rationale*: avoids re-work, prevents conflict with spec-129 locks,
  matches operator's "simplify-before-build" feedback memory.

- **D-131-02 — Ship in place on `spec-128/context-overrides-refactor` and
  PR #509.** No new branch. No new PR. `/ai-autopilot` operates in place
  (no fresh worktree from `main`).
  *Rationale*: operator constraint stated verbatim ("todo el trabajo aquí").
  Sub-specs S1-S6 file scope does not collide with spec-128 (contexts) or
  spec-129 (`skill_scripts*`).

- **D-131-03 — Markdown mirror strategy = byte-equivalent payload.** No
  `@AGENTS.md` import. No symlinks. No cross-references. Each of AGENTS.md /
  CLAUDE.md / GEMINI.md / `.github/copilot-instructions.md` is standalone
  and identical (frontmatter / banner aside).
  *Rationale*: every IDE's path-discovery quirk is eliminated; the mirroring
  cost is paid once in CI by `md_mirror.py`. Source brief §2.3.

- **D-131-04 — `/ai-constitution` pivots from generator-of-articles to
  project-identity interview.** Output sections: Mission, Stakeholders,
  Vocabulary, Prohibitions, Compliance gates, Anti-goals, Boundaries,
  Escalation, Language, Lifecycle phase. AI-behaviour content migrates
  out into CANONICAL.md.
  *Rationale*: source brief §1 rows 3b / 5; CONSTITUTION must own project
  identity, not framework behaviour. Lint enforces no overlap.

- **D-131-05 — Single end-of-implementation quality loop, single round,
  fail-loud.** Drop per-task verify+review in `/ai-build` and
  `/ai-autopilot`. Each task self-validates via TDD §10.5. One final round
  on full changeset. Blockers STOP and escalate; no auto-retry.
  *Rationale*: source brief §1 row 12 + token economics estimate
  (≈90 % gate-run reduction, ~13-19 min and ~1.3-1.8M tokens saved per
  10-task spec). Auto-retry masks root causes; fail-loud forces operator
  judgment.

- **D-131-06 — `/ai-build`, `/ai-autopilot`, `/ai-pr`, `/ai-commit` stay
  separate skills.** `/ai-autopilot` continues to delegate to `/ai-build`
  agents in Phase 4. `/ai-commit` stays as a standalone off-chain skill for
  WIP-only invocations.
  *Rationale*: SRP §10.3. Fusing them violates the contract surface
  operators have memorised; brief §2.2 explicit.

- **D-131-07 — Canonical chain documentation omits `/ai-commit`.** The
  chain in CANONICAL.md (and therefore in AGENTS / CLAUDE / GEMINI /
  copilot-instructions) reads
  `/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`.
  `/ai-pr` continues to run the commit pipeline internally.
  *Rationale*: source brief §1 rows 1-2; "double-execution" perception comes
  from the chain doc, not from the skills. Fix is workflow-level.

- **D-131-08 — Mandatory `effort:` and `model_tier:` SKILL.md
  frontmatter.** Every skill declares cheap / mid / high effort and
  haiku / sonnet / opus model tier. Lint enforces. Audit chain records the
  dispatch decision per invocation.
  *Rationale*: brief §2.6. Investing in `/ai-plan` (high tier) is what
  unlocks cheap-tier execution downstream. Observability is required to
  confirm the token-economics estimate.

- **D-131-09 — Honour spec-129 D-129-03 lock: 47-skill baseline, no
  `ai-skill-tune` rename.** Skill count drift to 48 is reconciled by
  inventorying the addition rather than by churn.
  *Rationale*: operator memory + spec-129 lock; brief data ("49 skills",
  "ai-skill-improve") is stale.

- **D-131-09b (2026-05-12) — Operator override: D-129-03 lock released;
  rename `ai-skill-tune` → `ai-skill-improve` approved direct** (DX
  excellence brief M1, lines 366-395). Rationale: `improve` is a
  self-describing verb naming the operation; `tune` is a domain metaphor.
  47-skill baseline preserved (1-for-1 substitution).

- **D-131-10 — Defer `copilot-instinct-*.sh` and related renames.** Out of
  scope for this spec. Reopen in a focused naming-cleanup spec once the
  Antigravity audit extension catches any hidden references.
  *Rationale*: spec-129 intentionally skipped them; pulling them in here
  inflates blast radius without acceptance gains for the residual.

- **D-131-11 — Sub-agent policy lane is positive-allow-list-first.** Hook
  read-only commands clear immediately (`rg`, `grep`, `find`, `ls`,
  `cat` without redirect). IOC patterns run only on the residual.
  *Rationale*: source brief §1 rows 16 / 18; integrity hook empty-stderr
  bug class. Positive allow-list is cheaper and safer than IOC tuning.

- **D-131-12 — Trusted-script lane is hash-pinned, not path-pinned.**
  Entries in `hooks-manifest.json` carry `sha256` of the script;
  invocation must match a single argv (no `eval`, no piping). RTK
  rewriting and IOC re-evaluation are bypassed for the inner subprocesses
  triggered by the trusted script.
  *Rationale*: brief §M6 + §2.4.1. Hash pinning inherits the existing
  `hooks-manifest.json` invariant and avoids string-match exploits.

- **D-131-13 — `/ai-autopilot` consumes this spec and produces N parallel
  sub-spec waves.** Phase 1 decomposes S1-S6 into independent sub-specs
  honouring the dependency edges declared under "Cross-cutting". Each
  sub-spec gets its own deep plan via `/ai-plan` and its own implementation
  wave via `/ai-build` agents. The single final quality loop (D-131-05) is
  applied per sub-spec.
  *Rationale*: operator directive ("lo dejamos listo para autopilot")
  + brief §6 hand-off checklist + autopilot Phase 1 contract.

- **D-131-14 — Reuse `scripts/sync_mirrors/core.py` plumbing.** No new
  entry point. Surfaces 5.5 / 7 / 7.5 / copilot are refactored internally
  to read CANONICAL.md and emit byte-equivalent payload. The slim copilot
  cross-ref at `core.py:1103` is removed.
  *Rationale*: DRY §10.4; brief §2.3 explicit. Adding a new sync command
  violates the existing one-entry-point invariant.

- **D-131-15 — Anonymous spec.** No PII, no machine paths, no operator
  names in any file shipped by this spec (CHANGELOG, docs, telemetry).
  *Rationale*: operator memory `feedback_anonymous_feedback.md`.

- **D-131-16 — Canonical-slot activation; spec-129 archived adjacent.**
  This spec occupies `.ai-engineering/specs/spec.md`. Spec-129's spec
  body is archived at
  `.ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md`.
  `/ai-autopilot` reads the canonical slot per the standard contract.
  `spec_lifecycle.py mark_shipped` runs for spec-129 once PR #509 merges.
  *Rationale*: operator confirmed spec-129 complete (2026-05-11);
  preserving the spec-129 body adjacent keeps traceability without
  blocking the canonical pointer used by every downstream skill.

- **D-131-18 — Exhaustive brief-coverage audit closed 6 residual gaps.**
  After the spec was drafted, an operator-requested cross-reference
  against `drafts/dx-excellence-refactor-brief.md` (592 lines, §0–§7)
  surfaced 6 items that were implicit but not explicitly covered:
  (G1) brief §1 row #14 `handlers/prompt-enhance.md` DRY delegation to
  `/ai-prompt` → added to S6; (G2) brief §1 row #15 `/ai-research` vs
  `/ai-explore` description disambiguation → added to S6;
  (G3) brief §0 North Star paragraph → added to Summary + Cross-cutting
  wave re-anchor gate; (G4) brief §2.3 strict content-contracts
  per-file table → added to S1 acceptance (transcribed into
  CANONICAL.md as authoring reference); (G5) brief §2.6 M5
  sub-brainstorm artefact → added to S3 as `docs/model-dispatch-policy.md`
  consumed by `effort.py` lint; (G6) brief §6 "re-anchor to North Star
  every wave" → added as Cross-cutting acceptance gate enforced by
  `/ai-autopilot` Phase 5. Brief §1 row #13 (`/ai-brainstorm` step 0
  reference correct) is a documented false-positive in the brief itself
  and requires no action.
  *Rationale*: operator audit ("super importante revisar que la spec
  tiene todo lo que hemos hablado del brief") forced an exhaustive
  cross-reference; closing every gap preserves the brief as the
  single source of truth and prevents downstream surprise when
  `/ai-autopilot` Phase 1 decomposes against the spec.

- **D-131-17 — Add `tools/spec_lint/` as the enforcement surface for
  `.ai-engineering/contexts/spec-schema.md`.** Parallel to
  `tools/skill_lint/`; same CLI shape (`python -m spec_lint`); same
  pre-commit wiring pattern. Unknown frontmatter keys are advisory
  warnings (not blockers) to preserve operator-added metadata
  ergonomics. Both bullet (`- **D-NNN-NN — …**`) and level-3-heading
  (`### D-NNN-NN — …`) decision-entry forms accepted; legacy specs
  pass without rewrite.
  *Rationale*: operator audit surfaced "no automated validator for
  spec.md" (this conversation, 2026-05-11). Schema enforcement is
  currently 100 % manual; the integrity bar for the canonical-chain
  contract should match `SKILL.md` (already linted by
  `tools/skill_lint/`). Backward compatibility (heading + bullet both
  accepted) avoids forcing rewrites of spec-129 or older archive
  bodies.

## Risks

- **R-131-01 — File-scope collision with spec-128 / spec-129 inside
  PR #509.** Mitigation: S1 touches `<repo>/AGENTS.md`, `<repo>/CLAUDE.md`,
  `<repo>/GEMINI.md`, `<repo>/.github/copilot-instructions.md`,
  `<repo>/CONSTITUTION.md`, and `scripts/sync_mirrors/core.py`; none of
  these are in spec-128 (`.ai-engineering/contexts/*`) or spec-129
  (`.ai-engineering/scripts/skills/skill_scripts*`) scope. S2 touches
  `.claude/skills/ai-{build,autopilot,pr,cleanup,brainstorm,commit}/SKILL.md`;
  no overlap. S3 touches all `SKILL.md` frontmatter — may collide if
  spec-129 is still amending skills; sequence S3 after spec-129 lands or
  rebases. Verify with `git status` per wave before dispatch.

- **R-131-02 — Mirror lint flags legitimate IDE-specific extras.**
  Mitigation: define a single "EXTRAS" markdown section (e.g.
  `<!-- ide-extras:start -->` / `:end`) that the lint excludes from the
  sha256 hash. Document the contract in CANONICAL.md.

- **R-131-03 — `/ai-constitution` interview deletes operator-authored
  content.** Mitigation: refactor never overwrites without
  diff + confirm; CONSTITUTION.md migration uses `_history.md`-style
  rotation; lint runs only after migration committed.

- **R-131-04 — Single-round fail-loud surprises operators expecting
  auto-retry.** Mitigation: CHANGELOG entry; `/ai-build` and
  `/ai-autopilot` STOP messages cite the source spec; operator can
  re-dispatch with explicit `/ai-build --rerun-quality-loop` once the
  blocker is addressed.

- **R-131-05 — Token-economics estimate (≈90 % gate reduction) unverified
  on real corpus.** Mitigation: S3 ships audit chain with `model_tier` +
  `effort` fields; measure post-merge on the dogfood corpus and capture
  the actual delta in `LESSONS.md`.

- **R-131-06 — Sub-agent allow-list permits dangerous patterns slipping
  past IOC.** Mitigation: positive-allow-list constrained to verb +
  no-redirect form (no shell pipes, no `;`, no `&&`); IOC retains
  veto on the residual; regression tests cover the bypass cases.

- **R-131-07 — Trusted-script lane drift (script edited without manifest
  refresh).** Mitigation: `AIENG_HOOK_INTEGRITY_MODE=enforce` (already
  default) catches drift on next invocation; CI runs
  `regenerate-hooks-manifest.py --check` per PR.

- **R-131-08 — Antigravity audit lacks a stable detection probe.**
  Mitigation: `/ai-ide-audit` Antigravity check is advisory in this
  spec; CI gate added once the Antigravity CLI exposes a deterministic
  version probe.

- **R-131-09 — `effort:` frontmatter rolls out faster than dispatch logic
  is ready.** Mitigation: ship the lint and frontmatter additions
  first (passive); enable cheap-tier dispatch only after S3 dispatch
  logic lands; `model_tier` is observed but not enforced for one
  release cycle.

- **R-131-10 — Brief uses stale data (49 skills, `ai-skill-improve`).**
  Mitigation: D-131-09 explicit; reviewers compare baseline against
  `.ai-engineering/manifest.yml` skills index, not the brief.

- **R-131-11 — PR #509 grows unwieldy with spec-128 + spec-129 + this
  spec stacked.** Mitigation: operator can split into separate PRs
  later if review fatigue surfaces; spec metadata (`branch:` + `pr:`)
  is the SSOT and remains accurate even under split.

- **R-131-12 — `tools/spec_lint` rejects legacy archive specs.**
  Mitigation: S7 explicitly accepts both bullet and heading decision
  forms; the integration test exercises `spec-129-skills-agents-excellence-pragmatic.md`
  as a fixture and must pass; frontmatter allow-list pre-includes the
  metadata extras already in use across in-flight specs.

- **R-131-13 — Adding a new lint to pre-commit slows the hot path.**
  Mitigation: S7 hot-path budget ≤500 ms per invocation; CI
  enforcement is independent of pre-commit (the gate also runs in
  GitHub Actions); operator can `SKIP=spec-lint` for a local commit
  if needed (CI still blocks).

## References

- pr: arcasilesgroup/ai-engineering#509
- doc: .ai-engineering/specs/drafts/dx-excellence-refactor-brief.md
- doc: .ai-engineering/specs/drafts/cli-ux-overhaul-brief.md
- doc: .ai-engineering/specs/drafts/skills-agents-excellence-refactor.md
- doc: .ai-engineering/specs/drafts/skills-agents-excellence-phase-c.md
- doc: .ai-engineering/specs/spec-129-skills-agents-excellence-pragmatic.md
- doc: .ai-engineering/state/specs/skills-agents-excellence-pragmatic.json
- doc: .ai-engineering/state/specs/spec-131.json
- doc: .ai-engineering/contexts/spec-schema.md
- doc: tools/skill_lint/
- doc: tools/spec_lint/ (new, S7)
- doc: CONSTITUTION.md
- doc: AGENTS.md
- doc: CLAUDE.md
- doc: GEMINI.md
- doc: .github/copilot-instructions.md
- doc: .ai-engineering/scripts/spec_lifecycle.py
- doc: scripts/sync_mirrors/core.py
- doc: tools/no_suppression/
- doc: .ai-engineering/scripts/hooks/_lib/hook_context.py
- doc: .ai-engineering/scripts/hooks/_lib/hook-common.py
- doc: https://developers.openai.com/codex/guides/agents-md
- doc: https://code.claude.com/docs/en/memory
- doc: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md
- doc: https://antigravity.codes/blog/user-rules
- doc: https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions
- research: NotebookLM b8a09700-2ce7-4d6c-84d7-82b89765ea53

## Open Questions

1. **CANONICAL.md "extras" mechanism.** Should the IDE-specific extras live
   in a fenced block inside the same file (`<!-- ide-extras -->`) or in a
   separate `templates/project/<ide>-extras.md` that the sync script
   appends per-IDE? Resolution gate: S1 deep-plan via `/ai-plan`.
2. **S3 sequencing vs spec-129.** Spec-129 may still be amending SKILL.md
   frontmatter in flight; should S3 fork into "passive frontmatter add"
   (independent) + "dispatch logic" (sequenced after spec-129 merges)?
   Resolution gate: re-check `git log --since` at autopilot Phase 0.
3. **Telemetry corpus for D-131-05 verification.** Should we record the
   pre-trim baseline on the current PR #509 changeset, or wait for the
   first post-merge spec to land before measuring? Resolution gate:
   S5 plan.
4. **Antigravity audit probe.** Concrete probe for `/ai-ide-audit` —
   parse `~/.gemini/settings.json` `context.fileName` for `AGENTS.md`?
   File a follow-up if no deterministic probe surfaces.
5. **CONSTITUTION.md migration content review.** Operator-authored
   prohibitions / compliance gates currently inside CONSTITUTION.md need
   to be preserved verbatim; should the migration be an interactive
   `/ai-constitution --migrate` flow or a one-shot script? Resolution
   gate: S1 deep-plan.
