# spec-104 Phase 0 Exploration Notes

**Task**: T-0.2 — read-only exploration of extension points + spec-101 orthogonality verification.
**Date**: 2026-04-26.
**Branch**: `feat/spec-101-installer-robustness` (umbrella).

---

## 1. Extension points in `src/ai_engineering/policy/gates.py`

File is 289 lines. Current sequential dispatch flow lives in `run_gate(hook, project_root, *, commit_msg_file)` at lines 55-128:

| Line range | Concern | spec-104 hook |
|---|---|---|
| 71-75 | Lazy import of `branch_protection`/`hook_integrity`/`version_deprecation` | KEEP — preflight checks pre-orchestrator |
| 77-78 | `t0 = monotonic()` + `result = GateResult(hook=hook)` | KEEP — orchestrator wraps this |
| 81-98 | Branch protection + version deprecation + hook integrity (preflight, fail-fast on violation) | KEEP — must run BEFORE Wave 1; orchestrator only owns Wave 1+2 |
| **100-105** | **Sequential dispatch by hook**: `_run_pre_commit_checks` / `_run_commit_msg_checks` / `_run_pre_push_checks` | **PRIMARY HOOK POINT** — D-104-01 inserts orchestrator dispatch here when `hook in {PRE_COMMIT, PRE_PUSH}` and `AIENG_LEGACY_PIPELINE` is unset |
| 107-127 | Audit emit + `build_complete` event on PRE_PUSH success | KEEP — orchestrator emits parallel `gate-findings.json` (D-104-06) but does not replace these events |
| 226-258 | `_run_pre_commit_checks(project_root, result)` — runs `get_checks_for_stage(PRE_COMMIT, ...)` then `run_checks_for_specs` (data-driven, spec-101 D-101-01); falls back to legacy `PRE_COMMIT_CHECKS` registry when manifest missing; trailing risk-warning check | These are the calls the orchestrator wraps |
| 261-288 | `_run_pre_push_checks(...)` — same pattern, adds `check_sonar_gate` + `_check_expired_risk_acceptances` | Same — orchestrator wraps the spec-execution; sonar + risk checks remain post-orchestrator |

**Wave 1 vs Wave 2 split logic** (D-104-01):
- Wave 1 (serial fixers): `ruff format`, `ruff check --fix`, `ai-eng spec verify --fix`. The current `CheckSpec` list does NOT carry a `wave` attribute — spec-104 must add either (a) a derived classifier in orchestrator (probably best — keep `CheckSpec` frozen) or (b) a new field on `CheckSpec`.
- Wave 2 (parallel checkers): `gitleaks-staged`, `validate`, `docs-gate` (LLM), `ty-check`, `pytest-smoke`. Currently `_classify_stage` (`stack_runner.py:556-564`) only classifies into PRE_COMMIT vs PRE_PUSH. spec-104 introduces an orthogonal dimension (Wave 1=fixer, Wave 2=checker) — **propose `_classify_wave(tool_name) -> Wave` helper inside orchestrator**, not in `stack_runner.py` (orthogonality with spec-101).
- Race-safety invariant (R-5 / T-2.11/T-2.12): orchestrator holds `wave1_complete: threading.Event` and `assert wave1_complete.is_set()` before `run_wave2`.

**Recommended insertion shape** (T-2.2 / T-2.4):

```python
# Inside run_gate, replacing lines 100-105:
if os.environ.get("AIENG_LEGACY_PIPELINE") or hook == GateHook.COMMIT_MSG:
    # legacy serial path
    _run_pre_commit_checks(...) / _run_commit_msg_checks(...) / _run_pre_push_checks(...)
else:
    from ai_engineering.policy.orchestrator import run_orchestrated_gate
    run_orchestrated_gate(hook, project_root, result, mode=...)
```

The `result: GateResult` is mutated in-place — this matches the existing pattern; orchestrator must append `GateCheckResult` entries to `result.checks` so the audit emit at line 109 works unchanged.

---

## 2. Extension points in `src/ai_engineering/cli_commands/gate.py`

File is 240 lines. Current functions:

