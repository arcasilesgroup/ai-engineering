---
execution_route:
  version: 1
  spec: spec-158
  executor: build
  automation: assisted
  concern_count: 2
  estimated_files: 9
  reason: >
    Two tightly-related public-install concerns. (A) settings.json hook-command
    migrator: pure-core module + IO wrapper, wired into update(), surfaced in
    UpdateResult/summary, two test files. (B) operator-anonymity hardening:
    genericize 3 transcript_usage.py docstring leaks (canonical + template),
    regenerate hooks-manifest, add a name-agnostic operator-path gate. ~9 files,
    one stack (python). 2 concerns / 9 files stays below the >=3-concern or
    >=10-file autopilot threshold.
  safe_next_command: "/ai-build"
spec: spec-158
title: Public-install hardening — hook-command migration + operator-anonymity gate
status: approved
pipeline: standard
---

# spec-158 — Execution Plan

## Architecture

**Pattern: Hexagonal (§10.8) — pure core + IO shell.**

The migrator splits into a **pure planner** (parse settings dict -> list of exact
`(old_command, new_command)` rewrites + a skipped list; no IO) and an **IO
wrapper** (`migrate_hook_commands(target, *, dry_run)` — reads
`.claude/settings.json`, guards on `run-hook.sh` presence, applies rewrites via
**literal `json.dumps` string replacement on the raw file text** for
minimum-diff, backs up + writes only when `not dry_run`, returns a
`HookMigrationReport`).

Critical boundary decision (from updater evidence): `.claude/settings.json` is
ownership-**denied** (`control_plane.py:121`, `FileChange` -> `skip-denied`). The
migrator therefore does **NOT** flow through the `FileChange`/reconciler path —
it is a **framework-owned field migration** (spec-158 D-158-04) called directly
from `update()`, attached to `UpdateResult.hook_migration`, surfaced in
`to_dict()` and the human summary. This bypasses the protected-file overwrite
block while leaving whole-file ownership protection intact.

**Minimum-diff mechanism (D-158-06):** for each exact-shape command, compute
`old_literal = json.dumps(old_cmd)` and `new_literal = json.dumps(new_cmd)`
(both include surrounding quotes + identical JSON escaping to what the file
already contains) and do `raw = raw.replace(old_literal, new_literal)`. Only
command string values change; matchers, timeouts, key order, whitespace, and
`permissions.deny` survive byte-for-byte. A duplicated command (same script in
two events) is rewritten in all positions (correct). Re-validate with
`json.loads` after; if a literal is not found in raw (escaping mismatch), that
command is reported `skipped`, never corrupted.

**Detection (D-158-02):**
- Exact-shape regex over a command:
  `^python3 "\$CLAUDE_PROJECT_DIR/\.ai-engineering/scripts/hooks/(?P<script>[^"]+\.py)"(?P<args>.*)$`
  -> rewrite to
  `bash "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh" "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<script>"<args>`.
- Already routed through `run-hook.sh` -> not matched -> no rewrite (idempotent;
  not counted as skipped-for-review).
- Command referencing the framework hooks dir but NOT matching the exact shape
  (custom interpreter, absolute path, extra flags, wrapper) -> `skipped`
  (reported for manual review).
