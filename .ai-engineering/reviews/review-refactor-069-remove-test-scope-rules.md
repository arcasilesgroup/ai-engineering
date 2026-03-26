# Code Review: main..refactor/069-remove-test-scope-rules

**Date**: 2026-03-25
**Scope**: 329 files, 48 commits, +28,589/-5,793 lines
**Specs covered**: 064, 065, 068, 069, 071, 075, 076
**Reviewer**: Claude Opus 4.6 (comprehensive review)

---

## Summary

This branch delivers 7 sequential specs modernizing the framework: test scope removal, state model overhaul (InstallManifest -> InstallState), installer phase redesign, autopilot v2, dispatch enhancement, IDE mirror parity, and doctor redesign. The architecture is sound and the changes are well-motivated. A few correctness issues need fixing before merge.

---

## Findings

### BLOCKING (2)

#### B1. `test_installer_integration.py` -- 4 tests reference non-existent attribute

**File**: `tests/integration/test_installer_integration.py:346,371,409,415`
**Confidence**: 95%

`list_status()` now returns `ManifestConfig`, not `InstallState`. `add_stack()` and `remove_stack()` also return `ManifestConfig`. But 4 tests access `manifest.installed_stacks` which doesn't exist on either model. The stacks live at `manifest.providers.stacks`.

Additionally, line 408 asserts `isinstance(manifest, InstallState)` but `list_status()` returns `ManifestConfig`.

```python
# Current (will fail with AttributeError):
manifest = list_status(installed_project)
assert isinstance(manifest, InstallState)       # line 408 -- WRONG type
assert "python" in manifest.installed_stacks     # line 409 -- WRONG attr

# Fix:
from ai_engineering.config.manifest import ManifestConfig

manifest = list_status(installed_project)
assert isinstance(manifest, ManifestConfig)
assert "python" in manifest.providers.stacks
```

Affected lines: 346, 371, 408-409, 414-415.

---

#### B2. `signals.py:683` -- Semantic mismatch: `authenticated` repurposed for hook integrity

**File**: `src/ai_engineering/lib/signals.py:683`
**Confidence**: 90%

```python
hooks_verified = git_hooks_entry.authenticated if git_hooks_entry else False
```

`ToolEntry.authenticated` semantically means "tool is logged in / has credentials". Using it for "hooks are integrity-verified" is a semantic mismatch. The value is technically set correctly (via `hooks/manager.py:352` comment: `# integrity_verified mapped to authenticated`), but this mapping is fragile:

- Any code checking `git_hooks_entry.authenticated` for its actual meaning (auth status) will get the wrong answer
- The `observe` CLI uses this to display "verified" status -- correct today but relies on an undocumented convention

```python
# Option A: Add a dedicated field to ToolEntry
class ToolEntry(BaseModel):
    installed: bool = False
    authenticated: bool = False
    integrity_verified: bool = False  # new field
    mode: str = "cli"
    scopes: list[str] = Field(default_factory=list)

# Option B: Keep authenticated but add explicit doc + constant
# (Less clean but minimal change)
```

---

### SUGGESTION (3)

#### S1. `merge_settings` missing `FileNotFoundError` handling

**File**: `src/ai_engineering/installer/merge.py:55-57`
**Confidence**: 80%

```python
try:
    with open(real_target, encoding="utf-8") as fh:
        target_data = json.load(fh)
except (json.JSONDecodeError, ValueError):
```

If `target_path` doesn't exist, `FileNotFoundError` propagates unhandled. The `except` only catches malformed JSON. Either:
- Add `FileNotFoundError` to the except clause and write template as-is (most resilient)
- Or document the precondition that target must exist

```python
except FileNotFoundError:
    # Target doesn't exist yet -- write template as-is
    with open(real_target, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(template_data, indent=2) + "\n")
    return Path(real_target)
except (json.JSONDecodeError, ValueError):
```

---

#### S2. `ToolEntry` overloaded for heterogeneous data

**File**: `src/ai_engineering/hooks/manager.py:350-362`
**Confidence**: 75%

The `tooling` dict mixes actual tool entries with hook metadata:

```python
state.tooling["git_hooks"] = ToolEntry(installed=True, authenticated=True)
state.tooling["hook_hash:pre-commit"] = ToolEntry(installed=True, mode="abc123...")
state.tooling["hook_hash:pre-push"] = ToolEntry(installed=True, mode="def456...")
```

Using `mode` to store SHA-256 hashes and `authenticated` for integrity verification stretches the `ToolEntry` semantics. This makes the `tooling` dict hard to query (e.g., "list all actual tools" requires filtering out `hook_hash:*` entries). Consider a dedicated `hook_state` field on `InstallState` or a sub-dict convention.

---

#### S3. `from_legacy_dict` timezone handling

**File**: `src/ai_engineering/state/models.py:389`
**Confidence**: 70%

```python
installed_at = _dt.fromisoformat(installed_at_raw) if installed_at_raw else _dt.now(tz=UTC)
```

Legacy `installedAt` values may be timezone-naive strings. `fromisoformat()` will produce a naive `datetime`, but `InstallState.installed_at` defaults to `datetime.now(tz=UTC)` (aware). Mixing aware and naive datetimes in the same field across instances can cause `TypeError` on comparison. Consider:

```python
installed_at_parsed = _dt.fromisoformat(installed_at_raw)
if installed_at_parsed.tzinfo is None:
    installed_at_parsed = installed_at_parsed.replace(tzinfo=UTC)
installed_at = installed_at_parsed
```

---

### QUESTION (2)

#### Q1. Test scope removal -- intentional loss of selective test running?

The removed `test_scope.py` (760+ LOC) allowed targeted test selection based on changed files. The replacement runs `pytest tests/{unit,integration,e2e}` unconditionally. The commit message mentions the suite is fast enough (unit 24s, integration 5m). Is there a plan for when the suite grows beyond those times?

#### Q2. `doctor/phases/detect.py:99` -- Hardcoded schema version

```python
if ctx.install_state.schema_version != "2.0":
    problems.append(f"schema_version is '{ctx.install_state.schema_version}', expected '2.0'")
```

Should this use `InstallState.model_fields["schema_version"].default` or a module constant instead of a magic string?

---

### Positive Observations

- **Path traversal protection** in `merge_settings` is well-implemented (CWE-22 / S2083 compliant with `os.path.realpath()` + prefix check)
- **State model migration** via `from_legacy_dict` is thorough, handling both `install-manifest.json` and `tools.json` legacy formats
- **Phase architecture** for installer and doctor is clean, with clear separation of concerns
- **Autopilot v2** upgrade is well-structured with DAG-driven execution and quality convergence loops
- **Test scope removal** simplifies CI significantly -- removing 760 LOC of manual mapping that was never enforced
- **Ownership defaults** in `defaults.py` are comprehensive and correctly map framework/team/system ownership

---

## Verdict

**Needs fixes before merge** -- 2 blocking issues (B1 is a test failure, B2 is a semantic bug that will cause incorrect reporting). Both are straightforward to fix.
