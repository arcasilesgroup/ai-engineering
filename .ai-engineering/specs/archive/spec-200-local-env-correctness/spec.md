---
spec: spec-200
slug: local-env-correctness
title: "Local-environment correctness: surface-aware stack detection and canonical hook state"
status: in-progress
effort: medium
summary: "Stop the stack detector reading an AI surface directory's own package manifest as a project stack, make CLI-envelope tests immune to any stderr diagnostic, and retire the forbidden state/runtime/ path across every live writer, the installer, and the dead re-exports left behind by spec-125."
---

# spec-200 — Local-environment correctness

## Summary

Two defects make `ai-engineering` behave differently on a developer machine
than it does in CI, and both were found the hard way while cutting v0.13.0.

The first is consumer-facing. `_WALK_EXCLUDE` in the stack detector prunes
vendor and build directories — `node_modules`, `.venv`, `build`, `dist`,
`target`, `Pods` — but not the AI surface directories the framework itself
generates: `.opencode`, `.claude`, `.codex`, `.agents`, `.cursor`. OpenCode
installs its own plugin runtime as `.opencode/package.json` and
`.opencode/package-lock.json`, and the marker walk reads those as a
project-level JavaScript stack. Any project that configures `python` and also
has OpenCode installed therefore reports permanent stack drift on every
`ai-eng` invocation, and under `AIENG_STACK_DRIFT_STRICT=1` that drift is
*blocking* on `commit`, `pr` and `gate`. Surface directories are already
detected separately and deliberately by `detect_surfaces`, which is root-level
only by design; they have no business in stack detection at all.

The drift warning is written to stderr, which should be harmless, but Typer's
`CliRunner` merges stderr into `result.output`. Seventeen tests that parse a
JSON envelope out of `result.output` therefore fail whenever any diagnostic is
emitted. Excluding the surface directories removes today's trigger, but the
tests remain fragile: a project that legitimately adds a second stack would
break them again with correct code on both sides. The assertion those tests
mean to make is about the envelope on stdout, so they should read stdout.

The second defect is local-only noise with the same shape. spec-125 relocated
`.ai-engineering/state/runtime/` to `.ai-engineering/runtime/`, and
`test_forbidden_dirs_absent` guards against the old path reappearing — but the
hook library still writes there. In CI no hook layer runs, so the directory
never appears and the test passes; in an interactive session hooks fire on
every tool call and recreate it between the test's own cleanup and its
assertion, so the test fails on code that is correct. The test's docstring
already records this as a known leftover awaiting a proper fix.

The relocation is less complete than spec-125's own notes imply. Five hook-tree
files still resolve the forbidden path in live code — `trace_context.py` writes
`trace-context.json`, `audit.py` writes `event-sidecars/`, `hook-common.py` and
`runtime-session-start.py` both write `session-pointer.json`, and
`observability.py` *reads* the `VERSION` file that stamps `frameworkVersion` on
every telemetry event. Two more files carry nine dead `*_REL` constants that
spec-125 Wave 2b kept as backwards-compatible re-exports, self-documented as
"do NOT use these for new code" and unused by the helpers around them. And the
path escapes the hook tree entirely: `cli_commands/core.py` writes that
`VERSION` file, and `installer/opa.py` writes the compiled OPA bundle beside
it. Ten sites, three of them outside the layer the defect was assumed to live
in.

That inventory raised a migration question, and answering it is what makes this
spec safe to land in one pass. It has a structural answer rather than a
mechanism (D-200-05): hook scripts are project-deployed files, so a consumer
only receives the new path by running `ai-eng install` or `ai-eng update`, and
both funnel through `_finalize_hooks_manifest`, which re-stamps `VERSION` in
the same run before any new-path hook can execute. Old scripts read the old
file, new scripts read the new one, and no intermediate state exists.

Neither defect affects the published package. Both cost real time: together
they produced nineteen spurious local failures and a NO-GO on a release whose
content was sound.

## Goals

- A project that configures one stack and also has an AI surface directory
  containing that surface's own package manifest reports no stack drift.
- Stack detection never treats a framework-generated surface directory as
  evidence of a project stack, regardless of what a host tool installs inside
  it.
- CLI tests that assert on a JSON envelope parse stdout only, so any present or
  future diagnostic written to stderr cannot fail them.
