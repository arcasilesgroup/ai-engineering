---
execution_route:
  version: 1
  spec: spec-154
  executor: autopilot
  automation: hitl
  concern_count: 3
  estimated_files: 12
  reason: >-
    12 files across 3 IDE surfaces (Claude/Codex/Copilot) + integrity manifest
    + tests; meets the >=10-file autopilot threshold (CLAUDE.md §11). Security-
    sensitive (prompt-injection-guard dispatch, hook integrity) and Copilot-
    regression risk warrant wave decomposition + a final quality loop with HITL
    review at PR.
  safe_next_command: "/ai-autopilot"
status: draft
pipeline: full
spec: spec-154
title: Resolve a Python >=3.11 interpreter for hook dispatch
---

# Plan — spec-154: Resolve a Python >=3.11 interpreter for hook dispatch

## Design

`--skip-design` — pure infra/shell-dispatch change, no UI surface, no
user-visible artifact. Design routing is a no-op.

## Architecture

Pattern: **adapter at the dispatch boundary** (ad-hoc). One shared shell
resolver (`_lib/resolve-python.sh`) + one transparent per-IDE launcher
(`_lib/run-hook.sh`) that all hook commands route through. Existing
`copilot-runtime.sh` is refactored to *source* the shared resolver (DRY)
while keeping its public functions so the 15 `copilot-*.sh` wrappers are
untouched (D-154-02; preserves Copilot — AC5).

```
 IDE command string
   Claude:  bash run-hook.sh  "$CLAUDE_PROJECT_DIR/.../x.py"
   Codex:   AIENG_HOOK_ENGINE=codex bash run-hook.sh .ai-engineering/.../x.py
   Copilot: copilot-x.sh  ── sources ──▶ copilot-runtime.sh ─┐
                                                              │
   run-hook.sh ── sources ──▶ resolve-python.sh ◀────────────┘
                                   │
                                   ▼
              cache hit? runtime/resolved-python.txt (read builtin)
                                   │ miss
                                   ▼
        .venv/bin/python → .venv/Scripts/python.exe → uv run python
          → python3.13/3.12/3.11 (trusted by name) → python3 if >=3.11
                                   │ none
                                   ▼
              one actionable line to stderr; exit 0 (non-blocking)
                                   │ resolved
                                   ▼
                       exec "$PY" "$@"   (transparent — __file__ = the .py,
                                          so run_hook_safe integrity intact)
```

## Plan corrections to spec (from OQ resolution — wf_9d7837f1-555)

The exploration refined three spec assertions. These supersede the spec
where they conflict:

1. **Integrity blocking ≠ trustedArgvs** (corrects spec D-154-05 / R2 /
   AC3). `run_hook_safe` blocks only on hook **script-byte drift** in the
   manifest `hooks` (sha256) section — it never reads `trustedArgvs`
   (that subsystem only feeds the prompt-injection-guard bypass lane for
   `session_bootstrap` argvs). We are **not** editing any `.py`, so the
   `.py`-block risk is nil. The real integrity task: after creating new
   `_lib/*.sh` and editing `copilot-runtime.sh`, run
   `regenerate-hooks-manifest.py` so the new/changed `.sh` bytes enroll;
   the gate is `regenerate-hooks-manifest.py --check` exit 0 (CI). [OQ2]
2. **Parity guard is `test_canonical_events_count.py`, not
   `test_surface_parity.py`** (corrects spec AC4). `test_surface_parity`
   enforces the No-Twin Axiom (skill↔CLI), unrelated to hooks.
   `test_canonical_events_count.py::test_no_dead_wirings` scans
   `settings.json` command path patterns and WILL catch a renamed launcher
   path — that is the guard the wiring must satisfy. [FIX-SURFACE]
3. **Transparent launcher is mandatory** (sharpens spec D-154-01). The
   launcher must `exec "$PY" "$real_script.py" "$@"` — it must NOT pass
   itself as the hook script, or `__file__`-based integrity resolution
   breaks. [OQ1]

Plus two scope rulings:

4. **Codex confirmed broken → in scope** (spec OQ3 resolved): `.codex/
   hooks.json` uses identical bare `python3` (11 cmds). [OQ3, verdict
   CONFIRMED]
5. **Windows `.ps1` deferred** (spec OQ5 resolved as far as code allows):
   whether Claude/Codex dispatch via git-bash vs pwsh on Windows is a
   runtime fact not determinable from the repo. v1 ships the bash launcher
   (covers macOS/Linux + Windows-git-bash; `resolve-python.sh` carries the
   `.venv/Scripts/python.exe` probe). A parallel `run-hook.ps1` + the
   `copilot-runtime.ps1` >=3.11 gate are deferred to a Windows follow-up
   and recorded in Risks. [OQ5]

