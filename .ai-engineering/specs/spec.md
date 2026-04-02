---
spec: spec-100
title: Version alignment and install story — commit-back, CHANGELOG, documentation
status: done
effort: high
---

## Summary

ai-engineering has three published versions on PyPI (0.1.0, 0.2.0, 0.3.0) but `pyproject.toml` on main permanently says `0.1.0`, CHANGELOG.md has no section headers for 0.2.0 or 0.3.0 (everything lives under `[Unreleased]`), `version/registry.json` is stale, and the README Install section recommends `pip install` without explaining virtual environments, pipx, or PEP 668 restrictions. Users who follow the README on modern macOS/Linux hit an error on the first command.

## Goals

- [ ] `pyproject.toml` version on main matches the latest published PyPI version (currently `0.3.0`)
- [ ] `version/registry.json` lists all three published versions (0.1.0, 0.2.0, 0.3.0) — one-time backfill in this PR
- [ ] `ci-build.yml` commits the version bump back to main after a successful tag creation (not after PyPI publish — PyPI publish is a separate manual `release.yml` step)
- [ ] `ci-build.yml` adds `if` guard on `workflow_run` trigger to skip when head commit contains `[skip ci]` (native `[skip ci]` semantics do not apply to `workflow_run`)
- [ ] CHANGELOG.md has proper `[0.3.0]`, `[0.2.0]`, `[0.1.0]` section headers with entries assigned to the correct release based on `git log` tag boundaries
- [ ] `[Unreleased]` section is empty (HEAD = v0.3.0, no post-release changes exist)
- [ ] README Install section recommends `pipx install ai-engineering` as primary method, `uv tool install ai-engineering` as alternative, and `pip install` as fallback with venv guidance
- [ ] Prerequisites (Python 3.11+, Git) appear before install commands, not after
- [ ] README documents that `ai-eng install .` auto-installs missing tools (ruff, gitleaks, ty, pip-audit) during the install phase — clarifying this is install-time behavior, not runtime
- [ ] GETTING_STARTED.md connects to the install flow with a brief "How to install" preamble that links back to the README Install section
- [ ] All documentation is in English — translate or remove 2 Spanish-language files in `docs/` (`trabajo-humano-era-ai-native-2026-2031.md`, `ai-engineering-auditoria-diagramas.md`)

## Non-Goals

- Changing the semantic-release configuration or switching to a different release tool
- Adding brew formula or other OS-level package distribution
- Rewriting GETTING_STARTED.md beyond adding the install preamble
- Modifying the installer code itself (it already works correctly)
- Backfilling detailed commit-level attribution in CHANGELOG entries — use the existing entries, just move them under the correct version header
- Updating `docs/solution-intent.md` install references (internal doc, low traffic — tracked separately if needed)
- Tightening `release.yml` CHANGELOG validation to fail on missing version headers (separate CI concern)

## Decisions

D-100-01: Reorganize CHANGELOG by mapping entries to versions using `git log v0.1.0..v0.2.0` and `git log v0.2.0..v0.3.0` commit boundaries. Entries matching commits in the v0.1.0→v0.2.0 range go under `[0.2.0] - 2026-04-01`. Entries matching v0.2.0→v0.3.0 go under `[0.3.0] - 2026-04-02`. `[Unreleased]` becomes empty.
**Rationale**: The entries already exist and are accurate — they just need to be placed under the correct version header. No content rewriting needed, only reorganization.

D-100-02: `ci-build.yml` commit-back triggers at tag-creation time (inside `ci-build.yml`), NOT after PyPI publish. The workflow updates `pyproject.toml` and `version/registry.json` on main via the GitHub Git Data API (blob→tree→commit→ref update). The commit message is `chore(release): bump version to X.Y.Z [skip ci]`. A `workflow_run` guard (`if: !contains(...)`) prevents the commit-back from triggering a new CI run.
**Rationale**: Previous spec-097 attempts (commits 343-349) failed because: (a) detached HEAD in semantic-release, (b) `force` sent as string not boolean in API call, (c) approach was ultimately abandoned. This time, the commit-back runs AFTER the tag is created and artifacts are built, using the proven Git Data API pattern that successfully creates tags. The key difference: we update the ref for `refs/heads/main`, not create a new tag ref.

D-100-03: README Install section structure: Prerequisites → Primary install (pipx) → Alternative (uv tool) → Fallback (pip + venv) → Verify → Quick Start. Each method is a single code block with copy-paste commands.
**Rationale**: pipx is the Python ecosystem standard for CLI tools (isolated, PATH-managed, no venv activation needed). uv tool is the modern equivalent. pip requires manual venv management which is error-prone for end users. Ordering by simplicity reduces friction.

D-100-04: Set `pyproject.toml` version to `0.3.0` and backfill `version/registry.json` with all three versions in this PR. One-time manual alignment.
**Rationale**: After this, the CI commit-back handles all future version bumps automatically. The registry.json backfill is a one-time data correction, not a process change.

D-100-06: Delete the 2 Spanish-language documents in `docs/` rather than translating them. `trabajo-humano-era-ai-native-2026-2031.md` is a strategic vision essay and `ai-engineering-auditoria-diagramas.md` is an internal architecture audit — both are internal working documents superseded by the current README ecosystem and solution-intent docs.
**Rationale**: These are internal artifacts, not user-facing documentation. Translating 594 lines of strategic prose adds no value to end users. The content they cover (vision, architecture) is already captured in English in `docs/solution-intent.md` and the README ecosystem.

D-100-05: Sequencing constraint — CHANGELOG reorganization (D-100-01) and version alignment (D-100-04) happen first, before the ci-build.yml commit-back implementation (D-100-02). Documentation changes (D-100-03) are independent and can be parallelized.
**Rationale**: The commit-back must target a repo that already has correct version state. If we implement commit-back first on a repo with misaligned versions, the first release would produce incorrect state.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Commit-back triggers CI loop via `workflow_run` | Infinite workflow runs | `[skip ci]` in commit message + explicit `if` guard on `workflow_run` trigger (native skip semantics don't apply to `workflow_run`) |
| Branch protection blocks commit-back | Release fails | Git Data API bypasses branch protection (same mechanism that creates tags). Fallback: open a PR automatically |
| Git Data API commit-back fails (same as spec-097) | Version drifts again | Previous failures were: detached HEAD (fixed by not using semantic-release for the commit), JSON boolean bug (fixed). New approach creates commit directly via API, not through semantic-release |
| CHANGELOG entry misattribution | Wrong entries under wrong version | Verify with `git log --oneline vX..vY` mapping; review diff before merging |
| Users find old `pip install` in cached README | Confusion | PyPI long_description updates on next release; GitHub README updates immediately on merge |

## References

- PyPI: https://pypi.org/project/ai-engineering/ (0.1.0, 0.2.0, 0.3.0)
- Current ci-build.yml sed-based local bump: `.github/workflows/ci-build.yml`
- Previous commit-back attempts: commits 343-349 (spec-097), ultimately abandoned in commit 349
- PEP 668 (externally managed environments): https://peps.python.org/pep-0668/
- Tool auto-install code: `src/ai_engineering/installer/tools.py:40` (`ensure_tool` with `allow_install=True`)
