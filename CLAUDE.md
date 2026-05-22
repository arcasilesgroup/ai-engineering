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
`/ai-brainstorm` first when a task has no spec.

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

## Skills (53)

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
| Skills (53) | `.claude/skills/ai-<name>/SKILL.md` |
| Agents (9) | `.claude/agents/ai-<name>.md` |
| Placement contract | `.ai-engineering/reference/knowledge-placement.md` |
| Hook scripts | `.ai-engineering/scripts/hooks/` |
| CLI | `ai-eng <command>` |
| Audit chain | `.ai-engineering/state/framework-events.ndjson` |
| Decisions | `.ai-engineering/state/decision-store.json` |
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

<!-- ide-extras:start -->
## Hot-Path Discipline (Claude Code)

Claude Code triggers pre-commit and pre-push hooks on every save and
commit, so the deterministic gate must finish fast:

- **Pre-commit budget**: under 1 second wall-clock (lint, format check,
  secret scan on staged hunks only).
- **Pre-push budget**: under 5 seconds for residual checks before the
  push pipeline takes over.
- **Heavier work belongs in CI**: full test suite, dependency audit, and
  governance evaluation never run on the local hot path.

If a check exceeds budget, profile it and move work off the hot path
before adding new logic to the hook.

## Hooks Configuration (Claude Code)

Claude Code reads hook wiring from `.claude/settings.json`. The project
registers **11 canonical hook events** (audited in spec-122-d D-122-27,
CI-guarded by `tests/unit/hooks/test_canonical_events_count.py`):
`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`,
`Stop`, `PreCompact`, `PostCompact`, `SessionStart`, `SubagentStop`,
`Notification`, `SessionEnd`.

Hook scripts live under `.ai-engineering/scripts/hooks/` (canonical).
`.claude/hooks/` is a read-only symlink to that directory. Hook bytes
are pinned in `.ai-engineering/state/hooks-manifest.json` (sha256 per
script); `run_hook_safe` enforces integrity per
`AIENG_HOOK_INTEGRITY_MODE` (default `enforce`).

## Runtime Layer Tunables

```
# Established
AIENG_TOOL_OFFLOAD_BYTES         # default 16384
AIENG_LOOP_WINDOW                # default 6
AIENG_RALPH_MAX_RETRIES          # default 5
AIENG_RALPH_BLOCK                # default 0 (observe-only)
AIENG_HOOK_INTEGRITY_MODE        # default enforce

# spec-139 M1 — concurrency budget primitive
AIENG_MAX_WAVE_AGENTS            # default auto (floor=2, ceiling=6)
AIENG_MAX_QUALITY_AGENTS         # default 3 (Phase 5 assessor cap)
AIENG_MAX_THREAD_WORKERS         # default 4 (orchestrator ThreadPoolExecutor cap)

# spec-139 M5 — hook hot-path cache/debounce controls
AIENG_HOOK_CACHE_TTL_SEC            # default 300 (IOC/decision cache TTL seconds)
AIENG_AUTOFORMAT_DEBOUNCE_SEC       # default 1.0 (per-file formatter debounce seconds)

# spec-139 M6 — SessionEnd rotation controls
AIENG_RUNTIME_ROTATE_THROTTLE_SEC   # default 3600 (1 hour throttle)
AIENG_NDJSON_MAX_LINES              # default 100000 (rotation signal line cap)
AIENG_NDJSON_MAX_BYTES              # default 52428800 (rotation signal byte cap; 50 MiB)

# spec-147 G2 — escape-hatch toggles + overrides (behavior-changing; unset = the safe/standard path)
AIENG_RALPH_DISABLED                # set "1" to disable the Ralph Stop-loop guard
AIENG_RISK_ACCUMULATOR_DISABLED     # set "1" to disable the risk accumulator
AIENG_INSTINCT_BATCH_DISABLED       # set "1" to disable instinct batch extraction
AIENG_TELEMETRY_DEBUG               # set "1" to enable verbose telemetry logging
AIENG_HOOK_ENGINE                   # override the detected IDE engine (unset -> claude_code)
AIENG_HOOK_ENGINE_DEFAULT           # fallback engine label when none is detected (unset -> unknown)
AIENG_EVENT_SIDECAR_BYTES           # 3072 bytes; event sidecar threshold
AIE_MCP_HEALTH_FAIL_OPEN            # "1" pass-through MCP health gate; SECURITY RISK

# spec notebooklm-async-tier3 — /ai-research Tier 3 deep-research harvest
AIENG_RESEARCH_NLM_WAIT_SEC         # default 300 (ceiling 900; NotebookLM deep-research harvest)

# Reserved roadmap — not implemented
AIENG_HOST_PREFLIGHT_DISABLED       # reserved spec-139 M2
AIENG_HOST_PREFLIGHT_MIN_FREE_MB    # reserved spec-139 M2
AIENG_HOST_PREFLIGHT_MAX_PRESSURE_PCT  # reserved spec-139 M2
AIENG_HOOK_BUDGET_PROFILE           # reserved spec-139 M5
```

State lives under `.ai-engineering/runtime/` (gitignored — session
state, not source of truth).

## Token Efficiency

- Use `/clear` aggressively when context is no longer load-bearing.
- Dispatch `ai-explore` for deep codebase research (read-only, fresh
  context).
- Cite files with `startLine:endLine:filepath`; never paste large code
  blocks the user did not ask for.

## Optional: Engram (third-party memory)

`ai-engineering` ships without a built-in memory layer. Engram is a
peer product maintained by `Gentleman-Programming/engram`; install it
separately if you want cross-session memory (spec-132 D-132-06; the
installer no longer wires Engram automatically).

Install:

```bash
# macOS
brew install engram
# Linux
ENGRAM_URL="https://github.com/Gentleman-Programming/engram/releases/latest"
curl -fsSL "$ENGRAM_URL/download/engram-linux-x86_64" -o "$HOME/.local/bin/engram"
chmod +x "$HOME/.local/bin/engram"
# Windows
winget install Engram
```

Then run the IDE-specific setup once per project (use the entry that
matches your IDE):

```bash
engram setup claude_code   # Claude Code
engram setup codex          # OpenAI Codex
```

GitHub Copilot is not currently supported by Engram. Verify the
integration with `ai-eng doctor`.

## Audit Observability (files-only)

```bash
ai-eng audit verify                            # verify the framework-events.ndjson hash chain
ai-eng audit tokens --by skill|agent|session   # token rollup over the NDJSON
ai-eng audit replay --session <id>             # depth-first span-tree walk over the NDJSON
```
<!-- ide-extras:end -->
