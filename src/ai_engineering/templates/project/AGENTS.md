# Canonical Cross-IDE Rulebook

> Hard rules live in [CONSTITUTION.md](CONSTITUTION.md). This file is
> the canonical multi-IDE entry point for "how AI works in this repo".
> Every IDE-native mirror (AGENTS.md, CLAUDE.md,
> .github/copilot-instructions.md) carries identical canonical payload;
> IDE-specific extras live in the fenced block at the bottom.

## 0. Bootstrap

Every session: (1) read [CONSTITUTION.md](CONSTITUTION.md) (project
identity); (2) read `.ai-engineering/manifest.yml` (config SoT);
(3) consult [docs/persistence-doctrine.md](docs/persistence-doctrine.md)
for the canonical store of each datum (decisions live in spec markdown;
the `decision-store.json` cache is populated after `ai-eng decision
backfill` or `/ai-brainstorm` approval per spec-138 M3 follow-up);
(4) no implementation without an approved spec — invoke
`/ai-brainstorm` first when a task has no spec; (5) read
[SOUL.md](SOUL.md) (the agent's collaborator values — the judgment
layer above the deterministic plane).

See [docs/persistence-doctrine.md](docs/persistence-doctrine.md) for
the three-tier files-only model (NDJSON audit, JSON/YAML
records+config, Markdown) and the SSOT-PD rebuild semantics.

## Operating Mindset (§1–§9 condensed)

Karpathy / Boris one-liners that frame the §10 principles. Full prose
in [.ai-engineering/reference/principles.md](.ai-engineering/reference/principles.md) under "Operating Mindset".

1. **Think Before Coding** — read failing input + spec gates BEFORE editing.
2. **Simplicity First** — fewest moving parts; prefer deletion over abstraction.
3. **Surgical Changes** — one commit, one change; drive-by refactors get their own justification.
4. **Goal-Driven Execution** (Verification Before Done) — green gate before "done"; staff-engineer bar.
5. **Plan-Mode Default** — enter plan mode for non-trivial tasks; re-plan when things go sideways.
6. **Subagent Strategy** — one task per subagent; offload research into fresh context windows.
7. **Self-Improvement Loop** — every user correction updates `.ai-engineering/LESSONS.md`.
8. **Demand Elegance** — "is there a more elegant way?" on non-trivial changes; clear beats clever.
9. **Autonomous Bug Fixing** — fix bugs you spot; mention them in the commit.

## Soul

The agent's collaborator values — Pragmatic Helpfulness, Honest &
Direct, Collaborative Partner, Learn & Grow — live in
[SOUL.md](SOUL.md). They are the judgment layer above the deterministic
plane (gates, Prohibitions), read each session per §0. SOUL.md owns the
*values framing*; the Operating Mindset (§1-9) and §10 principles own
the engineering prose.

## 10. Engineering Principles (pointer)

The eight first-class principles (§10.1 KISS, §10.2 YAGNI, §10.3 SOLID,
§10.4 DRY, §10.5 TDD, §10.6 SDD, §10.7 Clean Code, §10.8 Hexagonal
Architecture) live in [.ai-engineering/reference/principles.md](.ai-engineering/reference/principles.md). Every
SKILL.md `## Workflow` cites at least one §10.x anchor; anchors are
stable at the new home.

## 11. Canonical Chain

The active spec workflow is:

**(/ai-spec-draft) → /ai-brainstorm → /ai-plan → /ai-build → /ai-pr**

- `/ai-spec-draft` is the OPTIONAL pre-step: it produces a researched
  problem brief at `.ai-engineering/specs/drafts/<topic>-brief.md` to hand
  off to `/ai-brainstorm`. Skip it when the problem is already well-scoped.
- `/ai-brainstorm` produces an approved spec at
  `.ai-engineering/specs/spec.md`.
- `/ai-plan` produces an exhaustive patch-ready plan at
  `.ai-engineering/specs/plan.md` and records the recommended executor
  route (`/ai-build` or `/ai-autopilot`).
