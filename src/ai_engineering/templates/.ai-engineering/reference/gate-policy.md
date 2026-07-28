# Gate policy: local fast-slice + CI authoritative (spec-104 D-104-02)

## Purpose

`/ai-commit` and `/ai-pr` must feel fast without weakening any gate. Pre-spec-104,
the local pre-push ran six checks serially plus a duplicate of the CI matrix
(`semgrep` + `pip-audit` + full `pytest` + `ty`) for a 3-5 min cold-cache wall clock.
spec-104 splits that into two layers:

- **Local fast-slice** — a curated set protecting minimum integrity within a ~60 s warm-cache budget.
- **CI authoritative** — the full check matrix, run before merge with auto-complete blocked until green. CI is the shift-left of production, not a redundant repeat of the local layer.

This document is the single source of truth for *which* checks live where and *why*.
`/ai-start` reads it at session start so every IDE driver (Claude Code, GitHub Copilot,
Codex, Antigravity) sees the same policy.

## Local fast-slice (~60 s budget)

`ai-eng gate run --cache-aware` runs these five checks (Wave 1 fixers serial, Wave 2
checkers parallel). Each has a budget contract the orchestrator measures and surfaces in
`wall_clock_ms` on `gate-findings.json`.

| Check | Wave | Budget (warm) | Budget (cold) | Cache-aware |
|---|---|---|---|---|
| `gitleaks protect --staged` | 2 | 1 s | 3 s | yes |
| `ruff format` + `ruff check --fix` | 1 | 2 s | 6 s | yes |
| `ty check src/` | 2 | 5 s | 15 s | yes |
| `pytest -m smoke` | 2 | 8 s | 25 s | yes |
| `ai-eng validate` | 2 | 2 s | 5 s | yes (skipped if `.ai-engineering/` unchanged) |
| docs gate (LLM dispatch) | 2 | 10 s | 30 s | no (non-deterministic) |

Cold-cache budgets sum to ~84 s, but Wave 2 runs in parallel so realised wall-clock is
`max(individual)` ~30-40 s plus Wave 1 ~6 s ≈ ~40-50 s. The 60 s budget covers git
overhead and orchestrator bookkeeping.

## CI authoritative

CI runs the local five plus three checks that intentionally do not run locally:

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

CI is the shift-left of production: `auto_merge` stays blocked until every CI check passes.
The `/ai-pr` watch loop autofixes residual CI failures (existing mechanism, unchanged). No
gate is weakened — only the *moment* moves from `git push` to `git push + 90 s of CI`.

## Why this is not configurable

The split is fixed at the framework level. No `manifest.yml` knob adds `semgrep` to the
local fast-slice or removes `pytest -m smoke`. Reasons:

- **LESSONS rule**: "stable framework orchestration should not become per-project config by default." Each per-project switch is a drift surface where one project's policy diverges from the framework contract.
- **Mirror drift**: Claude Code, GitHub Copilot, Codex, and Antigravity all consume the same `.claude/`, `.github/`, `.codex/`, `.agents/` skill mirrors. A configurable policy would be re-read per IDE driver, multiplying the surface for skew.
- **Audit traceability**: regulated consumers (banking, healthcare) need a single policy artefact auditors can read in five minutes. A per-project knob means per-project audit.

A team that legitimately needs a different cut forks this context file and overrides via
`contexts.precedence: [team, frameworks, languages]` in `manifest.yml` — visible, versioned,
and reviewable. A knob is not.

## Error-handling posture (fail-open vs fail-closed)

Every check, hook, and plumbing path chooses one of two things when it cannot complete:
**fail closed** (block) or **fail open** (log and continue). The choice is fixed by
*blast radius if the path is wrong or absent*, not taste:

- **Security / integrity boundaries fail CLOSED.** Secret scanning (the `gitleaks` /
  `semgrep` / `pip-audit` gates, BLOCK at MEDIUM and above), hook-integrity verification
  (`AIENG_HOOK_INTEGRITY_MODE`, default `enforce`), and the MCP health gate
  (`AIE_MCP_HEALTH_FAIL_OPEN` defaults closed) all BLOCK when they cannot run. A scanner
  that cannot execute is **not** a pass — an un-checkable secret is a leaked secret, and
  unverified hook bytes are untrusted code.