- Command not referencing the framework hooks dir -> ignored (user's own).

## Phases

### Phase 1 — Pure planner core (TDD)

- [ ] T-1 — RED: pure planner tests
  - Agent: build
  - Files: `tests/unit/updater/test_hook_command_migration.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (prose): create the test module (house style: plain `tmp_path`, no
    fixtures needed for the pure fn). Cover `plan_command_rewrites(settings: dict)`:
    (a) exact `python3 ".../observe.py"` -> `bash ".../run-hook.sh" ".../observe.py"`;
    (b) trailing args preserved (`... .py" --flag` -> `...run-hook.sh" "....py" --flag`);
    (c) duplicate command in two events -> both in rewrites;
    (d) already-`run-hook.sh` command -> 0 rewrites, 0 skipped;
    (e) non-canonical framework-dir command (`python /abs/x.py`, or `python3 '...'`
    single-quote, or extra interpreter flag) -> 0 rewrites, 1 skipped;
    (f) non-framework command (`echo hi`) -> ignored (0/0);
    (g) missing/empty `hooks` block -> (0/0). Import
    `from ai_engineering.updater.hook_command_migration import plan_command_rewrites`.
  - Gate: `.venv/bin/python -m pytest tests/unit/updater/test_hook_command_migration.py -q` -> fails (ModuleNotFoundError).

- [ ] T-2 — GREEN: planner module
  - Agent: build
  - Files: `src/ai_engineering/updater/hook_command_migration.py` (new)
  - Principles applied: §10.8 Hexagonal, §10.1 KISS
  - Patch (prose): module constants
    `_HOOKS_PREFIX = "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/"`,
    `_RUN_HOOK = _HOOKS_PREFIX + "_lib/run-hook.sh"`, compiled regex
    `_PY_CMD = re.compile(r'^python3 "\$CLAUDE_PROJECT_DIR/\.ai-engineering/scripts/hooks/(?P<script>[^"]+\.py)"(?P<args>.*)$')`.
    `def plan_command_rewrites(settings: Mapping) -> tuple[list[tuple[str, str]], list[str]]`:
    walk `settings.get("hooks", {})` -> each event -> list of entries -> each
    `entry.get("hooks", [])` -> each hook dict's `command`. For each command:
    skip if it already contains `_lib/run-hook.sh`; elif `_PY_CMD` matches ->
    append `(old, f'bash "{_RUN_HOOK}" "{_HOOKS_PREFIX}{m["script"]}"{m["args"]}')`
    to rewrites; elif command references `_HOOKS_PREFIX` -> append to skipped;
    else ignore. De-dupe rewrites preserving order. Return `(rewrites, skipped)`.
  - Gate: T-1 tests pass.

### Phase 2 — IO wrapper (TDD)

- [ ] T-3 — RED: IO wrapper + report tests
  - Agent: build
  - Files: `tests/unit/updater/test_hook_command_migration.py` (extend)
  - Principles applied: §10.5 TDD
  - Patch (prose): add a `_write_settings(claude_dir, data)` helper and a
    `_seed_run_hook(target)` helper (touch
    `.ai-engineering/scripts/hooks/_lib/run-hook.sh`). Cover
    `migrate_hook_commands(target, *, dry_run)`:
    (a) absent `.claude/settings.json` -> `HookMigrationReport(migrated=[], skipped=[], backup_path=None, applied=False)`, nothing written;
    (b) `run-hook.sh` absent -> rewrites NOT applied, report lists the candidates as `skipped` with reason, file unchanged (AC8);
    (c) `dry_run=True` with candidates + run-hook.sh present -> report.migrated populated, file on disk UNCHANGED, backup_path None;
    (d) `dry_run=False` -> file rewritten to `run-hook.sh` form, a backup file matching `settings.json.bak-*` exists, `permissions.deny` + matchers + timeouts preserved, JSON valid;
    (e) minimum-diff: raw text equals the original except the rewritten command literals (assert non-command bytes unchanged);
    (f) idempotent: second `migrate_hook_commands(dry_run=False)` -> `migrated == []`, file content stable.
  - Gate: fails (function/dataclass absent).

- [ ] T-4 — GREEN: IO wrapper + report dataclass
  - Agent: build
  - Files: `src/ai_engineering/updater/hook_command_migration.py` (extend)
  - Principles applied: §10.8 Hexagonal, §10.5 TDD, §10.7 Clean Code
  - Patch (prose): `@dataclass HookMigrationReport` with
    `migrated: list[str]`, `skipped: list[str]`, `backup_path: Path | None`,
    `applied: bool`, plus `count`/`to_dict()` helpers.
    `def migrate_hook_commands(target: Path, *, dry_run: bool) -> HookMigrationReport`:
    resolve `settings = target/".claude"/"settings.json"`; if not file -> empty
    report. `raw = settings.read_text()`, `data = json.loads(raw)`
    (on `JSONDecodeError` -> empty report, do not touch). `rewrites, skipped =
    plan_command_rewrites(data)`. If rewrites and
    `not (target/".ai-engineering"/"scripts"/"hooks"/"_lib"/"run-hook.sh").is_file()`
    -> move rewrite scripts into `skipped` (reason: resolver-absent), `rewrites=[]`
    (AC8). `migrated = [old for old,_ in rewrites]`. If `dry_run` or not rewrites
    -> return report (no write). Else: `new_raw = raw`; for `old,new` in rewrites:
    `new_raw = new_raw.replace(json.dumps(old), json.dumps(new))`; if a literal
    absent -> drop from migrated, add to skipped. `json.loads(new_raw)` (validate;
    on failure -> return report unwritten + skipped). Backup:
    `bak = settings.with_name(f"settings.json.bak-{datetime.now(UTC):%Y%m%dT%H%M%SZ}")`,
    `shutil.copy2(settings, bak)`. Write `new_raw` (atomic: temp + `os.replace`).
    Return report with `backup_path=bak`, `applied=True`.
  - Gate: T-3 tests pass.

### Phase 3 — Wire into updater + result + summary

- [ ] T-5 — UpdateResult carries the migration report
  - Agent: build
  - Files: `src/ai_engineering/updater/service.py:117-168`
  - Principles applied: §10.3 SOLID (single result aggregate)
  - Patch (deterministic):
    ```diff
    @@ class UpdateResult
         dry_run: bool
         changes: list[FileChange] = field(default_factory=list)
    +    hook_migration: "HookMigrationReport | None" = None
    @@ def to_dict(self) -> dict[str, object]:
                 "changes": [change.to_dict(dry_run=self.dry_run) for change in self.changes],
    +            "hook_migration": (
    +                self.hook_migration.to_dict() if self.hook_migration is not None else None
    +            ),
             }
    ```
    Plus a top-of-file `from ai_engineering.updater.hook_command_migration import HookMigrationReport` (TYPE_CHECKING or runtime import).
  - Gate: a unit assertion that `UpdateResult(dry_run=True).to_dict()["hook_migration"] is None`.

- [ ] T-6 — update() runs the migrator (both branches)
  - Agent: build
  - Files: `src/ai_engineering/updater/service.py:465-482`
  - Principles applied: §10.4 DRY (compute once, attach once)
  - Patch (deterministic):
    ```diff
         adapter = _UpdateAdapter(target, dry_run=dry_run)
         run = ResourceReconciler().run(adapter, target, preview=dry_run)  # ty:ignore[invalid-argument-type]

    +    # spec-158 D-158-03/04: the resolver wiring inside the ownership-protected
    +    # .claude/settings.json is a framework-owned FIELD migration — it never
    +    # flows through the (denied) FileChange path. Compute always (dry-run
    +    # visibility); write + backup only on apply.
    +    from ai_engineering.updater.hook_command_migration import migrate_hook_commands
    +
    +    hook_migration = migrate_hook_commands(target, dry_run=dry_run)
    +
         if dry_run:
             payload = _UpdateAdapter._coerce_plan_payload(run.plan.payload)
    -        return payload.result
    +        payload.result.hook_migration = hook_migration
    +        return payload.result
    @@
         payload = _UpdateAdapter._coerce_apply_payload(run.apply_result.payload)
    -    return payload.result
    +    payload.result.hook_migration = hook_migration
    +    return payload.result
    ```
  - Gate: integration tests T-7.

- [ ] T-7 — Integration: dry-run report + apply rewrite + regression shape
  - Agent: build
  - Files: `tests/integration/test_updater.py` (extend, new `TestHookCommandMigration`)
  - Principles applied: §10.5 TDD
  - Patch (prose): using the `installed_project` fixture (full `.ai-engineering/`
    + `.claude/settings.json`): (AC5) seed a legacy `python3 ".../observe.py"`
    command into `.claude/settings.json`, `update(dry_run=True)` ->
    `result.hook_migration.migrated` non-empty, file unchanged on disk;
    (AC1/AC7) `update(dry_run=False)` -> settings command rewritten to
    `run-hook.sh` form, backup file present, JSON valid; (AC3) second
    `update(dry_run=False)` -> `hook_migration.migrated == []`; (AC2/AC6) a
    user-added hook + a `permissions.deny` entry survive the apply.
  - Gate: `.venv/bin/python -m pytest tests/integration/test_updater.py -q`.

- [ ] T-8 — Surface `migrate-hooks: N` in the update summary
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/core.py` (update_cmd summary render)
  - Principles applied: §10.7 Clean Code (visible, not silent)
  - Patch (prose): in the `update_cmd` human-summary block (where applied/denied
    counts print), add a line when `result.hook_migration` has content:
    `migrate-hooks: <len(migrated)> migrated, <len(skipped)> skipped` (preview vs
    applied verb per `result.dry_run`); list skipped command(s) as a manual-review
    hint. JSON path already carries it via `to_dict()` (T-5). Locate the exact
    render site first (`grep -n "denied\|applied\|update" core.py` around update_cmd).
  - Gate: `tests/integration/test_cli_command_modules.py` update assertions stay green; add one asserting the migrate line renders (human) and is absent under `--json`.