- No code in the repository resolves `.ai-engineering/state/runtime/` — not the
  hook library, not the installer, not a dead re-export — and
  `test_forbidden_dirs_absent` passes in an interactive session with hooks
  active, not only in CI where nothing writes.
- Telemetry keeps stamping the pinned `frameworkVersion` across the upgrade
  that moves the path: no install falls back to the importlib-metadata version
  because its `VERSION` file was left at an address nobody reads.
- The compiled OPA bundle and the signature the doctor probe looks for stay
  where their consumers expect them.
- The hook script tree and its installer template mirror stay byte-identical,
  and the hooks manifest is re-pinned, so hook integrity does not break for
  existing installs.
- No change to what `detect_surfaces` reports: surfaces are still discovered,
  just not as stacks.

## Non-Goals

- Making the stack detector consult `.gitignore`. Pruning is by directory name
  and stays that way; the defect is a missing name, not a missing mechanism.
- Changing the drift warning's severity, its wording, or the
  `AIENG_STACK_DRIFT_STRICT` contract. The warning is correct behaviour once it
  stops firing on false evidence.
- Silencing diagnostics so tests pass. The tests are what change; the
  diagnostic stays.
- A bespoke migration command, a compatibility read that tries the old path
  before the new one, or a deprecation window on the `*_REL` re-exports. §13.3
  forbids all three, and D-200-05 shows none is needed.
- Changing how `frameworkVersion` is resolved, or its fallback order. The
  `VERSION`-first, importlib-metadata-second contract from spec-190 D-190-01 is
  unchanged; only the file's address moves.
- Adding a reader for the compiled `bundle.tar.gz`. It has none today and gains
  none here; only its output path moves.
- The remaining stale-mirror defect: `.opencode` mirrors at the repository root
  are two specs out of date because the generator declares no root target for
  that family. Same area, different fix, and it belongs to its own spec.
- Registering the burned spec IDs 193–199 in the lifecycle ledger.

## Decisions

### D-200-01 — Surface directories are excluded from stack detection

`.opencode`, `.claude`, `.codex`, `.agents` and `.cursor` join `_WALK_EXCLUDE`
alongside the vendor and build directories already there.

**Rationale**: §10.1 KISS — the exclusion set is the mechanism that already
exists for exactly this, and these directories belong in it on principle, not
just to fix OpenCode. A surface directory holds host tooling the framework
itself generates; treating its contents as project evidence is a category
error. `detect_surfaces` already covers them, root-level only and by design,
so nothing is lost. Excluding only `.opencode` would leave the same trap for
the next host that installs a package manifest into its own directory.

### D-200-02 — Envelope tests assert on stdout, not on merged output

Tests that parse a JSON envelope stop reading `result.output` and read the
stdout stream instead.

**Rationale**: The assertion is about what the command emits on stdout;
reading merged output silently widens it into "and nothing was written to
stderr", which is not the contract and not something the tests declare. Fixing
only D-200-01 leaves seventeen tests that fail on correct code as soon as a
project legitimately gains a second stack. Diagnostics on stderr are a feature
— the tests should be indifferent to them.

### D-200-03 — Every live resolver of the forbidden path moves, hooks and installer alike

All five hook-tree files that resolve `.ai-engineering/state/runtime/` in live
code move to `.ai-engineering/runtime/` — `trace_context.py`, `audit.py`,
`hook-common.py`, `runtime-session-start.py`, `observability.py` — and so do the
two sites outside the hook tree: the `VERSION` write in
`cli_commands/core.py` and the bundle output in `installer/opa.py`. The stale
`state/runtime/bundle.tar.gz` reference in `installer/gitignore.py`'s docstring
is corrected in the same pass.

**Rationale**: §10.4 DRY — one canonical location per datum, and the datum's
canonical location was decided by spec-125. The guard test has been correctly
reporting a real violation that was read as flakiness because it only
reproduces where hooks run. Moving only the hook tree would leave the installer
writing `VERSION` to an address the moved reader no longer consults, which is
strictly worse than the defect: the telemetry version would silently degrade to
a fallback with no failure anywhere. The path is one datum; it moves as one
change or not at all. Both `state/runtime/` and `runtime/` are already ignored
by the gitignore template, so no ignore rule needs adding.