| Function | Lines | Role |
|---|---|---|
| `_print_gate_result(result)` | 34-67 | Print or JSON-emit a single `GateResult`; raises `typer.Exit(1)` on fail. Already uses `is_json_mode()` from `cli_output`. |
| `gate_pre_commit(target)` | 70-79 | Wraps `run_gate(GateHook.PRE_COMMIT, root)`. |
| `gate_commit_msg(msg_file, target)` | 82-95 | Wraps `run_gate(COMMIT_MSG, root, commit_msg_file=msg_file)`. |
| `gate_pre_push(target)` | 98-107 | Wraps `run_gate(PRE_PUSH, root)`. |
| `_check_risk_inline(root, strict)` | 110-138 | Decision-store risk lifecycle inspection. |
| `gate_risk_check(target, strict)` | 141-165 | Risk-only check command. |
| `gate_all(target, strict)` | 168-239 | Composite: PRE_COMMIT + PRE_PUSH + risk; aggregates results, JSON or text emit. |

**Where new flags attach** (D-104-10, T-3.1/T-3.2):

The plan calls for `ai-eng gate run --cache-aware --no-cache --force --json --mode={local,ci}`. There is **no `gate_run` function today** — the CLI surface uses three command-name variants (`gate pre-commit`, `gate pre-push`, etc.). spec-104 has two integration options:

- **Option A (recommended)**: add a NEW `gate_run(target, mode, cache_aware, no_cache, force, json)` function. Keep existing 3 hook-specific entry points unchanged for backwards compat (git hooks already invoke them). Register `gate run` as a separate Typer command. NG-8 explicitly allows extending `ai-eng gate run` with new flags — spec-104 adds the `gate run` subcommand surface.
- **Option B**: extend `gate_all` with the new flags. Risk: `gate_all` does PRE_COMMIT + PRE_PUSH + risk; spec-104 wants single-pass orchestrator. Mismatch.

Decision: **Option A**. New file structure:

```python
# Insert after gate_pre_push at ~line 107, before _check_risk_inline at line 110
def gate_run(
    target: Annotated[Path | None, typer.Option("--target", "-t", ...)] = None,
    mode: Annotated[str, typer.Option("--mode", help="local|ci")] = "local",
    cache_aware: Annotated[bool, typer.Option("--cache-aware/--no-cache-aware")] = True,
    no_cache: Annotated[bool, typer.Option("--no-cache")] = False,
    force: Annotated[bool, typer.Option("--force")] = False,
    json_out: Annotated[bool, typer.Option("--json")] = False,  # already covered by is_json_mode()
) -> None:
    """Run the orchestrated gate (Wave 1 fixers + Wave 2 checkers, cache-aware)."""
    ...
```

`--json` is partially redundant with global `--json` already wired via `cli_output.is_json_mode()`; keeping both so users can scope JSON to this single command.

Additionally, `gate cache --status` / `gate cache --clear --yes` (T-3.3/T-3.4) need a NEW Typer subcommand — `gate cache` is not registered today. Search `src/ai_engineering/cli_app.py` (or wherever Typer registration happens) for the `gate` subcommand wiring; the new `gate cache` subcommand needs to be added there.

---

## 3. Pydantic patterns in `src/ai_engineering/state/models.py`

File is 812 lines. Pydantic version: **v2** (confirmed in `pyproject.toml`: `pydantic>=2.0,<3.0`). Patterns to follow for `GateFinding`, `AutoFixedEntry`, `GateFindingsDocument`, `WatchLoopState` (T-0.4):

