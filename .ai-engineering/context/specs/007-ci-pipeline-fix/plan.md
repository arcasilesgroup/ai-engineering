---
spec: "007"
approach: "serial-phases"
---

# Plan — CI Pipeline Fix

## Architecture

### New Files

None.

### Modified Files

| File | Change |
|------|--------|
| `pyproject.toml` | Replace `[project.optional-dependencies].dev` with `[dependency-groups].dev` |
| `uv.lock` | Regenerated via `uv lock` |
| `.ai-engineering/README.md` | Update Reference Structure tree + fix Template Mirror Contract broken refs |
| `.ai-engineering/context/product/framework-contract.md` | Update Target Installed Structure tree + fix mirror contract broken refs |
| `.ai-engineering/context/specs/001-rewrite-v2/tasks.md` | Annotate deleted file paths to avoid validator match |
| `.ai-engineering/context/specs/002-cross-ref-hardening/tasks.md` | Correct `skills/swe/` → `skills/lifecycle/` paths |
| `src/ai_engineering/templates/.ai-engineering/README.md` | Mirror canonical README fix |
| `src/ai_engineering/templates/.ai-engineering/context/product/framework-contract.md` | Mirror canonical framework-contract fix |

### Mirror Copies

| Canonical | Mirror |
|-----------|--------|
| `.ai-engineering/README.md` | `src/ai_engineering/templates/.ai-engineering/README.md` |
| `.ai-engineering/context/product/framework-contract.md` | `src/ai_engineering/templates/.ai-engineering/context/product/framework-contract.md` |

## File Structure

No new directories. All changes are in-place modifications.

## Session Map

### Phase 0: Scaffold [S]

- Create branch, spec files, activate spec.
- Size: Small — 4 files, < 15 min.

### Phase 1: Fix Dependency Resolution [S]

- Migrate `pyproject.toml` dev deps to `[dependency-groups].dev`.
- Remove `[project.optional-dependencies]` section.
- Regenerate `uv.lock` via `uv lock`.
- Local verification: `uv sync --dev && uv run ruff --version && uv run pytest --version`.
- Size: Small — 1 file edit + lock regen.

### Phase 2: Fix Broken References [M]

- Update `.ai-engineering/README.md` Reference Structure tree (lines 30–55) to match actual layout.
- Update `.ai-engineering/README.md` line 63 to remove deleted-path references.
- Update `.ai-engineering/context/product/framework-contract.md` Target Installed Structure (lines 300–335).
- Update `.ai-engineering/context/product/framework-contract.md` line 340 to remove deleted-path references.
- Fix `.ai-engineering/context/specs/001-rewrite-v2/tasks.md` lines 24, 25, 28 — annotate deleted paths.
- Fix `.ai-engineering/context/specs/002-cross-ref-hardening/tasks.md` lines 18–19 — correct `swe/` → `lifecycle/`.
- Size: Medium — 4 governance files, careful text surgery.

### Phase 3: Sync Template Mirrors [S]

- Copy canonical fixes to template mirrors.
- Verify with `uv run ai-eng validate` — must pass 6/6.
- Size: Small — 2 mirror files.

### Phase 4: Verify & Close [S]

- Run full local CI equivalent: `uv run ruff check`, `uv run ty check`, `uv run pytest`, `uv run pip-audit`, `uv run ai-eng validate`.
- Push branch, open PR, verify CI green.
- Create `done.md`.
- Size: Small — verification only.

## Patterns

- One atomic commit per phase: `spec-007: Phase N — <description>`.
- Mirror edits must be character-identical to canonical (validated by `mirror-sync` category).
- Governance file edits preserve surrounding context — minimal surgical changes only.
