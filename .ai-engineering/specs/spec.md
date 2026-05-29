---
spec: spec-154
spec_id: spec-154
slug: hook-interpreter-resolution
title: Resolve a Python >=3.11 interpreter for hook dispatch (Claude Code, Codex, Copilot)
status: draft
summary: "Route all IDE hook dispatch (Claude Code, Codex, Copilot) through one shared resolver that selects a Python >=3.11 interpreter (project .venv first), instead of bare python3 — which hits system 3.9 when no venv is active and breaks every 3.11-idiom hook. Interpreter selection, not a compat shim."
created: 2026-05-29
refs:
  audit: wf_a933215e-70b
  related_decision: D-135-13
  requires_python: pyproject.toml:8
---

# spec-154 — Resolve a Python >=3.11 interpreter for hook dispatch

## Summary

Framework hooks are dispatched by every IDE as a bare `python3
"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<x>.py"` command. Bare
`python3` resolves via `PATH`. On a machine where the first `python3` on
`PATH` is older than 3.11 — e.g. macOS CommandLineTools `/usr/bin/python3`
(3.9.6) shadowing a Homebrew/`uv` 3.11+ — the hooks raise `ImportError`
(`from datetime import UTC`, `from itertools import pairwise`) or
`TypeError` (PEP 604 `X | Y` annotations without `from __future__`),
because the hook code legitimately targets the declared floor
(`requires-python = ">=3.11"`). Every hook that imports those idioms exits
non-zero, surfacing as `Failed with non-blocking status code: Traceback`
on every event, on any consumer install whose active interpreter is <3.11.

The fix is interpreter **selection**, not a code change to the hook
libraries: a single shared, dependency-free shell resolver that selects a
>=3.11 interpreter (project `.venv` first) for hook dispatch across all
supported IDEs, generalizing the resolver that already exists for the
GitHub Copilot bridge (`_lib/copilot-runtime.sh`). Making the hook
libraries run on <3.11 (a compat shim) is explicitly rejected.

## Goals

- Every wired hook, on every supported IDE surface (Claude Code, Codex,
  GitHub Copilot), runs under a Python >=3.11 interpreter regardless of how
  the session was launched or what bare `python3` resolves to.
- One source of truth for interpreter resolution, shared by all IDE hook
  entry points (DRY); the Copilot-only resolution logic in
  `copilot-runtime.sh` is absorbed into it.
- When no >=3.11 interpreter can be found, fail **non-blocking** with
  exactly one actionable message — never a per-event traceback.
- Preserve existing GitHub Copilot hook behavior with no regression,
  proven by tests.
- Keep `run_hook_safe` green in `enforce` mode: the hook integrity
  manifest (`trustedArgvs` / `trustedScripts`) is regenerated to match the
  new command wiring.
- Respect the hot-path budget (<1s pre-commit, <5s pre-push): the common
  resolution path must not spawn an extra Python process for version
  detection.
- Propagate the fix to consumers through the installer template, with
  mirror parity preserved (`test_surface_parity` stays green).

## Non-Goals

- Making the hook libraries (`hooks/`, `_lib/`) compatible with Python
  <3.11. Rejected: ~43 files, violates CONSTITUTION Prohibition 4 /
  CLAUDE.md §13 Rule 3, hooks are stdlib-only (no shared compat module
  injectable), and `sync_mirrors` would overwrite per-file edits
  (audit verdict: `shim_feasible=False`, `policy_conflict=True`).
- Changing `requires-python = ">=3.11"` or the supported-Python floor.
- Adding an `ai-eng doctor` Python-version check in v1 (KISS — deferred;
  `cli_preflight` already gates the CLI and the launcher guard already
  emits an actionable line).
- Changing the set, order, or count of hook events (11 canonical events
  unchanged).
- Touching the Apple/macOS system `python3`.

## Decisions

- **D-154-01 — Mechanism: shell, not Python.** The resolver is a
  POSIX/bash script. A Python-based resolver would need a good interpreter
  to choose an interpreter (chicken-and-egg). The compat-shim alternative
  is rejected (see Non-Goals).
- **D-154-02 — Scope: unify all three IDEs via a shared resolution library
  (recommended variant).** Introduce one shared resolution source
  (e.g. `_lib/resolve-python.sh`) that `copilot-runtime.sh` and the new
  Claude/Codex launcher both consume. Keep each IDE's existing **entry
  wrappers** (Copilot's `copilot-*.sh`; a new `run-hook.sh` for
  Claude/Codex) so the working Copilot dispatch path is structurally
  preserved while the resolution *algorithm* becomes single-source.
  (Alternative considered: one monolithic `run-hook.sh` fully replacing
  `copilot-runtime.sh` — higher Copilot-regression risk for the same DRY
  benefit; rejected in favor of the shared-lib variant.)
- **D-154-03 — Resolution order (behavioral contract).** project venv
  (`$CLAUDE_PROJECT_DIR/.venv/bin/python`, Windows
  `.venv/Scripts/python.exe`) → `uv run python` (only when no venv) →
  version-known named interpreters `python3.13` → `python3.12` →
  `python3.11` (trusted by name, no version spawn) → bare `python3`
  **only if** it reports >=3.11. Project venv always wins for
  reproducibility, even when a newer system Python exists.