### Phase 5 — Operator-anonymity hardening (concern B, TDD; parallelizable with Phases 1-3)

- [ ] T-10 — RED: name-agnostic operator-path gate
  - Agent: build
  - Files: `tests/unit/test_no_operator_paths.py` (new)
  - Principles applied: §10.5 TDD, Hard Rule 4
  - Patch (prose): model on `test_no_forbidden_substrings.py`. Scan shipped
    surfaces relative to repo root: `src/ai_engineering/**/*` (all files incl.
    `.py/.md/.json/.sh` — templates ship verbatim), `.ai-engineering/scripts/**/*`,
    `docs/**/*.md`, root `*.md` + `CONSTITUTION.md`. Regex
    `re.compile(r"[/\\](Users|home)[/\\]([A-Za-z][A-Za-z0-9_.-]*)")`; for each
    match, FAIL if `group(2).lower()` not in
    `GENERIC = {"user","users","you","youruser","runner","linuxbrew","root","test","example","name","project","app","ci","build","home","someone"}`.
    Self-exclude this test file. Add explicit unit asserts: a planted string
    `"/Users/plantedoperator/x"` is flagged by the matcher fn; `/home/linuxbrew`
    and `/Users/you` are NOT. Skip binary files (decode errors -> skip).
  - Gate: `.venv/bin/python -m pytest tests/unit/test_no_operator_paths.py -q` ->
    FAILS, flagging the 3 `transcript_usage.py` `soydachi` lines (proves detection).

