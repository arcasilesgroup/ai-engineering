---
spec: spec-156
title: Scope-Aware CLI — Auto-Detect Global/Local + Dual-Scope Hardening
status: draft
effort: large
summary: Make every ai-eng command auto-detect global vs local installs and act on the resolved scope (local-wins + announce when both), and harden the dual-scope install/update/doctor stack and the PyPI update notice so the branch is robust and 100% functional.
---

# spec-156 — Scope-Aware CLI + Dual-Scope Hardening

## Summary

The `feat/version-update-notice` branch adds two headline features on top of a
solid, well-tested default (local) CLI: (1) a cross-surface PyPI
update-available notice, and (2) global-vs-local install with dual-scope
update. A 17-agent adversarial audit of the branch (vs `main`) found the
default/local path sound, but both new features leaky or non-functional under
**global scope** and **automation/`--json` hot paths**.

Two corrections drive this spec. First, a **product reframe**: the operator does
not want `--global`/`--local` to be the primary interface. Instead, **every**
`ai-eng` invocation must first auto-detect whether a global install
(`~/.ai-engineering/`) and/or a local install (`./.ai-engineering/`) exist, then
act on the resolved scope and announce it — for `install`, `update`, `config`,
`doctor`, and every other command. Flags become an explicit override
(escape hatch), not the entry point.

Second, a **robustness mandate**: the install/update/doctor stack is only
partly scope-aware. The brain (`.ai-engineering/`) re-roots to `~/` correctly,
but IDE surfaces, post-pipeline manifest writers, the operational/scripts
phases, and the entire updater do **not** — so a global install is created once
and then silently corrupts on the next `update`/`reconfigure`/`repair`. The
update notice leaks onto automation surfaces and burns its own throttle.

## Current State (audit evidence)

Blocker / High findings (adversarially verified):

1. **`update --global` never re-roots IDE surfaces** — `updater/service.py`
   computes `dest = target/rel` with `target = Path.home()`, so it plans
   `~/CLAUDE.md` instead of `~/.claude/CLAUDE.md` and orphans the real files.
   Global installs are un-updatable. (`updater/service.py:783,802`)
2. **Global install drops operator stack/surface/vcs choices** —
   `_write_providers/_write_surfaces/initialize_manifest_project_name` are
   anchored at the repo `target`; for global the manifest lives at `~`, so they
   no-op and leave template defaults. (`installer/service.py:310-312,415,435`)
3. **Interactive global leaks a phantom repo-local marker + 9 scripts** —
   `install_with_pipeline` computes a scoped `state_root` but calls
   `_run_operational_phases(target,…)` and `ScriptsPhase` against the repo
   unconditionally, so `doctor`/`update` then see BOTH scopes and write into
   the opted-out repo. The new wizard prompt makes this reachable interactively.
   (`installer/service.py:316,544`; `scripts.py:103,158`)
4. **Scope is never persisted; `_is_reinstall` checks the repo only** —
   `InstallState` has no `scope` field; global reinstall/reconfigure/repair/
   `--fresh` is undetectable and surface-deselection cleanup never fires.
   (`core.py:325`)
5. **Update notice leaks + burns throttle on automation/`--json`** — the app
   callback gates on the top-level `json_output` flag only and ignores
   `_EXEMPT_COMMANDS`; the 6 per-command `--json` options set mode AFTER the
   callback, so the notice (and `cache.mark_shown()` disk write) fires on
   `check --json`, `gate` pre-commit, `internal python`, `update`, `doctor`.
   (`cli_factory.py:216`)
6. **Test-infra** — a lifecycle test leaks process-global json-mode, silently
   no-op'ing 4 notice tests; CI is green only by alphabetical collection order.
   (`cli_output._json_mode`, `test_version_lifecycle.py:265`)
7. **Global multi-surface `AGENTS.md` fan-out** — codex/copilot/opencode/
   antigravity all map `AGENTS.md→AGENTS.md`; the dest index dedups
   (last-write-wins) so only one home gets the file and `verify()` falsely
   passes. (`ide_config.py:44,206`)

