# Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is
> the canonical multi-IDE entry point for "how AI works in this repo".
> Every IDE-native mirror (AGENTS.md, CLAUDE.md, GEMINI.md,
> .github/copilot-instructions.md) carries identical canonical payload;
> IDE-specific extras live in the fenced block at the bottom.

## 0. Bootstrap

Every session: (1) read [CONSTITUTION.md](CONSTITUTION.md) (project
identity); (2) read `.ai-engineering/manifest.yml` (config SoT);
(3) query `.ai-engineering/state/state.db` `decisions` table (active
decisions / risk posture); (4) no implementation without an approved
spec — invoke `/ai-brainstorm` first when a task has no spec.

## Operating Mindset (§1–§9 condensed)

Karpathy / Boris one-liners that frame the §10 principles. Full prose
in [docs/principles.md](docs/principles.md) under "Operating Mindset".

1. **Think Before Coding** — read failing input + spec gates BEFORE editing.
2. **Simplicity First** — fewest moving parts; prefer deletion over abstraction.
3. **Surgical Changes** — one commit, one change; drive-by refactors get their own justification.
4. **Goal-Driven Execution** (Verification Before Done) — green gate before "done"; staff-engineer bar.
5. **Plan-Mode Default** — enter plan mode for non-trivial tasks; re-plan when things go sideways.
6. **Subagent Strategy** — one task per subagent; offload research into fresh context windows.
7. **Self-Improvement Loop** — every user correction updates `.ai-engineering/LESSONS.md`.
8. **Demand Elegance** — "is there a more elegant way?" on non-trivial changes; clear beats clever.
9. **Autonomous Bug Fixing** — fix bugs you spot; mention them in the commit.

## 10. Engineering Principles (pointer)

The eight first-class principles (§10.1 KISS, §10.2 YAGNI, §10.3 SOLID,
§10.4 DRY, §10.5 TDD, §10.6 SDD, §10.7 Clean Code, §10.8 Hexagonal
Architecture) live in [docs/principles.md](docs/principles.md). Every
SKILL.md `## Workflow` cites at least one §10.x anchor; anchors are
stable at the new home.

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

## Skills (53)

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
| Skills (53) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (9) | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/contexts/knowledge-placement.md` |
| Hook scripts | `.ai-engineering/scripts/hooks/` |
| CLI | `ai-eng <command>` |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Decisions | `.ai-engineering/state/state.db` `decisions` table |
| Config | `.ai-engineering/manifest.yml` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |

## 13. Hard Rules

Non-negotiable rules per commit, push, and risk-acceptance decision:

1. **Secrets gate.** `gitleaks protect --staged` on commit;
   `semgrep --config .semgrep.yml` + `pip-audit` on push. BLOCK at
   CRITICAL/HIGH/MEDIUM; LOW warns. Risk acceptance via
   `ai-eng risk accept --finding-id …` (never inline).
2. **No suppression.** No `# noqa`, `# nosec`, `// @ts-ignore`,
   `// nolint`, `# pragma: no cover`, `// NOSONAR`. Refactor or
   risk-accept (spec-128 sub-d gate).
3. **No backwards-compat shims** for renamed/deleted/migrated content.
   Hard rename, hard delete, hard migration. CHANGELOG documents the
   breakage.
4. **Anonymous content.** No PII, no machine paths, no operator names
   in committed files. Use placeholders (`$HOME/.local/bin`, `$(which
   …)`) for machine-relative references.
5. **Single-round fail-loud quality loop.** `/ai-build`,
   `/ai-autopilot` Phase 5, `/ai-pr` run ONE final-quality-loop round
   on the full changeset. Blockers STOP and escalate — no auto-retry.
6. **Conventional Commits.** `<type>(<scope>): <subject>` imperative
   mood. Body explains "why", not "what". Never `--no-verify`.

## 14–16. Pointer rows

The bulk of the canonical-payload prose lives in `docs/` so the
mirrors stay lean (spec-134 sub-005 mirror diet). Authoritative homes:

- **§10 Engineering Principles** → [docs/principles.md](docs/principles.md)
  (§10.1 KISS through §10.8 Hexagonal Architecture; the 34 skill /
  agent files that cite `§10.x` resolve here).
- **§14 Strict Content Contracts** + **§15 IDE-Extras Escape Hatch** →
  [docs/mirror-authoring.md](docs/mirror-authoring.md) (per-file
  authoring table + the `<!-- ide-extras:start -->` fence contract).
- **§16 Surface Axioms** (A1 / A2) →
  [docs/surface-axioms.md](docs/surface-axioms.md) (Surface Axiom and
  No-Twin Axiom; D-133-04 enforcement at `test_surface_parity.py`).

<!-- ide-extras:start -->
## First Action (Gemini CLI)

Your first action in every session MUST be to run `/ai-start`. Do not
respond to any user request until `/ai-start` completes. `/ai-*` are
slash commands in the IDE agent surface, not `ai-eng` CLI subcommands.

## Hooks Wiring (Gemini-specific)

Gemini CLI hook configuration lives in `.gemini/settings.json`. Hook
event mapping (canonical Python script in
`.ai-engineering/scripts/hooks/`):

| Cross-IDE primitive          | Gemini event |
|------------------------------|--------------|
| Progressive disclosure       | `BeforeAgent` |
| Tool offload + loop detect   | `AfterTool` |
| Checkpoint + Ralph Loop      | `AfterAgent` |

Compaction events (PreCompact / PostCompact) are not surfaced by
Gemini CLI; the snapshot primitive degrades gracefully.

## Surface Pointers (Gemini)

| What | Where |
|------|-------|
| Skills | `.gemini/skills/ai-<name>/SKILL.md` |
| Agents | `.gemini/agents/ai-<name>.md` |
| Hook scripts | `.ai-engineering/scripts/hooks/` (shared) |
| CLI | `ai-eng <command>` |
<!-- ide-extras:end -->