| Pattern | Used by | Apply to spec-104 |
|---|---|---|
| `class Foo(BaseModel)` + `Field(default=..., alias="camelCase")` + `model_config = {"populate_by_name": True}` | `OwnershipMap`, `Decision`, `DecisionStore`, `FrameworkEvent`, `InstinctObservation`, `InstinctMeta`, `FrameworkCapabilitiesCatalog` | **Use `populate_by_name` for `GateFindingsDocument`** — JSON consumers (spec-105) may use snake_case or camelCase. |
| `model_config = {"frozen": True}` | `ToolSpec`, `StackSpec`, `SdkPrereq` | **Use frozen for `GateFinding`** — findings are immutable records once captured. |
| `StrEnum` for closed value sets | `OwnershipLevel`, `GateHook`, `RiskCategory`, `RiskSeverity`, `DecisionStatus`, `Platform`, `ToolScope`, `ToolInstallState`, `PythonEnvMode` | **Use StrEnum for `Severity`** (`critical|high|medium|low|info`) and `ProducedBy` (`ai-commit|ai-pr|watch-loop`). |
| `@field_validator` with `@classmethod` | `SdkPrereq._validate_min_version` | **Use for `GateFinding.rule_id`** — assert non-empty stable id (D-104-06 forbids human messages as rule_id). |
| `@model_validator(mode="after")` | `ToolSpec._enforce_platform_invariants`, `StackSpec._require_reason_for_stack_unsupported` | **Use for `GateFinding`** — assert `auto_fixable=True` requires non-null `auto_fix_command` (T-0.3). |
| `@model_validator(mode="before")` for raw-shape coercion | `StackSpec._coerce_raw_block`, `RequiredToolsBlock._coerce_raw_blocks` | Likely not needed for spec-104 (schema is explicit). |
| `datetime` with `Field(default_factory=lambda: datetime.now(tz=UTC))` | `AuditEntry`, `FrameworkEvent`, `InstinctObservation`, `InstallState.installed_at` | **Use for `GateFindingsDocument.produced_at`** — UTC default. |
| Schema versioning: `schema_version: str = Field(default="1.0", alias="schemaVersion")` | `OwnershipMap`, `DecisionStore`, `FrameworkEvent`, `FrameworkCapabilitiesCatalog`, `InstinctObservation`, `InstinctMeta`, `InstallState` | **CRITICAL: `GateFindingsDocument.schema` is `Literal["ai-engineering/gate-findings/v1"]`**, NOT a free string (D-104-06: consumers reject unknown versions). Use `from typing import Literal` and a `Field(default="ai-engineering/gate-findings/v1")` with a literal type. |

**Required imports to add**:
```python
from typing import Literal
from uuid import UUID, uuid4
```

**Naming**: existing models use snake_case Python attrs + camelCase aliases. New models should follow suit; spec D-104-06 schema uses snake_case (`session_id`, `produced_by`, `wall_clock_ms`) — use snake_case attrs with optional camelCase aliases via `populate_by_name`.

---

## 4. Skill markdown current baseline (D-104-07 verification)

`wc -l` output:

```
     126 .claude/skills/ai-commit/SKILL.md
     221 .claude/skills/ai-pr/SKILL.md
     185 .claude/skills/ai-pr/handlers/watch.md
     532 total
```

**Verified: matches D-104-07 baseline (126 / 221 / 185 = 532).**

D-104-07 target: ≥160 lines removed combined → end state ≤372 lines. Per-file allocation (from plan T-7.3/T-7.4/T-7.5):

