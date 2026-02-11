---
spec: "013"
total: 18
completed: 4
last_session: "2026-02-11"
next_session: "Phase 1 — F5 typer dependency"
---

# Tasks — CLI UX Hardening

## Phase 0: Scaffold [S]

- [x] 0.1 Create branch `feat/cli-ux-hardening` from main
- [x] 0.2 Create spec 013 scaffold (spec.md, plan.md, tasks.md)
- [x] 0.3 Activate spec 013 in _active.md
- [x] 0.4 Update product-contract.md → 013

## Phase 1: F5 — Typer Dependency [S]

- [ ] 1.1 Remove `[all]` from pyproject.toml typer dependency
- [ ] 1.2 Run `uv lock` to update lockfile
- [ ] 1.3 Verify clean install with no warning

## Phase 2: F4 — Auto-Install Hooks [S]

- [ ] 2.1 Add `install_hooks()` call to `installer/service.py` `install()` function
- [ ] 2.2 Update e2e install tests to expect hooks
- [ ] 2.3 Verify doctor passes without `--fix-hooks` after fresh install

## Phase 3: F1 — Centralized Error Handler [M]

- [ ] 3.1 Add `FileNotFoundError` handler in `cli_factory.py` app callback
- [ ] 3.2 Add tests for clean error messages on bad paths
- [ ] 3.3 Verify all commands show friendly error on `/nonexistent`

## Phase 4: F2 — Stack Name Validation [M]

- [ ] 4.1 Add `get_available_stacks()` helper in `installer/operations.py`
- [ ] 4.2 Add validation in `stack_ide.py` `stack_add`/`ide_add`
- [ ] 4.3 Add tests for invalid stack name rejection
- [ ] 4.4 Verify existing stack operations still work

## Phase 5: Close [S]

- [ ] 5.1 Run full test suite
- [ ] 5.2 Run `ai-eng validate` (6/6 integrity)
- [ ] 5.3 Create done.md
- [ ] 5.4 Update tasks.md frontmatter