### D-200-04 — The dead `*_REL` re-exports are deleted, not deprecated

The nine legacy constants in `_lib/runtime_state.py` (`RUNTIME_DIR_REL` and the
six leaves derived from it) and `_lib/risk_accumulator.py` (`RUNTIME_DIR_REL`,
`RISK_STATE_REL`) are removed along with their `__all__` entries, and the
removal is recorded in CHANGELOG as a breaking change.

**Rationale**: §13.3 — no backwards-compat shims for migrated content; hard
rename, hard delete, CHANGELOG documents the breakage. These constants are that
shim verbatim: spec-125 Wave 2b kept them "solely so any external import path
keeps resolving", and their own comment says "do NOT use these for new code".
Every active resolution already flows through the `RUNTIME_DIR(project_root)`
factory in `hook_context.py`. Leaving them is not neutral — a constant named
`RUNTIME_DIR_REL` pointing at the forbidden path is precisely how a future
writer resurrects it, and the guard test would then blame the writer instead of
the bait. Repointing them at the new path instead of deleting them would keep
two names for one datum, which is the §10.4 violation this spec exists to
close.

### D-200-05 — No migration step: the deployment model already sequences it

Nothing migrates existing `.ai-engineering/state/runtime/` content. The
correctness argument is structural, and it is an acceptance criterion rather
than a review note.

**Rationale**: Hook scripts are project-deployed files, not package modules, so
a consumer receives new-path hooks only by running `ai-eng install` or `ai-eng
update` — and both funnel through `_finalize_hooks_manifest`, which writes
`VERSION` before returning. A run that deploys new hook bytes therefore
re-stamps `VERSION` at the new path in the same run, ahead of any new-path hook
executing; a consumer who upgrades the package without running either still has
old-path scripts reading the old-path file. Both states are self-consistent and
there is no window between them. The remaining files are transient by
construction: `session-pointer.json`, `trace-context.json` and `event-sidecars/`
are per-session, and `bundle.tar.gz` is a write-only build artifact with no
reader anywhere — `opa_runner.DEFAULT_BUNDLE_PATH` is `.ai-engineering/policies`
and the signature the doctor probe checks is written into that directory, not
beside the tarball. A migration command would move data that is either rewritten
on the next install or safe to abandon, which is §10.2 YAGNI.

One caveat this decision pins deliberately: `_finalize_update_hooks_manifest`
early-returns when an apply mutated no files, so the `VERSION` stamp is skipped
on a no-op update. That is harmless here — the update carrying this change
necessarily rewrites hook scripts, so `applied_count` is non-zero — but the
stamp must not later be moved out of `_finalize_hooks_manifest` into a
narrower call site, because the zero-window guarantee above depends on it
running wherever hook bytes are deployed.

### D-200-06 — The orphaned directory is reaped by the rotation path that already exists

The now-unwritten `.ai-engineering/state/runtime/` directory is removed by the
existing SessionEnd runtime-rotation reaper, alongside the stale `state.db` and
siblings it already deletes.

**Rationale**: §10.1 KISS — the reaper for stale runtime leftovers exists and
this is one more leftover; a dedicated cleanup command for a gitignored
directory holding at most four transient files would be new surface for no new
capability. Reaping matters despite the directory being invisible to git:
`test_forbidden_dirs_absent` asserts on the filesystem, so a developer machine
that keeps the orphan from before the upgrade would keep failing the guard on
correct code — the exact symptom this spec is closing.

### D-200-07 — Script tree and template mirror change in lockstep

Every hook script edited under `.ai-engineering/scripts/hooks/` is mirrored
byte-identically into `src/ai_engineering/templates/.ai-engineering/scripts/`,
and the hooks manifest is regenerated in the same change.

**Rationale**: The template tree is the install payload; letting the two drift
ships a fix that never reaches consumers. The manifest pins a sha256 per hook
script and `run_hook_safe` enforces it, so editing a script without re-pinning
disables the hook for anyone running in the default enforce mode — the failure
would be silent and worse than the defect being fixed.

## Risks