- **Framework plumbing fails OPEN, and must LOG.** Lifecycle sidecars
  (`spec_lifecycle.py`), `/ai-board` sync, telemetry, advisory hooks, version checks,
  doctor probes, and instinct extraction log the failure and continue. A `/ai-brainstorm`
  session must never die because a JSON sidecar is locked.
- **Never silently swallow.** A fail-open path that catches broadly *without logging* is
  the actual anti-pattern — not the broad `except` itself. The log line is what turns a
  swallowed error into an observable one.
- **A security gate that cannot run is a fail-open hole — a bug, not a design.**
  `docs/ci-branch-protection.md` and `docs/supply-chain-control-matrix.md` spell this out:
  a required gate the aggregate never inspects silently regresses the whole policy. Treat
  any fail-open on a security boundary as a defect.

A path that *hardens* an otherwise-open default to closed exposes a tunable
(`AIENG_IOC_FAIL_CLOSED` makes the IOC denylist fail closed on a missing or corrupt
`iocs.json`, default off); the baseline posture still follows the blast-radius rule above.

**Mechanical backing, not a blanket lint.** `ruff` `TRY004` (raise the correct exception
type) and `TRY400` (`logging.exception` preserves the traceback) back the "log, don't
swallow" half. `BLE001` (blind-except) is deliberately **not** enabled: it would force
suppression on the intentional fail-open plumbing layer, which the no-suppression hard rule
forbids. Audited deviations are recorded inline with `# audit:exempt:<reason>` markers
(e.g. `audit:exempt:typer-cli-3-fail-closed-gates-...`); this section is the doctrine those
fail-closed-gate justifications point at.

## Surface support tiers (spec-201 D-201-03)

`manifest.yml` enables six surfaces with no stated difference between them, which invites
an inference of parity only Claude Code earns. Two tiers, declared:

- **GUARDED** — content mirrors PLUS an enforced hook plane that can deny a tool call:
  `claude-code`, `codex`, `cursor`, `github-copilot` (**best-effort**), and `opencode`
  (**best-effort**).
- **CONTENT-ONLY** — skills, agents and instruction mirrors, **no enforcement**:
  `antigravity`. Nothing on that surface blocks a `--no-verify`, and no hook scans fetched
  content.

| Surface | Tier | Hook config | Enforcement proof |
|---|---|---|---|
| `claude-code` | GUARDED | `.claude/settings.json` | Hook bytes sha-pinned in `hooks-manifest.json`, `AIENG_HOOK_INTEGRITY_MODE=enforce` by default. |
| `codex` | GUARDED | `.codex/hooks.json` | `tests/integration/test_codex_guard_wiring.py` replays the config's own command string: `git commit --no-verify` returns exit 2 with a `decision: block` body. |
| `cursor` | GUARDED | `.cursor/hooks.json` | `tests/integration/test_cursor_guard_wiring.py` replays the config's own command string: the bridge emits `{"permission":"deny", …}`, Cursor's documented deny envelope. |
| `github-copilot` | GUARDED (**best-effort**) | `.github/hooks/hooks.json` | `tests/architecture/test_surface_support_tiers.py` runs `copilot-deny.sh`: `git commit --no-verify` yields `{"permissionDecision":"deny", …}`. `copilot-injection-guard.sh` delegates to `prompt-injection-guard.py` preserving exit 2. |
| `opencode` | GUARDED (**best-effort**) | `.opencode/plugin/ai-engineering.ts` | `tests/integration/hooks/test_opencode_plugin_guard.py` loads the real plugin in a JS runtime: `tool.execute.before` throws and `permission.ask` sets `status:"deny"`. |
| `antigravity` | CONTENT-ONLY | — | No deny plane. |

