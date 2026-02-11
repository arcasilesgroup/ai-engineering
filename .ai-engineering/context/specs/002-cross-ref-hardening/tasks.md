---
total: 22
completed: 22
last_session: S1
next_session: done
---

# Tasks: Cross-Reference Hardening + Skill Registration

## Phase 0: Scaffold — `S0 · Agent-1 · ✓ COMPLETE`

- [x] **Task 0.1**: Create `.ai-engineering/context/specs/002-cross-ref-hardening/` with `spec.md`, `plan.md`, `tasks.md`
- [x] **Task 0.2**: Update `_active.md` — pointer to `002-cross-ref-hardening`

## Phase 1: New Skill Creation — `S0 · Agent-1 · ✓ COMPLETE`

- [x] **Task 1.1**: Create `skills/docs/changelog.md` (canonical + mirror)
- [x] **Task 1.2**: Create `skills/govern/create-skill.md` (canonical + mirror)
- [x] **Task 1.3**: Create `skills/govern/create-agent.md` (canonical + mirror)
- [x] **Task 1.4**: Create `skills/docs/writer.md` (canonical + mirror)

## Phase 2: Cross-Reference Hardening — `S0 · Agent-1 · ✓ COMPLETE`

- [x] **Task 2.1**: Add cross-refs to agents — `code-simplifier` (+quality/core.md), `codebase-mapper` (+doc-writer), `principal-engineer` (+security-review), `quality-auditor` (+stacks/python.md), `verify-app` (+migration) — canonical + mirror
- [x] **Task 2.2**: Add cross-refs to SWE skills — `code-review` (+security-review, test-strategy, performance-analysis, code-simplifier), `debug` (+verify-app), `dependency-update` (+security-reviewer), `performance-analysis` (+principal-engineer), `pr-creation` (+changelog-documentation, stacks/python), `prompt-engineer` (+create-skill, create-agent), `python-mastery` (+architect, code-simplifier, codebase-mapper, principal-engineer), `test-strategy` (+debugger, principal-engineer, verify-app) — canonical + mirror
- [x] **Task 2.3**: Add cross-refs to utility skills — `git-helpers` (+commit, pr, core.md), `platform-detection` (+install-readiness, core.md) — canonical + mirror
- [x] **Task 2.4**: Add cross-refs to validation skills — `install-readiness` (+platform-detection, core.md, verify-app) — canonical + mirror
- [x] **Task 2.5**: Add cross-refs to workflow skills — `commit` (+verify-app), `pr` (+pr-creation, verify-app) — canonical + mirror
- [x] **Task 2.6**: Update all 6 instruction files — add `changelog-documentation`, `create-skill`, `create-agent`, `doc-writer` references under `### SWE Skills`
- [x] **Task 2.7**: Update `product-contract.md` — skill count 18 → 21 in objectives and KPIs
- [x] **Task 2.8**: Update `CHANGELOG.md` — add entries for 4 new skills

## Phase 3: Lifecycle Category — `S1 · Agent-1 · ✓ COMPLETE`

- [x] **Task 3.1**: Create `skills/govern/` directory (canonical + mirror)
- [x] **Task 3.2**: Move `create-skill.md` from `swe/` to `lifecycle/` (canonical + mirror) — `git mv` or file move + delete
- [x] **Task 3.3**: Move `create-agent.md` from `swe/` to `lifecycle/` (canonical + mirror) — `git mv` or file move + delete
- [x] **Task 3.4**: Update `create-skill.md` procedure — add `lifecycle/` to the valid category list and update subsection mapping
- [x] **Task 3.5**: Update all 6 instruction files — move `create-skill`/`create-agent` from `### SWE Skills` to new `### Lifecycle Skills` subsection, update paths from `swe/` to `lifecycle/`
- [x] **Task 3.6**: Update cross-references in `prompt-engineer.md` and `create-agent.md` — change `swe/create-skill` → `lifecycle/create-skill` and `swe/create-agent` → `lifecycle/create-agent` (canonical + mirror)

## Phase 4: Verify + Close — `S1 · Agent-1 · ✓ COMPLETE`

- [x] **Task 4.1**: Verify all canonical files exist and follow template structure
- [x] **Task 4.2**: Verify all template mirrors are byte-identical to canonical
- [x] **Task 4.3**: Verify product-contract counter matches actual skill count (21)
- [x] **Task 4.4**: Update tasks.md frontmatter and create `done.md`