- **The exclusion could hide a genuine stack.** A polyglot repository that
  really does keep source inside a surface directory would stop being detected.
  Mitigation: surface directories are framework-generated and documented as
  such; keeping project source there is already unsupported. If it ever becomes
  a real pattern, the fix is an explicit `providers.stacks` entry, which is
  authoritative anyway.
- **Reading stdout instead of merged output could mask a regression** where a
  command wrongly writes part of its envelope to stderr. Mitigation: that is a
  distinct assertion and should be its own test if it matters; conflating the
  two is what made these tests fragile in the first place.
- **The path inventory grew once and could grow again.** It was assumed to be
  hooks-only, then found to include the installer and the OPA bundle; a reader
  outside this repository — a consumer script, an out-of-tree hook — cannot be
  inventoried at all. Mitigation: the `*_REL` deletions turn any such import
  into an `ImportError` at load rather than a silent read of a directory nobody
  writes, which is the failure mode worth having, and CHANGELOG names the break.
- **The `VERSION` stamp is the one datum where a missed move degrades in
  silence.** If the reader moves and the installer write does not, telemetry
  falls back to the metadata version and no gate notices. Mitigation: the two
  sites move in the same change (D-200-03), and an acceptance criterion asserts
  the post-install file exists at the new path with the pinned version.
- **D-200-05's no-migration argument is only as good as its premise.** It holds
  because the `VERSION` stamp sits inside `_finalize_hooks_manifest`, which runs
  wherever hook bytes are deployed. A later refactor that narrows that call site
  reopens the window. Mitigation: the dependency is stated in the decision and
  carries a test asserting the stamp happens on the update path, so the
  refactor fails loudly.
- **A missed template mirror or a stale manifest silently disables hooks.**
  This has happened before in this repository, and this change edits seven hook
  scripts — the widest mirror surface the repo has touched in a while.
  Mitigation: byte-parity and manifest freshness are acceptance criteria here,
  not review notes.
- **The defects are independent and could have been separate specs.** Bundling
  them means the verified stack-detector fix waits on the path work.
  Mitigation: they share a root cause worth naming — behaviour that differs
  between a developer machine and CI, verified only in CI — and the path work
  is now fully inventoried rather than estimated. If it grows past this
  inventory during `/ai-plan`, it splits and A+B ships alone.

## Acceptance Criteria

- [ ] With `.opencode/package.json` present and `providers.stacks: [python]`,
      `ai-eng check` emits no stack-drift warning.
- [ ] A regression test covers the surface-directory case, failing against the
      current exclusion set and passing after it.
- [ ] `detect_surfaces` still reports every surface it reported before, proven
      by an unchanged assertion.
- [ ] Every test that parses a JSON envelope passes with a diagnostic present
      on stderr, demonstrated by a deliberately induced drift warning.
- [ ] A repository-wide search for `state/runtime` returns no live path
      resolution in `src/` or `.ai-engineering/scripts/` — no writer, no reader,
      and no `*_REL` constant.
- [ ] `test_forbidden_dirs_absent` passes in an interactive session with hooks
      active, not only under CI.
- [ ] After `ai-eng install` into a fixture root,
      `.ai-engineering/runtime/VERSION` exists and holds the installed version,
      and `.ai-engineering/state/runtime/` does not exist.
- [ ] A test asserts the update path reaches the `VERSION` stamp when an apply
      mutates files, so a later refactor of `_finalize_hooks_manifest` cannot
      silently reopen D-200-05's zero-window guarantee.
- [ ] The hook observability library resolves `frameworkVersion` from the new
      `VERSION` location and still falls back to importlib metadata when the
      file is absent — the spec-190 D-190-01 order is unchanged.
- [ ] `ai-eng doctor` reports the `opa-bundle-signature` probe passing after an
      install that writes the bundle to its new path.
- [ ] The SessionEnd rotation reaper removes a pre-existing
      `.ai-engineering/state/runtime/` directory, covered by a test that seeds
      one.
- [ ] CHANGELOG records the `*_REL` constant removals as a breaking change.
- [ ] Every edited hook script is byte-identical to its counterpart under
      `src/ai_engineering/templates/.ai-engineering/scripts/`.
- [ ] The hooks manifest is regenerated and `ai-eng doctor` reports hook
      integrity passing.
- [ ] The full unit suite passes locally with hooks active and OpenCode
      installed — the exact configuration that produced nineteen failures.
