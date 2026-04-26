# Gate policy: local fast-slice + CI authoritative (spec-104 D-104-02)

## Purpose

`/ai-commit` and `/ai-pr` need to feel fast without weakening any gate. Pre-spec-104,
the local pre-push block ran six checks sequentially plus a duplicate of the CI matrix
(`semgrep` + `pip-audit` + `pytest` full + `ty` again) for a 3-5 min cold-cache wall
clock. spec-104 splits that work into two layers:

- **Local fast-slice** -- a curated set of checks that protect minimum integrity and
  fit within a ~60 s budget on warm cache.
- **CI authoritative** -- the full check matrix, run before merge with auto-complete
  blocked until green. CI is the shift-left of production, not a redundant repeat of
  the local layer.

This document is the single source of truth for *which* checks live where and *why*.
It is read at session start by `/ai-start` so every IDE driver (Claude Code, GitHub
Copilot, Codex, Gemini) sees the same policy.

## Local fast-slice (~60 s budget)

The `ai-eng gate run --cache-aware` orchestrator runs these five checks (Wave 1
fixers serial, Wave 2 checkers parallel). Each check has a budget contract: a soft
target the orchestrator measures against and surfaces in `wall_clock_ms` on
`gate-findings.json`.

| Check | Wave | Budget (warm) | Budget (cold) | Cache-aware |
|---|---|---|---|---|
| `gitleaks protect --staged` | 2 | 1 s | 3 s | yes |
| `ruff format` + `ruff check --fix` | 1 | 2 s | 6 s | yes |
| `ty check src/` | 2 | 5 s | 15 s | yes |
| `pytest -m smoke` | 2 | 8 s | 25 s | yes |
| `ai-eng validate` | 2 | 2 s | 5 s | yes (skipped if `.ai-engineering/` unchanged) |
| docs gate (LLM dispatch) | 2 | 10 s | 30 s | no (non-deterministic) |

Sum of cold-cache budgets is ~84 s, but Wave 2 runs in parallel so realised
wall-clock is `max(individual)` ~30-40 s plus Wave 1 ~6 s ~= ~40-50 s. The
60 s budget includes git overhead and orchestrator bookkeeping.

## CI authoritative

The CI workflow runs the local five plus three more checks that intentionally do not
run locally:

| Check | Local | CI | Why CI only |
|---|---|---|---|
| `gitleaks protect --staged` | yes | yes (full-source) | local is staged, CI is full-source |
| `ruff format` + `ruff check` | yes | yes (lint job) | parity guard |
| `ty check src/` | yes | yes (typecheck job) | parity guard |
| `pytest -m smoke` | yes | covered by full unit job | redundant on CI |
| `ai-eng validate` | yes | yes (content-integrity job) | parity guard |
| docs gate (LLM) | yes | no | non-deterministic; would flake CI |
| `semgrep` | no | yes (security job) | full-source needs holding 30+ s |
| `pip-audit` | no | yes (security job) | network access available on runner |
| `pytest` full + matrix | no | yes (test job, 3 OS x 3 Py) | matrix duplicates local cost |

CI is the shift-left of production: `auto_merge` stays blocked until every CI check
passes. The watch loop in `/ai-pr` autofixes residual CI failures (existing
mechanism, unchanged). No gate is weakened -- the gate still runs before merge,
only the *moment* moves from `git push` to `git push + 90 s of CI`.

## Why this is not configurable

The split is fixed at the framework level. There is no `manifest.yml` knob to add
`semgrep` to the local fast-slice or remove `pytest -m smoke`. Reasons:

- LESSONS rule: "stable framework orchestration should not become per-project
  config by default." Each per-project switch creates a drift surface where one
  project's policy diverges from the framework's contract.
- Mirror drift across IDEs. Claude Code, GitHub Copilot, Codex, and Gemini all
  consume the same `.claude/skills/`, `.github/skills/`, `.codex/skills/`,
  `.gemini/skills/` mirrors. A configurable policy would have to be re-read per
  IDE driver, multiplying the surface area for skew.
- Audit traceability. Regulated consumers (banking, healthcare) need a single
  policy artefact that auditors can read in five minutes. A per-project knob means
  per-project audit.

A team that legitimately needs a different cut may fork this context file and
override via the `contexts.precedence: [team, frameworks, languages]` ordering in
`manifest.yml`. The fork is visible, versioned, and reviewable -- a knob is not.

## Watch loop and CI autofix

When CI fails after `git push`, `/ai-pr` step 14 enters its watch loop. The loop:

1. Pulls `gh pr checks` every 30 s (active phase) or 5 min (passive phase).
2. On a fixable failure, runs the matching auto-fix command from
   `gate-findings.json` (e.g., `ruff check --fix`, `ruff format`).
3. Re-pushes and waits for the next CI cycle.
4. Bounded by D-104-05: 30 min wall-clock cap on the active phase, 4 h cap on
   the passive phase, exit 90 if either cap fires.

The active-phase cap is "30 min since last fix action" -- not "30 min total" -- so
a long CI run that is steadily making progress will not get truncated.

## Risk acceptance for delegated checks

When the watch loop hits its cap with residual failures, it emits
`.ai-engineering/state/watch-residuals.json`. The schema is identical to
`gate-findings.json` (D-104-06): `{schema, session_id, produced_by:
"watch-loop", findings, ...}`.

`ai-eng risk accept-all watch-residuals.json --justification "..."` (spec-105,
S3) consumes this artefact, persists each finding's `rule_id` to
`state/decision-store.json` with the justification, and unblocks the merge. The
justification is mandatory and surfaces in audit reports.

Until spec-105 lands, the fallback printed by the watch loop on cap is "or fix
manually and re-invoke `/ai-pr`".

## Migration note

`AIENG_LEGACY_PIPELINE=1` env var restores the pre-spec-104 sequential local-only
behaviour for one session. Use it if the new orchestrator misbehaves and you need
a known-good fallback while filing an issue. The legacy path emits a deprecation
warning and does not write `gate-findings.json` (no schema contract).

## References

- `.ai-engineering/specs/spec.md` D-104-02 (this policy's source decision).
- `.ai-engineering/specs/spec.md` D-104-05 (watch loop wall-clock bounds).
- `.ai-engineering/specs/spec.md` D-104-06 (gate-findings.json schema v1).
- `CLAUDE.md` "Don't" rules #1-9 (never-weaken-gates, never `--no-verify`,
  never bypass CI).
- `.ai-engineering/manifest.yml` `quality:` block (coverage, duplication,
  cyclomatic, cognitive thresholds enforced by both layers).
- `.ai-engineering/contexts/python-env-modes.md` (spec-101 D-101-12 worktree
  contract that gate-cache storage respects).