**Why Copilot is best-effort.** `copilot-deny.sh` opens with `trap 'exit 0' ERR` and exits 0
when `jq` is absent, so a host without `jq` silently allows everything the deny-list covers.
The delegating `copilot-injection-guard.sh` does preserve exit 2, so the injection lane is
hard; the deny-list lane is advisory in practice.

**Why OpenCode is best-effort, stated plainly rather than implied.** Claude Code hook bytes
are sha-pinned and integrity-enforced with a hard failure on mismatch. The OpenCode plugin
loads **unsigned**: `regenerate-hooks-manifest.py`'s `INCLUDE_SUFFIXES` is `{".py",".sh",
".ps1"}`, `.ts` is absent, and adding it would pin bytes nothing verifies — OpenCode loads
the plugin in its own JS runtime and nothing on that path reads `hooks-manifest.json`. The
signing half stays open on purpose; claiming equivalence without an integrity story for the
plugin would be an overclaim on a security boundary.

### Residual gaps this spec does NOT close

Named in words, because a security posture left implicit is the failure mode this work
exists to correct.

- **OpenCode plugins load unsigned** (above). A tampered `.opencode/plugin/*.ts` or
  `opencode-hook-bridge.ts` is detected by nothing at load time.
- **OpenCode plugin-load failures are silent-ish.** The 1.18.5 loader logs
  `Failed to load plugin …` and continues; a broken plugin degrades to no enforcement
  rather than refusing to start the session.
- **Event coverage is partial, deliberately.** Codex 0.145.0 exposes 7 hook events and
  `.codex/hooks.json` wires 5 (`SessionStart` is empty). OpenCode registers 3 of its hook
  surfaces. Cursor exposes 21 steps and `.cursor/hooks.json` registers 2. Widening event
  coverage is not in spec-201's goals.
- **Cursor registers only the two steps that have no Claude projection.** Cursor also loads
  `<workspace>/.claude/settings.json` natively and projects Claude's events onto its own
  `stop` / `sessionStart` / `sessionEnd` / `beforeSubmitPrompt` / `preCompact` /
  `preToolUse` / `postToolUse` / `subagentStop`; its dedupe keys on the literal command
  string, so registering those steps in `.cursor/hooks.json` would double-fire them rather
  than add coverage. A Cursor consumer WITHOUT a `.claude/settings.json` therefore gets the
  two guard lanes only.
- **Codex `matcher: ""` delivery on `PostToolUse` is operator-verified, not CI-gated.**
  Codex ships no hook-listing verb and a live `codex exec` needs auth plus network, so the
  gate proves the guard fires when the event is delivered; that Codex delivers `PostToolUse`
  for non-shell tools (`web_search`) is an operator acceptance item.
- **Codex needs a one-time re-trust for the new PostToolUse entry.** Codex trusts hook
  entries by position — `<event>:<group>:<index>` — so an upgrade that reorders groups
  silently invalidates every existing trust entry and the plane comes up inert with no
  warning. `no-verify-guard` is therefore APPENDED to the existing `PreToolUse` group
  (`pretooluse:0:3`), leaving `0:0`–`0:2` and their trust entries exactly where they were.
  The read-side guard at `posttooluse:1:0` (`injection-read-guard`) is genuinely new and has
  no trust entry: an upgrading operator must approve it once, at the first `PostToolUse`
  prompt, or that lane stays inert. Nothing in `.codex/hooks.json` may be re-ordered or
  inserted before an existing entry without paying this cost again.
- **`cursor-hook-bridge.py`'s sha pin is stale until the terminal manifest regen.** Its
  bytes changed in this spec. This does **not** open the Cursor plane: the bridge does not
  run under `run_hook_safe`, and the guards it spawns (`no-verify-guard.py`,
  `prompt-injection-guard.py`) are unchanged, so their pins hold and the deny was verified
  under `AIENG_HOOK_INTEGRITY_MODE=enforce`.

## Watch loop and CI autofix

When CI fails after `git push`, `/ai-pr` step 14 enters its watch loop:

1. Polls `gh pr checks` every 30 s (active phase) or 5 min (passive phase).
2. On a fixable failure, runs the matching auto-fix from `gate-findings.json` (e.g.,
   `ruff check --fix`, `ruff format`).
3. Re-pushes and waits for the next CI cycle.
4. Bounded by D-104-05: 30 min active-phase cap, 4 h passive-phase cap, exit 90 if either fires.

The active cap is "30 min since last fix action" — not "30 min total" — so a long CI run
making steady progress is not truncated.

## Risk acceptance for delegated checks

When the watch loop hits its cap with residual failures, it emits
`.ai-engineering/state/watch-residuals.json`, schema-identical to `gate-findings.json`
(D-104-06): `{schema, session_id, produced_by: "watch-loop", findings, ...}`.

`ai-eng risk accept-all <findings.json> --justification "..." --spec <spec-id> --follow-up "..."`
(spec-105 D-105-05) consumes this artefact, persists each finding's `rule_id` to
`state/decision-store.json` as a discrete `DEC-*` entry sharing one `batch_id`, and unblocks
the merge. Justification, spec ref, and follow-up plan are mandatory and surface in audit
reports.

### Lookup flow (orchestrator-level, D-105-07)

After Wave 2 collects findings, the orchestrator calls
`ai_engineering.policy.checks._accept_lookup.apply_risk_acceptances(findings, store, now=now)`,
which:

1. Builds canonical contexts `f"finding:{rule_id}"` for each live finding.
2. Looks each up in `state/decision-store.json` for an active (non-expired, non-revoked)
   risk-acceptance DEC entry.
3. Partitions findings into `(blocking, accepted)`. Accepted findings drop from the blocking
   set, surface separately under `accepted_findings[]` in `gate-findings.json` v1.1, and
   emit a `category=risk-acceptance, control=finding-bypassed` telemetry event each.

The CLI prints a compact ACCEPTED table per bypass plus an `expiring_soon[]` banner when any
DEC is within `_WARN_BEFORE_EXPIRY_DAYS` (default 7) of expiry.

### Bulk acceptance (D-105-01)

`accept-all` accepts findings of any severity (including critical) in one pass. Per-finding
TTLs follow `_SEVERITY_EXPIRY_DAYS` (critical=15d, high=30d, medium=60d, low=90d). Each
acceptance persists its severity unchanged — bulk acceptance is logged-acceptance, not
severity weakening.

### Dual-mode interaction (D-105-02 / D-105-03)

- **Regulated mode** (default): all gates run. Risk acceptances apply through
  `apply_risk_acceptances`; granted bypasses emit telemetry.
- **Prototyping mode**: Tier 2 governance checks skip; Tier 0+1 always block. Risk
  acceptances still apply for any finding that does run. Branch-aware escalation + CI
  override force regulated execution regardless of manifest, so prototyping cannot leak to
  protected branches or CI runs.

See `.ai-engineering/contexts/risk-acceptance-flow.md` for the full end-to-end lifecycle
(accept / renew / resolve / revoke).

## Migration note

`AIENG_LEGACY_PIPELINE=1` restores the pre-spec-104 sequential local-only behaviour for one
session — a known-good fallback if the orchestrator misbehaves while you file an issue. The
legacy path emits a deprecation warning and does not write `gate-findings.json` (no schema
contract).

## References

- `.ai-engineering/specs/spec.md` D-104-02 (this policy's source decision).
- `.ai-engineering/specs/spec.md` D-104-05 (watch loop wall-clock bounds).
- `.ai-engineering/specs/spec.md` D-104-06 (gate-findings.json schema v1).
- `CLAUDE.md` "Don't" rules #1-9 (never-weaken-gates, never `--no-verify`, never bypass CI).
- `.ai-engineering/manifest.yml` `quality:` block (coverage, duplication, cyclomatic, cognitive thresholds enforced by both layers).
- `.ai-engineering/contexts/python-env-modes.md` (spec-101 D-101-12 worktree contract that gate-cache storage respects).