- [ ] T-11 — GREEN: genericize leaks + sync template + regen manifest
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/transcript_usage.py:9`,
    `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/transcript_usage.py`,
    `.ai-engineering/state/hooks-manifest.json`
  - Principles applied: Hard Rule 4, §10.4 DRY
  - Patch (prose): in canonical `transcript_usage.py:9` replace
    `` ``/Users/soydachi/.claude/projects/-Users-<...>-ai-engineering/<session-id>.jsonl`` ``
    with a generic placeholder consistent with line 44's
    `${HOME}/.claude/projects/<slug>/<session-id>.jsonl` style (no operator name).
    Then `cp` canonical `transcript_usage.py` -> the template path so both are
    byte-identical (kills the `:67` drift too). Then regenerate the hooks manifest:
    `.venv/bin/python .ai-engineering/scripts/regenerate-hooks-manifest.py` (the
    canonical _lib byte change updates its sha256) and commit the manifest.
  - Gate: T-10 gate now GREEN; `git grep -nI soydachi` returns 0;
    `.venv/bin/python -m pytest tests/unit/hooks/test_transcript_usage.py
    tests/unit/test_session_bootstrap_template_parity.py -q` (and any
    transcript_usage parity/manifest test) green;
    `.venv/bin/python -m ai_engineering.cli internal ...` not needed — verify
    manifest via `ai-eng audit verify` or the hooks-manifest check test.

### Phase 4 — Quality gate

- [ ] T-9 — Full gate
  - Agent: verify
  - Files: —
  - Principles applied: §10.5, Hard Rule 5
  - Patch: none.
  - Gate: `.venv/bin/python -m pytest tests/unit/updater tests/integration/test_updater.py tests/integration/test_cli_command_modules.py tests/unit/test_no_operator_paths.py tests/unit/hooks/test_transcript_usage.py -q` green; `ruff check` + `ruff format --check` clean on changed files; `ty check` clean on the new module + service.py; **`hooks-manifest.json` regenerated + consistent** (canonical `transcript_usage.py` bytes changed → AC9); `git grep -nI soydachi` == 0. Then full suite `-n auto`.

## Gate Criteria (maps to spec Acceptance)

- AC1 -> T-7 apply rewrite assertion.
- AC2/AC6 -> T-7 user-hook + deny preserved; T-3(d/e) minimum-diff.
- AC3 -> T-3(f) + T-7 second-apply idempotency.
- AC4 -> T-1(e) + T-3(b) skip-report.
- AC5 -> T-3(c) dry-run no-write + report; T-8 summary line.
- AC7 -> T-7 regression (resolver form after apply).
- AC8 -> T-3(b) run-hook.sh absent -> skip.
- AC9 -> T-9 full gate + hooks-manifest REGEN (transcript_usage bytes changed).
- AC10 -> T-11 genericize + template byte-sync; `git grep soydachi` == 0.
- AC11 -> T-10 name-agnostic gate (positive plant caught + linuxbrew/you pass).

## Risks during build

- **JSON-escape mismatch** between `json.dumps(old)` and the on-disk literal ->
  handled: literal-not-found drops to `skipped`, never corrupts (T-3 covers).
- **`datetime` import** — service.py / migration module are Python (not a
  Workflow script); `datetime.now(UTC)` is fine here.
- **core.py render-site drift** — T-8 says locate the exact site first; do not
  guess the line.

## safe_next_command

`/ai-build`