- **D-154-04 — Guard.** If no >=3.11 interpreter is found, emit exactly one
  actionable line to stderr (e.g. "ai-engineering hooks require Python
  >=3.11; activate .venv or install 3.11+") and `exit 0`. Non-blocking.
- **D-154-05 — Integrity.** Rewiring the hook command argv requires
  regenerating `.ai-engineering/state/hooks-manifest.json` (`trustedArgvs`)
  and registering the resolver/launcher script(s) under `trustedScripts`;
  `run_hook_safe` must stay green in `enforce` mode.
- **D-154-06 — Distribution + parity.** Edit the template source of truth
  (`src/ai_engineering/templates/project/.claude/settings.json` and the
  per-IDE hook configs) and regenerate mirrors via `sync_mirrors`; the
  installer copies the template verbatim
  (`installer/phases/hooks.py:179-191`) so consumers inherit the fix.
  `.claude/settings.json` is regenerated from source, not hand-edited.
- **D-154-07 — Prevention (KISS).** v1 ships the launcher + a regression
  test that executes representative hooks under a forced <3.11 interpreter
  and asserts upgrade-or-guard, plus a test asserting the Copilot path is
  unchanged. No `ai-eng doctor` Python-version check in v1.

## Acceptance Criteria

- **AC1** With the session `python3` = 3.9 and a >=3.11 present (on `PATH`
  or `.venv`), every wired hook dispatched via its IDE command runs under
  >=3.11 and exits 0 with no traceback.
- **AC2** With NO >=3.11 interpreter available anywhere, a wired hook
  prints exactly one actionable line and exits 0; no traceback; the
  session is not blocked.
- **AC3** `run_hook_safe` in `enforce` mode passes for all rewired hooks
  (manifest regenerated; argv ↔ manifest coherent).
- **AC4** `test_surface_parity` and the canonical-events-count test stay
  green.
- **AC5** Existing GitHub Copilot hook integration tests pass unchanged.
- **AC6** A new regression test fails on the pre-fix command wiring and
  passes post-fix.
- **AC7** Hot path: the common resolution path spawns no extra Python
  process for version detection (named interpreters trusted by name;
  `.venv/bin/python` invoked directly).

## Risks

- **R1 — Copilot regression.** Sharing resolution logic risks breaking the
  working Copilot path. Mitigation: keep Copilot entry wrappers; share only
  the resolver; AC5.
- **R2 — Integrity manifest drift.** If `trustedArgvs` is not regenerated,
  `enforce`-mode `run_hook_safe` would block ALL hooks (worse than today).
  Mitigation: explicit manifest-regen task + AC3 + an argv↔manifest
  coherence assertion.
- **R3 — Mirror parity break.** Editing live `settings.json` instead of the
  template trips `test_surface_parity`. Mitigation: D-154-06 (edit source +
  regen) + AC4.
- **R4 — Hot-path regression.** Naive per-hook version probing spawns
  Python and blows the <1s budget. Mitigation: D-154-03 trusts named
  interpreters; per-session caching of the resolved path (plan detail);
  AC7.
- **R5 — Residual (accepted).** On a machine with NO >=3.11 Python, all
  hooks — including the security hook `prompt-injection-guard` — are inert.
  Accepted: such a machine is unsupported (`requires-python>=3.11`); the
  guard line tells the user. Documented.
- **R6 — `uv run` cost/availability.** `uv` may be slow or absent; it is a
  fallback only when no `.venv` exists. Acceptable.
- **R7 — Windows.** `.venv/Scripts/python.exe` plus bash availability
  (git-bash) on Windows hook dispatch must keep parity with the existing
  Copilot `.ps1` story.

## Open Questions (for /ai-plan — technical HOW)

- **OQ1** Does `run_hook_safe` wrap the command at dispatch, or do scripts
  self-verify post-launch? Determines how the resolver integrates with the
  integrity layer and how the guard interacts with enforcement.
- **OQ2** Exact `trustedArgvs` regeneration workflow, and whether `.sh`
  launchers must appear in `trustedScripts` (`copilot-runtime.sh`
  currently does not).
- **OQ3** How Codex (`.codex/hooks/`) dispatches hooks today — is it
  actually broken, and what is its command form?
- **OQ4** Per-session interpreter-cache mechanism within the hot-path
  budget (env var vs runtime file).
- **OQ5** Windows hook-dispatch shell: do Claude Code / Codex invoke bash
  on Windows, or is a `.ps1` variant required (as Copilot has)?

## References

- doc: audit workflow wf_a933215e-70b (9 agents): root cause, per-hook
  blast radius, shim rejection, fix-surface enumeration, adversarial
  verdicts.
- code: pyproject.toml:8 (`requires-python = ">=3.11"`)
- code: src/ai_engineering/cli_preflight.py:15 (`_MINIMUM_PYTHON=(3,11)`,
  gates CLI only — hooks bypass it)
- code: .ai-engineering/scripts/hooks/_lib/copilot-runtime.sh:7-45
  (existing venv→uv resolver to generalize)
- code: .ai-engineering/state/hooks-manifest.json (`trustedArgvs` /
  `trustedScripts`)
- code: scripts/sync_mirrors/core.py; src/ai_engineering/installer/phases/hooks.py:179-191
- decision: D-135-13 (`spec_lifecycle.py` fixed narrowly with
  `timezone.utc`; lesson not generalized to hook dispatch)