Simplification vs fix-surface draft: **no separate `run-codex-hook.sh`** —
Codex sets `AIENG_HOOK_ENGINE=codex` inline before the generic
`run-hook.sh` (DRY; drops 2 files, 13→12).

## Phases & tasks

### Phase 1 — Shared resolver core (TDD)

- [ ] T-1 — RED: resolver behavior test
  - Agent: build
  - Files: tests/unit/hooks/test_resolve_python_sh.py (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): — (judgment: author cases) prefers `.venv/bin/python`; trusts `python3.13/12/11` by name; gates bare `python3` on `>=3.11`; on none → one stderr line + exit 0; cache read/write to `runtime/resolved-python.txt`; stale-cache (path no longer `-x`) re-resolves.
  - Gate: test fails (script absent)

- [ ] T-2 — GREEN: create `_lib/resolve-python.sh`
  - Agent: build
  - Files: .ai-engineering/scripts/hooks/_lib/resolve-python.sh (new)
  - Principles applied: §10.2 YAGNI, §10.4 DRY, §10.8 Hexagonal (dispatch adapter)
  - Patch (deterministic): — implement `resolve_python "$project_root"` per OQ4 design (cache-read via `read -r` builtin; venv → `.venv/Scripts/python.exe` → `uv run python` → named `python3.13/12/11` → bare `python3` with `python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,11) else 1)'`; guard line + `exit 0`; atomic cache write via mktemp+mv). Must be `set -eu`-safe and stdlib-shell only.
  - Gate: T-1 passes

- [ ] T-3 — template mirror of resolver
  - Agent: build
  - Files: src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/resolve-python.sh (new)
  - Principles applied: §10.4 DRY
  - Patch (deterministic): byte-equal copy of T-2 output.
  - Gate: `diff` live vs template == empty

### Phase 2 — Transparent launcher (TDD)

- [ ] T-4 — RED: launcher transparency + guard test
  - Agent: build
  - Files: tests/unit/hooks/test_run_hook_sh.py (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): — assert run-hook.sh execs the passed `.py` under the resolved interpreter; asserts the script arg (not the launcher) is what runs (integrity-transparency); asserts guard path exits 0 with one stderr line when resolver finds nothing.
  - Gate: test fails (launcher absent)

- [ ] T-5 — GREEN: create `_lib/run-hook.sh`
  - Agent: build
  - Files: .ai-engineering/scripts/hooks/_lib/run-hook.sh (new)
  - Principles applied: §10.1 KISS, §10.8 Hexagonal
  - Patch (deterministic): — source `resolve-python.sh`; `PY=$(resolve_python "$root")`; `[ -n "$PY" ] || exit 0`; `exec "$PY" "$@"`. Resolve `root` from `CLAUDE_PROJECT_DIR` else walk up. Transparent exec — no self-reference (OQ1).
  - Gate: T-4 passes

- [ ] T-6 — template mirror of launcher
  - Agent: build
  - Files: src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/run-hook.sh (new)
  - Principles applied: §10.4 DRY
  - Patch (deterministic): byte-equal copy of T-5.
  - Gate: `diff` live vs template == empty

### Phase 3 — Wire IDE surfaces (mechanical)

- [ ] T-7 — rewrite `.claude/settings.json` (22 commands)
  - Agent: build
  - Files: .claude/settings.json
  - Principles applied: §10.3 SOLID (single dispatch path)
  - Patch (deterministic):
    ```diff
    - "command": "python3 \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/telemetry-skill.py\""
    + "command": "bash \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh\" \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/telemetry-skill.py\""
    ```
    (apply same transform to all 22 entries)
  - Gate: `test_canonical_events_count.py::test_no_dead_wirings` green; 11-events-count test green

- [ ] T-8 — rewrite `templates/project/.claude/settings.json` (parallel)
  - Agent: build
  - Files: src/ai_engineering/templates/project/.claude/settings.json
  - Principles applied: §10.4 DRY (consumer parity)
  - Patch (deterministic): identical transform to T-7.
  - Gate: `diff` semantic-equal to T-7 (path-pattern parity)

- [ ] T-9 — rewrite `.codex/hooks.json` (11 commands)
  - Agent: build
  - Files: .codex/hooks.json
  - Principles applied: §10.3 SOLID
  - Patch (deterministic):
    ```diff
    - "command": "AIENG_HOOK_ENGINE=codex python3 .ai-engineering/scripts/hooks/codex-hook-bridge.py"
    + "command": "AIENG_HOOK_ENGINE=codex bash .ai-engineering/scripts/hooks/_lib/run-hook.sh .ai-engineering/scripts/hooks/codex-hook-bridge.py"
    ```
    (apply to all 11; relative paths preserved — run-hook.sh resolves root)
  - Gate: codex hooks.json valid JSON; T-15 codex case green

