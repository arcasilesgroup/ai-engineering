# Plan: spec-100 Version alignment and install story

## Pipeline: standard
## Phases: 4
## Tasks: 12 (build: 10, verify: 2)

### Phase 1: Version alignment + CHANGELOG reorganization
**Gate**: pyproject.toml says 0.3.0, registry.json has all 3 versions, CHANGELOG has proper version headers, [Unreleased] is empty. Spanish docs deleted.

- [ ] T-1.1: Set `pyproject.toml` version to `0.3.0` (D-100-04) (agent: build)
- [ ] T-1.2: Backfill `version/registry.json` with 0.1.0, 0.2.0, 0.3.0 entries including correct dates and status (D-100-04) (agent: build)
- [ ] T-1.3: Reorganize CHANGELOG.md — move entries under correct `[0.3.0]`, `[0.2.0]` headers using `git log` tag boundaries. Empty `[Unreleased]`. Keep `[0.1.0]` as-is (D-100-01) (agent: build)
- [ ] T-1.4: Delete `docs/trabajo-humano-era-ai-native-2026-2031.md` and `docs/ai-engineering-auditoria-diagramas.md` (D-100-06) (agent: build)
- [ ] T-1.5: Verify phase 1 — pyproject version is 0.3.0, registry has 3 entries, CHANGELOG has [0.3.0]/[0.2.0]/[0.1.0] headers, no Spanish files in docs/ (agent: verify)

### Phase 2: README + GETTING_STARTED documentation
**Gate**: Install section has pipx/uv/pip flow, prerequisites before commands, tool auto-install documented, GETTING_STARTED has install preamble.

- [ ] T-2.1: Rewrite README.md Install section — prerequisites first, then pipx (primary), uv tool (alternative), pip+venv (fallback), verify step, tool auto-install note (D-100-03) (agent: build)
- [ ] T-2.2: Add install preamble to GETTING_STARTED.md — brief "How to install" section at the top that links to README Install (agent: build)
- [ ] T-2.3: Verify phase 2 — README install section is correct, GETTING_STARTED links to it (agent: verify)

### Phase 3: CI commit-back implementation
**Gate**: ci-build.yml has commit-back step after tag creation, workflow_run has [skip ci] guard.

- [ ] T-3.1: Add `[skip ci]` guard to ci-build.yml `workflow_run` trigger — add `if` condition that checks head commit message does not contain `[skip ci]` (D-100-02) (agent: build)
- [ ] T-3.2: Add commit-back step to ci-build.yml — after tag creation, use Git Data API to update pyproject.toml and registry.json on main with bumped version. Commit message: `chore(release): bump version to X.Y.Z [skip ci]` (D-100-02) (agent: build)

### Phase 4: Final verification + spec closure
**Gate**: All 11 spec goals verifiable. Lint clean. Tests pass.

- [ ] T-4.1: Run full test suite, lint, format, secret scan. Fix any issues (agent: build)
- [ ] T-4.2: Update CHANGELOG with spec-100 entries under [Unreleased] (agent: build)