- `/ai-build` executes plans routed to build (multi-stack implementation
  gateway, D-127-11). For specs with ≥3 concerns or ≥10 file changes,
  `/ai-autopilot` wraps the chain.
- `/ai-pr` runs the final quality loop (verify + review + commit
  pipeline internally) and opens the PR.

`/ai-commit` is preserved as a standalone off-chain skill for WIP
checkpoints. It does NOT appear in the canonical chain (D-131-07).

## 12. Surface Index

## Skills (54)

Canonical skills and agents live under `.claude/`; mirror surfaces under
`.codex/`, `.agents/`, and `.github/` are byte-equivalent regenerations
written by `scripts/sync_mirrors/core.py`. Invoke a skill via
`/ai-<name>` in the IDE agent surface — never via a synthetic terminal
equivalent.

## Agents (9)

The 9 user-facing agents are defined at
`.claude/agents/ai-<name>.md` — that directory is the source of truth
(there is no `agents.registry` manifest key). `.claude/agents/` also
holds the internal review and verifier families (`review-*`,
`reviewer-*`, `verifier-*`) dispatched by `/ai-review` and `/ai-verify`;
those are not part of the user-facing 9. Each agent runs in
its own context window — offload research and parallel analysis to them.

## Source of Truth

| Surface | Where |
|---------|-------|
| Skills (54) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (9) | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/reference/knowledge-placement.md` |
| Hook scripts | `.ai-engineering/scripts/hooks/` |
| CLI | `ai-eng <command>` |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Decisions | `.ai-engineering/state/decision-store.json` |
| Config | `.ai-engineering/manifest.yml` |
| Constitution | [CONSTITUTION.md](CONSTITUTION.md) |
| Architecture / solution intent | [.ai-engineering/solution-intent.md](.ai-engineering/solution-intent.md) (§3.1 layered module map) |

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
5. **Bounded fail-loud quality loop.** `/ai-build` and
   `/ai-autopilot` Phase 5 may spend ONE finding-scoped remediation
   pass on blocker/critical/high quality-loop findings, then run a
   terminal final reassessment. Remaining blocker/critical/high
   findings STOP and escalate — no second remediation pass. `/ai-pr`
   keeps its final quality gate fail-loud.
6. **Conventional Commits.** `<type>(<scope>): <subject>` imperative
   mood. Body explains "why", not "what". Never `--no-verify`.
7. **Single Source of Truth Per Datum.** Every datum has exactly one
   canonical writable store. Derived caches are explicitly labelled
   (named, with a rebuild command) and rebuildable on demand. See
   [docs/persistence-doctrine.md](docs/persistence-doctrine.md) for
   the three-tier files-only model and the rebuild semantics.

## 14–16. Pointer rows

The bulk of the canonical-payload prose lives in `.ai-engineering/reference/` so the
mirrors stay lean (spec-134 sub-005 mirror diet). Authoritative homes:

- **§10 Engineering Principles** → [.ai-engineering/reference/principles.md](.ai-engineering/reference/principles.md)
  (§10.1 KISS through §10.8 Hexagonal Architecture; the 34 skill /
  agent files that cite `§10.x` resolve here).
- **§14 Strict Content Contracts** + **§15 IDE-Extras Escape Hatch** →
  [.ai-engineering/reference/mirror-authoring.md](.ai-engineering/reference/mirror-authoring.md) (per-file
  authoring table + the `<!-- ide-extras:start -->` fence contract).
- **§16 Surface Axioms** (A1 / A2) →
  [.ai-engineering/reference/surface-axioms.md](.ai-engineering/reference/surface-axioms.md) (Surface Axiom and
  No-Twin Axiom; D-133-04 enforcement at `test_surface_parity.py`).
- **Error-handling posture** (fail-open vs fail-closed) →
  [.ai-engineering/reference/gate-policy.md](.ai-engineering/reference/gate-policy.md)
  (security/integrity boundaries fail closed; plumbing fails open and must log).

<!-- ide-extras:start -->
<!-- ide-extras:end -->