- [ ] T-10 — refactor `_lib/copilot-runtime.sh` to source the shared resolver + add >=3.11 gate
  - Agent: build
  - Files: .ai-engineering/scripts/hooks/_lib/copilot-runtime.sh, src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/copilot-runtime.sh
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic): — keep public fns `copilot_framework_python_script` / `_inline` (signatures unchanged) but delegate path resolution to `resolve_python` from `resolve-python.sh`; add the >=3.11 gate that copilot-runtime.sh currently lacks. Behavior for the happy venv path must be unchanged (AC5).
  - Gate: AC5 — Copilot emitter tests unchanged (T-16)

### Phase 4 — Integrity, sync, regression tests

- [ ] T-11 — regenerate hook integrity manifest
  - Agent: build
  - Files: .ai-engineering/state/hooks-manifest.json
  - Principles applied: §10.6 SDD (governance coherence)
  - Patch (deterministic): run `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` (enrolls new `_lib/resolve-python.sh`, `_lib/run-hook.sh`, changed `copilot-runtime.sh`).
  - Gate: `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py --check` exit 0

- [ ] T-12 — propagate Codex template via mirror sync
  - Agent: build
  - Files: src/ai_engineering/templates/project/.codex/hooks.json (auto-regenerated)
  - Principles applied: §10.4 DRY
  - Patch (deterministic): run `python scripts/sync_command_mirrors.py`.
  - Gate: template == live `.codex/hooks.json` (sync idempotent on re-run)

- [ ] T-13 — RED→GREEN: <3.11 regression test (the spec's keystone test, D-154-07 / AC6)
  - Agent: build
  - Files: tests/integration/test_hook_interpreter_resolution.py (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): — with a forced <3.11 `python3` first on PATH but a >=3.11 named/venv present, invoke a representative hook (prompt-injection-guard) via `run-hook.sh`; assert it runs under >=3.11 (no `ImportError`, exit 0). Second case: no >=3.11 anywhere → exactly one stderr line + exit 0. Must FAIL on pre-fix wiring (bare python3) and PASS post-fix.
  - Gate: fails pre-fix, passes post-fix

- [ ] T-14 — Copilot non-regression gate (AC5)
  - Agent: verify
  - Files: tests/integration/test_framework_hook_emitters.py (existing — Copilot cases)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): — (read-only) run existing Copilot emitter tests; assert unchanged green after T-10.
  - Gate: existing Copilot tests pass unchanged

- [ ] T-15 — full suite gate
  - Agent: verify
  - Files: tests/unit/hooks/, tests/integration/
  - Principles applied: §10.4 Goal-Driven (green before done)
  - Patch (deterministic): — run hook + integrity + canonical-events + trusted-script-lane suites.
  - Gate: all green

### Phase 5 — Docs

- [ ] T-16 — CHANGELOG entry
  - Agent: build
  - Files: CHANGELOG.md
  - Principles applied: §10.7 Clean Code (document the breakage)
  - Patch (deterministic): — under Unreleased: "fix(hooks): resolve Python >=3.11 interpreter for hook dispatch across Claude Code, Codex, Copilot (spec-154)". Note the new launcher path in command wiring.
  - Gate: docs gate green

## Risks (carried + refined)

- **R1 Copilot regression** — T-10 edits the shared-by-15-wrappers
  runtime. Mitigation: keep public fn signatures; AC5/T-14.
- **R2 Manifest staleness (refined)** — new `.sh` files unenrolled →
  `regenerate --check` fails CI (not `run_hook_safe` block). Mitigation:
  T-11 + `--check` gate.
- **R3 Codex relative-path root** — `run-hook.sh` must resolve project
  root when Codex passes a *relative* script path. Mitigation: root walk
  + T-13 codex case.
- **R4 Windows-pwsh gap (deferred)** — if Claude/Codex dispatch via pwsh
  (not git-bash) on Windows, bash `run-hook.sh` is not invoked → hooks
  unguarded there. Deferred to a follow-up `run-hook.ps1` +
  `copilot-runtime.ps1` gate. Documented, not closed in v1.
- **R5 Residual <3.11-only machine** — all hooks (incl.
  prompt-injection-guard) inert; one guard line shown. Accepted
  (unsupported per requires-python).
- **R6 No argv↔settings coherence test** (pre-existing gap, OQ2) — out of
  scope; note for a future governance test.

## Follow-ups (not this spec)

- `/ai-learn`: spec-153's own auto-consolidation did not self-apply at its
  merge (PR #539) — generalize the merge→consolidate trigger.
- Windows `run-hook.ps1` + `copilot-runtime.ps1` >=3.11 gate (R4).
- Governance test asserting every `trustedArgvs` entry maps to a real
  `settings.json` command (R6).
