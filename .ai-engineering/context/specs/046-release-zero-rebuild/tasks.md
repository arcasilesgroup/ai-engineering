---
spec: "046"
total: 13
completed: 3
last_session: "2026-03-10"
next_session: "Phase 1 — Implement"
---

# Tasks — Release Zero-Rebuild

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec.md, plan.md, tasks.md
- [x] 0.2 Update _active.md
- [x] 0.3 Commit scaffold

## Phase 1: Implement [M]
- [ ] 1.1 Add `retention-days: 5` to CI artifact upload in `ci.yml`
- [ ] 1.2 Rewrite `release.yml` — add verify-ci job with retry/backoff for CI race condition
- [ ] 1.3 Rewrite `release.yml` — download-artifact job finds CI run-id and downloads `dist/`
- [ ] 1.4 Rewrite `release.yml` — publish job uses downloaded artifact for PyPI
- [ ] 1.5 Rewrite `release.yml` — github-release job uses downloaded artifact
- [ ] 1.6 Update `check_workflow_policy.py` if needed

## Phase 2: Validate [S]
- [ ] 2.1 Run actionlint on modified workflows
- [ ] 2.2 Run check_workflow_policy.py
- [ ] 2.3 Verify flow with `ai-eng release --wait` (tag after CI done)
- [ ] 2.4 Verify flow without `--wait` (tag immediately post-merge, verify-ci retries)