Medium / Low: PEP 440 comparison broken for rc/dev/post/local/ragged versions
(3 duplicated comparators) · ai-start reads stale manifest `framework_version`
instead of live `__version__` · offline respawns a refresh child every
invocation (`checked_at` never advances on failure) · `version` /
`version upgrade` bypass the CLI error boundary, emit no JSON envelope, and
`version upgrade --json` exits 2 · global cursor/copilot guidance collected but
never printed · `--global` hooks-manifest never regenerated · doctor
double-counts scope when repo==home · dry-run overstates git hooks for global.

Solid (do not touch): version adapters' fail-open contract (atomic cache,
detached DEVNULL refresh, 2 s cap); **stdout/JSON envelopes are clean** (the
notice leak is stderr/throttle only); deprecated/EOL hard-block; the brain tree
scope-rooting; antigravity never writing `GEMINI.md`; **the wizard scope-prompt
gating is correct** (fires only on first interactive greenfield no-flag install
and threads scope correctly).

## Goals

- Every `ai-eng` command resolves scope by **auto-detection** before acting:
  only-global → act global; only-local → act local; both → act local and
  announce that global also exists; neither → `install` runs the greenfield
  wizard (existing) and all other commands fail-loud "not installed".
- Every command **announces the resolved scope** in a single human line
  (suppressed in `--json`).
- `--global` / `--local` remain as an explicit per-command **override** for the
  ambiguous (both-installed) and CI/non-interactive cases — never required in
  the common case.
- `install`, `update`, `reconfigure`, `repair`, `--fresh`, `config`, and
  `doctor` are all **consistently scope-aware**: every destination AND every
  state/manifest/scripts/hooks write routes through one scope resolver, so a
  global install can be installed, updated, reconfigured, and repaired with no
  orphaned `~/CLAUDE.md`/`~/AGENTS.md` and no phantom repo-local marker.
- The chosen scope is **persisted** (on `InstallState`) and reinstall detection
  is scope-aware.
- Global install of multiple `AGENTS.md`-sharing surfaces writes the file into
  **each** owning IDE home, and `verify()` asserts per-surface presence.
- The update notice renders ONLY for interactive human commands: no leak onto
  `--json` (any entry point), `internal`, `gate`/hook hot paths; automation
  never advances the throttle.
- One canonical PEP 440 version comparator is used everywhere (CLI notice,
  checker, scope_status, ai-start template); ai-start sources the installed
  version from live `__version__`.
- `version` and `version upgrade` are wrapped in the CLI error boundary, emit a
  JSON envelope on success, capture subprocess stdout in JSON mode, and accept
  `--json`.
- Offline / PyPI-down spawns at most one refresh child per TTL.
- New regression tests cover: scope auto-resolution per state (only-global /
  only-local / both / neither), install→update→doctor global round-trip via the
  real pipeline, notice stdout purity + automation exemption + stale-spawn
  throttle, multi-surface global fan-out, and the json-mode test-isolation fix.

## Non-Goals

- Changing the **semantics** of the default local install/update (it is solid;
  only its scope-routing plumbing is generalized).
- Any third scope beyond `global` and `local` (no team/remote/org scope).
- Automatic migration of an existing install between scopes (operator re-runs
  `install` explicitly).
- Consolidating the 6 per-command `--json` options into a single top-level flag
  (orthogonal SSOT cleanup; the notice fix does not require it — deferred).
- Symlink/reference-based shared `AGENTS.md` (each IDE home gets a real file).
- Re-litigating governance side-changes already on the branch (decision-store
  tracking, `.snyk` policy, mirror/CLAUDE.md sync, hooks-manifest sha256).

## Decisions

