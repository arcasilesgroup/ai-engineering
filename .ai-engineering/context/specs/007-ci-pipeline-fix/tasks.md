---
spec: "007"
total: 16
completed: 0
last_session: "2026-02-11"
next_session: "Phase 0 — Scaffold"
---

# Tasks — CI Pipeline Fix

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `spec-007/ci-pipeline-fix` from main
- [x] 0.2 Create spec directory `context/specs/007-ci-pipeline-fix/`
- [x] 0.3 Create `spec.md`, `plan.md`, `tasks.md`
- [ ] 0.4 Update `_active.md` to point to 007
- [ ] 0.5 Commit: `spec-007: Phase 0 — scaffold spec files and activate`

## Phase 1: Fix Dependency Resolution [S]

- [ ] 1.1 In `pyproject.toml`, replace `[project.optional-dependencies].dev` with `[dependency-groups].dev` (PEP 735 syntax)
- [ ] 1.2 Regenerate `uv.lock` via `uv lock`
- [ ] 1.3 Local verify: `uv sync --dev && uv run ruff --version && uv run ty --version && uv run pytest --version && uv run pip-audit --version`
- [ ] 1.4 Commit: `spec-007: Phase 1 — migrate dev deps to dependency-groups`

## Phase 2: Fix Broken References [M]

- [ ] 2.1 Update `.ai-engineering/README.md` — fix Reference Structure tree to match actual `context/` layout
- [ ] 2.2 Update `.ai-engineering/README.md` — reword Template Mirror Contract to remove references to deleted paths
- [ ] 2.3 Update `.ai-engineering/context/product/framework-contract.md` — fix Target Installed Structure tree to match actual layout
- [ ] 2.4 Update `.ai-engineering/context/product/framework-contract.md` — reword mirror contract to remove deleted-path references
- [ ] 2.5 Fix `.ai-engineering/context/specs/001-rewrite-v2/tasks.md` — annotate deleted file paths so they don't match validator regex
- [ ] 2.6 Fix `.ai-engineering/context/specs/002-cross-ref-hardening/tasks.md` — correct `skills/swe/create-skill.md` → `skills/lifecycle/create-skill.md` and `skills/swe/create-agent.md` → `skills/lifecycle/create-agent.md`
- [ ] 2.7 Commit: `spec-007: Phase 2 — fix 10 broken file references in governance docs`

## Phase 3: Sync Template Mirrors [S]

- [ ] 3.1 Sync `src/ai_engineering/templates/.ai-engineering/README.md` with canonical README.md changes
- [ ] 3.2 Sync `src/ai_engineering/templates/.ai-engineering/context/product/framework-contract.md` with canonical framework-contract.md changes
- [ ] 3.3 Run `uv run ai-eng validate` — verify 6/6 categories pass
- [ ] 3.4 Commit: `spec-007: Phase 3 — sync template mirrors`

## Phase 4: Verify & Close [S]

- [ ] 4.1 Run full local gate: ruff check, ruff format, ty check, pytest, pip-audit, ai-eng validate
- [ ] 4.2 Push branch, open PR, verify all CI jobs green
- [ ] 4.3 Create `done.md` with summary, verification results, deferred items
- [ ] 4.4 Update `tasks.md` frontmatter: `completed: 16`, `next_session: "Done"`
