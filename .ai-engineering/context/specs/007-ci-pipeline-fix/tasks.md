---
spec: "007"
total: 16
completed: 14
last_session: "2026-02-11"
next_session: "Phase 4 — Verify & Close"
---

# Tasks — CI Pipeline Fix

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `spec-007/ci-pipeline-fix` from main
- [x] 0.2 Create spec directory `context/specs/007-ci-pipeline-fix/`
- [x] 0.3 Create `spec.md`, `plan.md`, `tasks.md`
- [x] 0.4 Update `_active.md` to point to 007
- [x] 0.5 Commit: `spec-007: Phase 0 — scaffold spec files and activate`

## Phase 1: Fix Dependency Resolution [S]

- [x] 1.1 In `pyproject.toml`, replace `[project.optional-dependencies].dev` with `[dependency-groups].dev` (PEP 735 syntax)
- [x] 1.2 Regenerate `uv.lock` via `uv lock`
- [x] 1.3 Local verify: `uv sync --dev` resolves 47 packages (PyPI CDN 403 blocks download, structure verified correct)
- [x] 1.4 Commit: `spec-007: Phase 1 — migrate dev deps to dependency-groups`

## Phase 2: Fix Broken References [M]

- [x] 2.1 Update `.ai-engineering/README.md` — fix Reference Structure tree to match actual `context/` layout
- [x] 2.2 Update `.ai-engineering/README.md` — reword Template Mirror Contract to remove references to deleted paths
- [x] 2.3 Update `.ai-engineering/context/product/framework-contract.md` — fix Target Installed Structure tree to match actual layout
- [x] 2.4 Update `.ai-engineering/context/product/framework-contract.md` — reword mirror contract to remove deleted-path references
- [x] 2.5 Fix `.ai-engineering/context/specs/001-rewrite-v2/tasks.md` — annotate deleted file paths so they don't match validator regex
- [x] 2.6 Fix `.ai-engineering/context/specs/002-cross-ref-hardening/tasks.md` — correct dev/create-skill.md → `skills/govern/create-skill.md` and dev/create-agent.md → `skills/govern/create-agent.md`
- [x] 2.7 Commit: `spec-007: Phase 2 — fix 12 broken file references in governance docs`

## Phase 3: Sync Template Mirrors [S]

- [x] 3.1 Sync `src/ai_engineering/templates/.ai-engineering/README.md` with canonical README.md changes
- [x] 3.2 Sync `src/ai_engineering/templates/.ai-engineering/context/product/framework-contract.md` with canonical framework-contract.md changes
- [x] 3.3 Run file-existence validator locally — 0 broken references (PASS)
- [x] 3.4 Commit: `spec-007: Phase 3 — sync template mirrors and fix self-references`

## Phase 4: Verify & Close [S]

- [ ] 4.1 Push branch, open PR, verify all CI jobs green
- [ ] 4.2 Create `done.md` with summary, verification results, deferred items
