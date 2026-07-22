---
spec: spec-192
slug: telemetry-followup
title: "Telemetry deck follow-up — 5 deferred gaps"
status: in-progress
date: 2026-07-22
concerns: 5
route: /ai-build
---

# spec-192 — Telemetry deck follow-up

## Summary

Five surgical fixes deferred from the telemetry deck analysis (19 jul 2026).
All are low-to-medium effort with high signal-to-noise ratio. No new subsystems —
each item touches 1–3 files and has a clear acceptance criterion.

## Goals

1. **Cut 65% of hook cost** — remove instinct-observe from PreToolUse (keep PostToolUse only).
2. **Close the 48% verify gap** — ai-build auto-dispatches ai-verify; ai-pr gates on prior verify.
3. **Eliminate wasted retries** — run `ruff --fix` before ralph consumes retries on lint findings.
4. **Reduce false-positive blocks** — risk accumulator per-command score floor + faster decay.
5. **Eliminate integrity drift at source** — auto re-pin manifest sha on update/install/dev-sync.

## Non-Goals

- Skill consolidation (#12 from deck) — separate spec.
- Dead install cleanup (#14) — operational, no spec needed.
- Background runtime-stop / async auto-format (#15) — lower ROI, deferred.
- Read-side injection coverage (#13) — shipped in spec-191.
- Intent router for no_ai_prefix (#6) — medium effort, separate spec.

## Decisions

### D-192-01: instinct-observe PostToolUse-only

**Rationale:** The hook is registered in both PreToolUse and PostToolUse, causing
2× executions per tool call (82,617 total, 65% of all hook wall-clock). Its output
(instincts) is only consumed at session-start, not mid-turn. PostToolUse captures
the same tool_response data. Removing PreToolUse registration halves the cost with
zero behavioral change.

**Change:** Remove the PreToolUse entry from `.claude/settings.json` (and the
template mirror). Keep the PostToolUse entry. Update hooks-manifest.

### D-192-02: mandatory verify — dual gate

**Rationale:** 48% of builds ship without verify/review. Two complementary gates:

1. **ai-build auto-dispatch:** At the end of a successful build phase, ai-build
   dispatches ai-verify automatically (like ai-autopilot already does). This covers
   the manual `ai-build` path.
2. **ai-pr gate:** ai-pr checks for a verify outcome in the current session or
   branch. If none found, it runs ai-verify inline before proceeding. This is the
   safety net for edge cases where ai-build's dispatch was skipped or failed.

**Change:** Edit ai-build and ai-pr skill definitions. ai-build: add verify
dispatch in post-build step. ai-pr: add verify-absent check in pre-flight.

### D-192-03: ruff --fix before ralph retries

**Rationale:** 31 ralph stops were caused by auto-fixable lint findings (E501,
UP017). The ralph loop retries the same code 5 times then gives up. Running
`ruff check --fix` once before the first retry resolves these mechanically.

**Change:** In the ralph convergence loop, after a lint-related finding, run
`ruff check --quiet --fix .` on the changed files before the next retry. Only
for lint findings (ruff exit codes), not for test failures or other errors.

### D-192-04: risk accumulator per-command floor + decay acceleration

**Rationale:** The risk accumulator uses session-scoped cumulative scoring with
0.95/minute decay. Benign IOC matches (CSS classes, PyPI curl, env var names)
accumulate across a session and can reach block/force_stop thresholds. The
allowlist from spec-191 helps but doesn't cover all benign patterns.

**Change:**
- Add a per-command score floor: if the last N commands had 0 findings, decay
  the score by an additional 50% (floor at 0).
- Increase base decay from 0.95 to 0.90/min (halves in ~6.6 min instead of
  ~13.5 min).
- Scope IOC patterns: require env-var patterns to match exfiltration forms
  (`curl`, `wget`, `requests.post`, `base64`, pipe-to-shell) rather than bare
  `os.environ` or `process.env`.

### D-192-05: auto re-pin manifest on update/install/dev-sync

**Rationale:** 15,368 integrity violations (80.5% of all errors) come from
stale manifest sha256 hashes. The coalescer from spec-190 deduplicates the noise
but doesn't fix the root cause. Auto re-pinning eliminates the drift entirely.

**Change:** In `ai-eng update`, `ai-eng install` finalize, and `ai-eng dev sync`,
after writing hook files, regenerate the manifest (sha256 per hook). This is
already the behavior of `regenerate-hooks-manifest.py` — wire it into the
finalize step of each entry point. Add a `--no-repin` flag for explicit override.

## Risks

- **D-192-01:** If any hook logic depends on PreToolUse instinct data mid-turn,
  removing it could break. Evidence: 129 session-starts show instincts only from
  ai-engineering (the dogfood repo), and the hook writes to a file read at
  session-start, not mid-turn. Low risk.
- **D-192-02:** Auto-dispatch adds ~1 agent spawn to every build. ai-autopilot
  already does this successfully. Cost is one extra context window per build.
- **D-192-03:** `ruff --fix` modifies files in-place. On a dirty working tree this
  could interact with concurrent edits. Mitigation: only fix files that ruff
  already flagged (not a full-project fix).
- **D-192-04:** Faster decay means real findings lose weight sooner. The per-command
  floor partially compensates. Monitor false-negative rate post-ship.
- **D-192-05:** Auto re-pin in dev-sync could mask intentional hook edits during
  development. The `--no-repin` flag provides an escape hatch.

## References

- Telemetry deck: `~/Downloads/ai-engineering · Telemetría del framework.html`
  (19 jul 2026, 234k events, 18 repos, 16 recommendations)
- spec-190: observability integrity — attributable, deduplicated, fail-loud telemetry
- spec-191: injection guard read-side coverage + allowlist wiring
- Risk accumulator: `.ai-engineering/scripts/hooks/_lib/risk_accumulator.py`
- Convergence loop: `.ai-engineering/scripts/hooks/_lib/convergence.py`
