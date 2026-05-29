---
spec: spec-154
title: Resolve a Python >=3.11 interpreter for hook dispatch (Claude Code, Codex, Copilot)
status: draft
effort: medium
summary: "Route all IDE hook dispatch (Claude Code, Codex, Copilot) through one shared resolver that selects a Python >=3.11 interpreter (project .venv first), instead of bare python3 — which hits system 3.9 when no venv is active and breaks every 3.11-idiom hook. Interpreter selection, not a compat shim."
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
  manifest is regenerated to match the new command wiring.
- Respect the hot-path budget (<1s pre-commit, <5s pre-push): the common
  resolution path must not spawn an extra Python process for version
  detection.
- Propagate the fix to consumers through the installer template, with
  mirror parity preserved.

## Non-Goals

- Making the hook libraries (`hooks/`, `_lib/`) compatible with Python
  <3.11. Rejected: ~43 files, violates CONSTITUTION Prohibition 4 /
  CLAUDE.md §13 Rule 3, hooks are stdlib-only (no shared compat module
  injectable), and `sync_mirrors` would overwrite per-file edits.
- Changing `requires-python = ">=3.11"` or the supported-Python floor.
- Adding an `ai-eng doctor` Python-version check in v1 (deferred;
  `cli_preflight` already gates the CLI and the launcher guard already
  emits an actionable line).
- Changing the set, order, or count of hook events (11 canonical events
  unchanged).
- Touching the Apple/macOS system `python3`.
- Windows native (pwsh/.ps1) hook dispatch — deferred to a follow-up; v1
  ships the POSIX bash launcher (covers macOS/Linux/git-bash).

## Decisions

- **D-154-01 — Mechanism: shell, not Python.** The resolver is a
  POSIX/bash script, sourced by the per-IDE launchers.
  **Rationale**: a Python-based resolver would itself need a working
  interpreter to choose an interpreter (chicken-and-egg); the alternative
  of shimming the hook libraries for <3.11 is rejected (Non-Goals;
  CONSTITUTION Prohibition 4).
- **D-154-02 — Scope: unify all three IDEs via a shared resolution
  library.** One shared source (`_lib/resolve-python.sh`) is consumed by
  both `copilot-runtime.sh` and the new `run-hook.sh`; each IDE keeps its
  existing entry wrappers.
  **Rationale**: this shares the resolution algorithm (DRY) while
  structurally preserving the working Copilot dispatch path; a monolithic
  launcher fully replacing `copilot-runtime.sh` carried higher
  Copilot-regression risk for the same benefit.
- **D-154-03 — Resolution order (behavioral contract).** project venv →
  named `python3.13` / `python3.12` / `python3.11` → `uv run` → bare
  `python3` only when it reports >=3.11; the project venv always wins.
  **Rationale**: venv and named interpreters are instant and
  version-known (no spawn); `uv run` spawns and is hot-path-hostile, so it
  ranks below named; bare `python3` is gated to avoid the <3.11 trap.
- **D-154-04 — Guard.** If no >=3.11 interpreter is found, emit exactly one
  actionable stderr line and exit 0 (non-blocking).
  **Rationale**: a missing-interpreter condition must not wedge the
  session; one warning beats a per-event traceback, and other security
  layers still run where they can.
- **D-154-05 — Integrity.** Regenerate `hooks-manifest.json` so the new
  launcher `.sh` files enroll; the gate is
  `regenerate-hooks-manifest.py --check`.
  **Rationale**: `run_hook_safe` verifies hook script bytes against the
  manifest, and the CI `--check` gate fails on any unenrolled or drifted
  `.sh`.
- **D-154-06 — Distribution + parity.** Edit the template source of truth
  and regenerate mirrors via `sync_mirrors`; the installer copies the
  template verbatim.
  **Rationale**: consumers inherit the fix with no per-repo edits, and
  editing live files instead of the template source would break surface
  parity.
- **D-154-07 — Prevention (KISS).** v1 ships the launcher plus a
  regression test (forced <3.11 → upgrade-or-guard); no `ai-eng doctor`
  Python check.
  **Rationale**: `cli_preflight` already gates the `ai-eng` CLI and the
  launcher guard already warns, so a doctor check is redundant surface for
  v1.

## Acceptance Criteria

- **AC1** With the session `python3` = 3.9 and a >=3.11 present (on `PATH`
  or `.venv`), every wired hook dispatched via its IDE command runs under
  >=3.11 and exits 0 with no traceback.
- **AC2** With NO >=3.11 interpreter available anywhere, a wired hook
  prints exactly one actionable line and exits 0; no traceback.
- **AC3** `run_hook_safe` in `enforce` mode passes for all rewired hooks
  (manifest regenerated; `--check` exit 0).
- **AC4** Surface/parity + canonical-events tests stay green.
- **AC5** Existing GitHub Copilot hook integration tests pass unchanged.
- **AC6** A regression test fails on the pre-fix command wiring and passes
  through the launcher.
- **AC7** Hot path: the common resolution path spawns no extra Python
  process for version detection.

## Risks

- **R1 — Copilot regression.** Sharing resolution logic risks the working
  Copilot path. Mitigation: keep Copilot entry wrappers; share only the
  resolver; AC5.
- **R2 — Integrity manifest staleness.** New `.sh` unenrolled →
  `regenerate --check` fails CI. Mitigation: regen task + the `--check`
  gate.
- **R3 — Mirror parity break.** Editing live files instead of the template
  trips parity. Mitigation: edit source + regen (D-154-06).
- **R4 — Windows pwsh gap (deferred).** If Claude/Codex dispatch via pwsh
  (not git-bash) on Windows, the bash launcher is not invoked. Deferred to
  a follow-up `run-hook.ps1` + `copilot-runtime.ps1` gate; documented, not
  closed in v1.
- **R5 — Residual <3.11-only machine.** All hooks (incl. the security hook)
  are inert; one guard line is shown. Accepted (unsupported per
  requires-python).
- **R6 — Hot-path regression.** Naive per-hook version probing spawns
  Python. Mitigation: trust named interpreters; per-session cache; AC7.

## Open Questions

- All five planning open questions (integrity dispatch model, manifest
  regen workflow, Codex wiring, hot-path cache, Windows shell) were
  resolved during `/ai-plan` and recorded in plan.md; none remain blocking
  for v1.

## References

- doc: audit workflow wf_a933215e-70b — root cause, per-hook blast radius,
  shim rejection, fix-surface enumeration, adversarial verdicts.
- doc: pyproject.toml:8 — requires-python = ">=3.11".
- doc: src/ai_engineering/cli_preflight.py:15 — _MINIMUM_PYTHON gates the
  CLI, not hook dispatch.
- doc: .ai-engineering/scripts/hooks/_lib/copilot-runtime.sh — existing
  venv resolver generalized into the shared resolver.
- doc: .ai-engineering/state/hooks-manifest.json — hook integrity manifest.
- doc: D-135-13 — prior spec_lifecycle.py narrow fix (timezone.utc), not
  generalized to hook dispatch.