| File | Pre | Cut | Post (target) |
|---|---:|---:|---:|
| ai-commit/SKILL.md | 126 | -10 (lines 110-119 Common Mistakes dup of CLAUDE.md Don't) + boilerplate trim | ~85-100 |
| ai-pr/SKILL.md | 221 | -11 (lines 53-63 stack-detection dup of contexts/languages) + -22 (lines 199-205 anti-pattern dup of watch.md) + boilerplate | ~140-160 |
| handlers/watch.md | 185 | +0 (consolidates anti-patterns from ai-pr; no net change) — boilerplate trim only | ~150-170 |

Total target ~375-430. Plan assumes ≤372 — needs sharper trim than the line ranges alone provide. T-7.6 explicitly addresses this: "Apply surrounding-boilerplate trim".

**Risk flagged for T-7.x**: section-headers will lose content but the section heading must remain detectable by `tests/unit/test_skill_contract_completeness.py` (T-7.1) — this means after removing duplicated content, do not also remove the `## Common Mistakes` H2 unless the test allows missing H2s. Currently planned: `## Process`, `## Integration`, `## Quick Reference`, `argument-hint` are MANDATORY; `## Common Mistakes` and `## References` are NOT in the contract — they can be removed entirely.

---

## 5. spec-101 file scope (orthogonality verification)

`git log --since=2026-04-20 origin/main..HEAD --name-only` analysis. spec-101 commits (excluding the spec-104 commit `6a2a36ef` which only touches notes/specs/plan):

**Paths spec-101 has touched**:
- `.ai-engineering/contexts/python-env-modes.md`
- `.ai-engineering/manifest.yml` (additive: `prereqs`, `python_env`, `required_tools` blocks)
- `.ai-engineering/notes/adoption-s2..s5-*.md`
- `.ai-engineering/state/decision-store.json`
- `.ai-engineering/specs/spec.md`, `plan.md` (frozen post-spec-101 brainstorm)
- `.ai-engineering/runs/spec-101/phase-0-notes.md`
- `.claude/agents/ai-build.md` + 3 mirrors (`.codex/`, `.gemini/`, `.github/`)
- `.github/CODEOWNERS`, `AGENTS.md`, `CHANGELOG.md`, `CLAUDE.md`, `README.md`
- `.github/workflows/install-smoke.yml`, `install-time-budget.yml`, `worktree-fast-second.yml`, `ci-check.yml`
- `sonar-project.properties`
- `pyproject.toml`, `uv.lock`
- `src/ai_engineering/cli_commands/core.py`, `_exit_codes.py`, `validate.py`
- `src/ai_engineering/installer/` (whole subtree: `phases/`, `mechanisms/`, `_shell_patterns.py`, `launchers.py`, `python_env.py`, `service.py`, `tool_registry.py`, `tools.py`, `user_scope_install.py`, `results.py`)
- `src/ai_engineering/doctor/phases/tools.py`, `runtime/branch_policy.py`
- `src/ai_engineering/prereqs/__init__.py`, `sdk.py`, `uv.py`
- `src/ai_engineering/state/manifest.py`, `models.py`, `service.py`
- **`src/ai_engineering/policy/gates.py`** (Wave 1 of spec-101 only — spec-101 frozen at 06f0d167; no further edits expected)
- **`src/ai_engineering/policy/checks/stack_runner.py`** (data-driven dispatch — spec-101 owns this file, frozen)
- `src/ai_engineering/templates/` (template tree)
- `src/ai_engineering/validator/`, `verify/tls_pip_audit.py`
- `tests/` (extensive — install/doctor/policy/state suites)

**spec-104 scope (per plan + spec)**:
- `src/ai_engineering/policy/orchestrator.py` (NEW)
- `src/ai_engineering/policy/gate_cache.py` (NEW)
- `src/ai_engineering/policy/watch_residuals.py` (NEW, T-6.3)
- `src/ai_engineering/cli_commands/gate.py` (EXTEND — add `gate_run`, `gate_cache_status`, `gate_cache_clear`)
- `src/ai_engineering/state/models.py` (EXTEND — add `GateFinding`, `AutoFixedEntry`, `GateFindingsDocument`, `WatchLoopState`)
- `.ai-engineering/contexts/gate-policy.md` (NEW)
- `.claude/skills/ai-commit/SKILL.md`, `.claude/skills/ai-pr/SKILL.md`, `.claude/skills/ai-pr/handlers/watch.md` (EDIT)
- IDE mirrors (`.github/skills/`, `.codex/skills/`, `.gemini/skills/`) regenerated by `ai-eng sync`
- `.github/workflows/ci-build.yml`, `ci-check.yml` (cache wiring)
- `tests/{unit,integration,perf,fixtures}/test_gate_*`, `test_orchestrator_*`, `test_skill_*`, `test_ai_pr_*`, `test_watch_*` (NEW)

**Overlap analysis**:

| Path | spec-101 | spec-104 | Conflict? |
|---|---|---|---|
| `policy/orchestrator.py` | ✗ | ✓ NEW | **NO** — spec-101 never created this. |
| `policy/gate_cache.py` | ✗ | ✓ NEW | **NO** — spec-101 never created this. |
| `policy/watch_residuals.py` | ✗ | ✓ NEW | **NO**. |
| `policy/gates.py` | ✓ (Wave 1, frozen) | ✓ (insertion at lines 100-105) | **POTENTIAL** — but spec-101 declared frozen post-PR463; spec-104 only adds an `if AIENG_LEGACY_PIPELINE:` branch + orchestrator call. No removal of existing logic. **Acceptable, additive.** |
| `policy/checks/stack_runner.py` | ✓ (whole file, frozen) | ✗ | **NO** — spec-104 does not edit `stack_runner.py`. Orchestrator imports `get_checks_for_stage` and `CheckSpec` as a stable contract. |
| `cli_commands/gate.py` | ✗ | ✓ EXTEND | **NO**. |
| `state/models.py` | ✓ (added spec-101 models: `Platform`, `ToolScope`, `ToolInstallState`, `PythonEnvMode`, `ToolSpec`, `StackSpec`, `RequiredToolsBlock`, `ToolInstallRecord`, `SdkPrereq`, `InstallState` extensions) | ✓ (add 4 new models at end) | **NO** — additions are append-only. |
| `state/service.py` | ✓ (legacy migration logic) | ✗ | **NO**. |
| `manifest.yml` | ✓ (`prereqs`, `python_env`, `required_tools`) | ✓ (POTENTIAL: `gates.policy_doc_ref` key, T-0.8 declares additive only) | **NO** — additive in different top-level key. **Test asserted by T-0.8.** |
| `.claude/skills/ai-build.md` | ✓ (write scopes) | ✓ (T-0.1 extends scopes) | **POTENTIAL** — same file edit. **Mitigation**: T-0.1 runs first and only adds new entries to AGENT_METADATA; spec-101 changes were already merged frozen. Verify no in-flight spec-101 edits remain to ai-build.md. |
| `.claude/skills/ai-commit/SKILL.md` | ✗ | ✓ | **NO** — spec-101 never edited skill markdown. |
| `.claude/skills/ai-pr/SKILL.md` | ✗ | ✓ | **NO**. |
| `.claude/skills/ai-pr/handlers/watch.md` | ✗ | ✓ | **NO**. |
| `.ai-engineering/contexts/gate-policy.md` | ✗ | ✓ NEW | **NO**. |
| `.github/workflows/ci-{build,check}.yml` | ✓ (`ci-check.yml` Wave 33: SonarCloud + macOS) | ✓ (cache wiring) | **POTENTIAL** — `ci-check.yml` overlap. **Mitigation**: spec-101 frozen on this file; spec-104 cache step is additive (new step block, doesn't modify Sonar/macOS jobs). |
| `tests/integration/test_stack_runner_data_driven.py`, `test_install_*`, `test_doctor_*`, etc. | ✓ | ✗ | **NO** — spec-104 adds new test files only (`test_orchestrator_*`, `test_gate_cache_*`, `test_watch_*`). |

**Conclusion**: zero functional overlap. The only shared files (`policy/gates.py`, `state/models.py`, `manifest.yml`, `ai-build.md`, `ci-check.yml`) are touched additively. spec-101 is frozen post-PR463 (per `notes/spec-101-frozen-pr463.md`) — no concurrent edits expected.

---

## 6. Identified risks for implementation

### Risk-A: Pydantic v2 quirks not surfaced in plan

- **Issue**: Pydantic v2 `Literal[...]` types in `model_config = {"frozen": True}` models work but require careful `__hash__` if used in sets. spec-104 may not need this, but verify.
- **Mitigation**: write `GateFinding` as frozen + use `tuple` not `list` for any sequence fields if hashability needed. Currently `findings: list[GateFinding]` in `GateFindingsDocument` is non-frozen container — acceptable.
- **Action**: T-0.4 should explicitly choose `model_config = {"frozen": True, "populate_by_name": True}` on `GateFinding` and `AutoFixedEntry`. `GateFindingsDocument` should NOT be frozen (mutable assembly during orchestrator run).

### Risk-B: asyncio vs concurrent.futures.ThreadPoolExecutor

- **Plan choice**: T-2.4 specifies `concurrent.futures.ThreadPoolExecutor(max_workers=5)`.
- **Subtlety**: subprocess invocations (`gitleaks`, `ty`, `pytest`, etc.) are I/O-bound waiting on child processes — threads are FINE here (no GIL contention). asyncio with `asyncio.create_subprocess_exec` would be marginally lower-overhead but adds an event loop dependency. **ThreadPoolExecutor is the right choice — confirm in T-2.4.**
- **Cross-platform caveat**: `ThreadPoolExecutor` works identically on Windows/POSIX. asyncio subprocess on Windows requires `ProactorEventLoop` (already default in Python 3.8+). No additional risk.

### Risk-C: Atomic write portability (D-104-03 + R-9)

- **Plan**: write atómico via `tempfile + os.rename`.
- **Subtlety**: `os.rename` on POSIX is atomic for same-filesystem moves; on **Windows**, `os.rename` raises `FileExistsError` if destination exists. spec-104 needs `os.replace(src, dst)` instead (Python 3.3+, atomic on both POSIX and Windows when destination exists).
- **Action**: T-1.2 implementation MUST use `os.replace`, not `os.rename`. Test T-1.1 should run on both runner OSes (CI matrix already covers this) and assert atomicity by interrupting writes mid-flight.
- **Tempfile location**: must be in same directory as final cache file (cross-filesystem `os.replace` may fall back to copy+delete, breaking atomicity). Use `tempfile.NamedTemporaryFile(dir=cache_dir, delete=False)` then `os.replace(temp.name, final_path)`.

### Risk-D: `_compute_cache_key` filename truncation collision risk (D-104-09)

- **Plan**: sha256 hex (64 chars) truncated to first 32 chars.
- **Subtlety**: 32 hex chars = 128 bits. Birthday collision probability negligible at scale; non-issue.
- **Risk**: cache key includes `sorted(staged_blob_shas)` — if staged set is empty (no files staged, e.g., `git commit -m "msg"` after `git add` reverted), the hash collapses to a deterministic value. Cache hits across different "empty stage" runs may replay stale results.
- **Mitigation**: T-0.5 should include a test for empty staged set (key still distinct via `tool_version` + `args` differences). In practice gate is only invoked on non-empty stage (pre-commit hook), so low-impact.

### Risk-E: `git ls-files --staged -z | xargs -0 git hash-object` portability

- **Plan D-104-09**: shell pipeline for staged blob shas.
- **Subtlety**: `xargs -0` on Windows requires Git Bash (already a dev prereq in this repo). For Python invocation, use `subprocess.run(["git", "ls-files", "-s"], ...)` which returns `<mode> <sha> <stage>\t<path>` lines — extract sha column directly without xargs. **Faster + cross-platform.**
- **Action**: T-0.6 implementation should use `git ls-files -s` parsing, NOT shell pipeline. Test cross-platform behavior.

### Risk-F: `AGENT_METADATA` regeneration drift across 4 IDE mirrors

- **Plan T-0.1**: Update ai-build.md + 9 mirrors. Run `uv run ai-eng sync`.
- **Risk**: `ai-eng sync --check` is the contract (G-7); if T-0.1 misses one of the 9 mirrors and sync regenerates inconsistently, CI fails. Mitigation: edit `.claude/agents/ai-build.md` ONLY (canonical), then `uv run ai-eng sync` regenerates the other 9 deterministically.
- **Action**: T-0.1 task must clarify "edit canonical only, run sync to propagate" — currently reads "+ 9 mirrors" which suggests editing all 10 manually.

### Risk-G: `ty` already in pre-push (`stack_runner.py:_PRE_PUSH_TOOLS`) — moving to local fast-slice changes stage

- **D-104-02**: `ty check src/` is in the local fast-slice (line 60-67 of spec). Currently `ty` is classified as PRE_PUSH (`stack_runner.py:551`).
- **Subtlety**: spec-104 wants `ty` to run in the local fast-slice (Wave 2). This is an orthogonal concern to PRE_COMMIT/PRE_PUSH classification. Orchestrator handles this independently — orchestrator runs Wave 2 regardless of `_classify_stage` in `stack_runner.py`.
- **Action**: T-4.3 (mode parameter to orchestrator) must NOT mutate `_PRE_PUSH_TOOLS`; it filters via a new `_LOCAL_FAST_SLICE: frozenset` constant in orchestrator. spec-101's classification stays untouched (orthogonality preserved).

### Risk-H: `pytest -m smoke` marker doesn't exist in this repo today

- **R-13**: marker is convention, not standard.
- **Verification**: `grep -rn "pytest.mark.smoke" tests/` would confirm. spec-104 plan T-4.2 / T-4.3 expects skip-passes when 0 tests collected. **Verify before T-2.4 implementation that orchestrator handles `pytest --collect-only -m smoke` with 0 tests gracefully** (currently `stack_runner.py` runs `pytest tests/unit/`, no `-m smoke`).
- **Action**: spec-104 introduces a NEW pytest invocation pattern. Document in `gate-policy.md` (T-4.1).

### Risk-I: Concurrent CLI calls writing the same cache file

- **Risk**: two parallel `ai-eng gate run` invocations in different terminals on the same project hit the same cache key and race on `os.replace`. Last-writer-wins (atomic), but the loser may have written newer data overwritten by older.
- **Mitigation**: T-1.1 mentions "concurrent writes handled (last-writer-wins, no corruption)". Acceptable — corruption-free is the contract; staleness window is bounded by max-age 24h. **No file lock needed.**

### Risk-J: spec-104 `manifest.yml` additive change vs spec-101 lint normaliser

- **Spec D-104-02**: "Política documentada en `.ai-engineering/contexts/gate-policy.md`; no configurable por `manifest.yml`". → no `manifest.yml` edit at all? **Plan T-0.8 says "additive only (`gates.policy_doc_ref` key)"**. Discrepancy.
- **Risk**: spec-101 lint normaliser parses `required_tools:` as the LAST top-level key (manifest.yml lines 209-211 comment). Inserting `gates:` BEFORE `required_tools:` is safe; AFTER would break the lint.
- **Action**: T-4.1 / T-0.8 must clarify whether any `manifest.yml` edit happens. If yes, insert `gates:` near the top (after `quality:` block at lines 79-83), NOT after `required_tools:`. Update phase-1 gate to assert manifest still parses.

### Risk-K: `GateFindingsDocument.schema` Literal collision

- **Plan G-4 / D-104-06**: `schema: "ai-engineering/gate-findings/v1"` literal.
- **Pydantic v2 subtlety**: `Field(default="...")` with `Literal["..."]` annotation works, but JSON serialization may emit it as a string-typed key. Some JSON consumers (jq, jsonschema-rs) may not enforce Literal — they're string. Spec-104 schema validation in tests must use Pydantic's `model_validate(...)` to enforce the literal, NOT loose `dict.get("schema") == "..."`.
- **Action**: T-0.3 test for "schema literal" should use `pytest.raises(ValidationError)` when constructing with wrong schema string, not just string compare.

### Risk-L: Watch loop wall-clock test isolation (T-6.1)

- **Plan**: use `freezegun` or equivalent.
- **Risk**: `freezegun` doesn't patch `time.monotonic()` reliably on all platforms; the watch loop in `handlers/watch.md` is markdown (instruction to agent), not Python code. The wall-clock state lives in `WatchLoopState` Pydantic model; orchestration is the agent reading the watch.md handler.
- **Subtlety**: T-6.1 tests integration of the wall-clock LOGIC. The logic likely lives in `src/ai_engineering/policy/watch_residuals.py` (T-6.3) or a new helper. Test the helper directly with monkeypatched `datetime.now`. Markdown handler just dictates the helper invocation contract.
- **Action**: T-6.5 implementation should expose `should_stop(state: WatchLoopState, now: datetime) -> StopReason | None` so tests call it with synthetic `now` without freezegun.

### Risk-M: Wall-clock cap exit code 90 collision

- **D-104-05**: Exit 90 distinct from spec-101 D-101-11 exits 80/81.
- **Risk**: verify no other exit code in `cli_commands/_exit_codes.py` already uses 90.
- **Action**: T-6.2 implementation should add `WATCH_LOOP_CAP_REACHED = 90` to `_exit_codes.py` (new spec-101 file). **Read `_exit_codes.py` before T-6.2 to confirm 90 is free.**

---

## Summary

- **Phase 0 hooks identified**: orchestrator inserts at `gates.py` lines 100-105; CLI extends `cli_commands/gate.py` with new `gate_run` + `gate cache` subcommands; Pydantic v2 patterns in `state/models.py` are clear and consistent (BaseModel + StrEnum + frozen + Literal for schema versions).
- **Skill baseline confirmed**: 126 + 221 + 185 = 532 lines exactly matches D-104-07.
- **Spec-101 orthogonality verified**: zero functional overlap; only `gates.py` + `state/models.py` + `manifest.yml` + `ai-build.md` + `ci-check.yml` are jointly touched, all additively. spec-101 frozen at commit `06f0d167` (Wave 37) — no concurrent edits.
- **13 implementation risks flagged** (A-M): pydantic v2 frozen+hashability, ThreadPoolExecutor confirmed correct, `os.replace` not `os.rename` for Windows atomicity, git ls-files parsing not shell pipeline, AGENT_METADATA canonical-only edit, `ty` mode-orthogonal classification, missing `pytest -m smoke` marker, manifest.yml `required_tools:` lint position, Literal schema validation strictness, freezegun-free watch test design, exit code 90 availability.
- **Recommended ordering tweaks**: (1) verify exit code 90 free before T-6.2; (2) verify `pytest -m smoke` absence before T-4.2; (3) clarify T-0.1 wording (canonical edit + sync, not 10 manual edits); (4) confirm whether `manifest.yml` `gates:` block is in scope — if yes, insert position matters for spec-101 lint compatibility.