- **D-156-01 — Detection-first scope model.** Every command auto-detects global
  (`~/.ai-engineering/` marker) and local (`./.ai-engineering/` marker) scope
  before acting: only-global→global; only-local→local; both→local-wins with an
  announcement that global exists; neither→`install` wizard or other commands
  fail-loud.
  **Rationale**: the operator wants scope inferred from reality, not declared by
  flag; local-wins is deterministic and CI-safe and matches the existing
  dual-scope update precedence.
- **D-156-02 — Flags are override-only.** `--global`/`--local` survive on every
  scope-affecting command purely as an explicit override for the both-installed
  and non-interactive/CI cases; they are never required in the common path.
  **Rationale**: deterministic disambiguation for automation without making the
  flag the primary interface (the reframe).
- **D-156-03 — Announce resolved scope.** Every scope-affecting command prints
  one concise human line ("acting on global (~/) …" / "acting on local (./);
  global also present — use --global to target it"), suppressed under `--json`.
  **Rationale**: the operator explicitly asked the CLI to state where it acts.
- **D-156-04 — One scope resolver for all destinations and state writes.** Route
  every IDE-surface destination, brain path, manifest write, operational-phase
  state write, ScriptsPhase write, and hooks-manifest path through a single
  scope resolver (`installer.scope.dest` plus a single scoped brain-root helper).
  **Rationale**: four blocker/high findings share one root cause — partial scope
  awareness; centralizing the mapping removes the whole class.
- **D-156-05 — Updater re-roots IDE surfaces.** The updater computes every IDE
  destination (and orphan detection) through `scope.dest(surface, scope, …)`,
  not `home/rel`.
  **Rationale**: fixes blocker 1; makes global installs updatable.
- **D-156-06 — Post-pipeline writers honor the scoped brain root.** Manifest
  project-name/providers/surfaces writers and `_run_operational_phases` plus
  `ScriptsPhase` write to `Path.home()` when scope is global.
  **Rationale**: fixes blocker 2 and high 3 (operator choices persisted; no
  phantom repo marker).
- **D-156-07 — Persist scope + scope-aware reinstall detection.** Add a `scope`
  field to `InstallState`; make `_is_reinstall` (and reconfigure/repair/`--fresh`
  detection plus surface-deselection cleanup) check the resolved scope's marker.
  **Rationale**: fixes high 4; the detection model needs the recorded scope.
- **D-156-08 — Per-surface global fan-out for shared instruction files.** In
  global scope, a shared `AGENTS.md` is written into every owning surface's home
  (`~/.codex/`, `~/.config/opencode/`, `~/.gemini/`), and `verify()` asserts
  per-surface presence.
  **Rationale**: fixes high 7; each IDE reads its own home, so one physical file
  per IDE is the only "100% functional" answer (symlinks rejected as
  cross-platform-fragile — Non-Goal).
- **D-156-09 — Notice renders after-command, gated on resolved mode plus exempt
  set.** Move the update-notice render to after output mode is resolved; gate on
  `cli_output.is_json_mode()` and a `_NOTICE_EXEMPT` set
  (at least {version, internal, gate, hook entrypoints}); automation/`--json`
  paths never call `cache.mark_shown()`.
  **Rationale**: fixes high 5 leak and throttle burn without consolidating
  `--json` (Non-Goal). Notice stays stderr-only.
- **D-156-10 — json-mode test isolation.** Add an autouse teardown fixture
  (`tests/conftest.py`) resetting `set_json_mode(False)`; optionally restore
  prior mode on callback exit.
  **Rationale**: fixes high 6 (CI green only by collection order; real
  cross-test contamination).
- **D-156-11 — One canonical PEP 440 comparator.** Extract a single
  `packaging.version.Version`-based comparator (InvalidVersion→False) used by
  `cli_ui`, `checker`, `scope_status`, and mirrored into the `session_bootstrap`
  template via sync.
  **Rationale**: the 3 hand-rolled `int(split('.'))` parsers miss
  rc/dev/post/local/ragged versions (notably `-e`/CI dev installs).
- **D-156-12 — Installed-version is live `__version__` everywhere.** ai-start
  and all "update available" surfaces source the installed version from
  `ai_engineering.__version__`, not manifest `framework_version`.
  **Rationale**: manifest `framework_version` goes stale after `version upgrade`
  (updater never rewrites it), causing perpetual nag; live `__version__` matches
  the notice.
- **D-156-13 — Refresh spawn throttle.** On fetch failure, stamp a separate
  `attempted_at` (or advance `checked_at`) so `is_stale()`/spawn is suppressed
  within `ttl_hours`.
  **Rationale**: fixes per-invocation fork+connect churn when offline; the
  detached child is otherwise harmless but unbounded.
- **D-156-14 — version commands join the error boundary.** Wrap `version` and
  `version upgrade` registrations in `_safe`; emit `emit_success` on rc 0;
  capture/DEVNULL the upgrade subprocess stdout in JSON mode; accept `--json`.
  **Rationale**: removes tracebacks and missing-envelope gaps on these exempt
  commands.
- **D-156-15 — Surface global guidance plus scope-aware hooks-manifest.**
  Aggregate each phase's `GuidanceSentinel` into install output and the JSON
  envelope so global cursor/copilot wire-up steps are printed; make
  `_finalize_hooks_manifest` use the scoped brain root.
  **Rationale**: choosing cursor/copilot in global must do something visible;
  the global hooks-manifest must regenerate to match `run_hook_safe` integrity.
- **D-156-16 — Single refresh entrypoint.** Keep `python -m
  ai_engineering.version.refresh` as the one spawn SoT; delete the redundant
  hidden `ai-eng internal version-refresh` command and correct the docstring.
  **Rationale**: settles the SSOT/dead-code question (the CLI command is never
  invoked by `spawn_background`).
- **D-156-17 — Low-severity polish.** Dedupe doctor scope when
  `target.resolve()==Path.home().resolve()`; guard the dry-run git-hooks
  `PlannedAction` with the same `scope != "global"` condition `execute()` uses.
  **Rationale**: removes double-counting and dry-run overstatement.

## Risks

- **Large blast radius** across installer/updater/cli/doctor.
  **Mitigation**: one scope resolver (D-156-04) instead of scattered edits; TDD
  per finding; the audit already enumerates exact file:line targets; existing
  local-path tests are the regression backstop.
- **Detection model changes UX of every command** (new announce line, new
  fail-loud "not installed" for non-install commands).
  **Mitigation**: concise one-line, `--json`-suppressed; fail-loud only when
  truly no install for a command that needs one.
- **Scope misdetection writing to the wrong root.**
  **Mitigation**: marker-presence detection is already proven for the brain; add
  install→update→doctor global round-trip integration tests through the real
  pipeline (not hand-rolled phase calls, which masked blocker 1).
- **Home-dir permission/creation failures under global.**
  **Mitigation**: fail-loud with a clean error-boundary message; never silently
  fall back to repo.
- **Notice-render relocation regressing the human experience** (notice missing
  where it should show).
  **Mitigation**: explicit exempt-set tests plus a stdout==''/stderr-has-notice
  test for human mode and a no-leak test for json and automation.
- **Behavioral change for scripts that relied on the leaky both-scope no-flag
  update.**
  **Mitigation**: local-wins is the documented precedence; CHANGELOG documents
  the breakage (hard-rule #3, no shim).

## Open Questions

- None blocking. D-156-08 (per-surface fan-out), D-156-12 (live `__version__`),
  D-156-15 (surface guidance), and D-156-16 (delete the redundant refresh
  command) were resolved with the rationale above and are flagged here for
  explicit confirmation in the spec-review loop; reverse any during review if the
  intended product behavior differs.

## References

- pr: arcasilesgroup/ai-engineering#556
- doc: .ai-engineering/runtime/tool-outputs/2026-05-30T175210Z-84b456277f5b4fea89fcaccd53ebdecf.txt (17-agent CLI-wide audit synthesis)
