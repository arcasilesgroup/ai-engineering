---
spec: "046"
total: 13
completed: 13
last_session: "2026-03-10"
next_session: "DONE — ready for PR"
---

# Tasks — Release Zero-Rebuild

## Phase 0: Scaffold [S]
- [x] 0.1 Create spec.md, plan.md, tasks.md
- [x] 0.2 Update _active.md
- [x] 0.3 Commit scaffold

## Phase 1: Implement [M]
- [x] 1.1 Add `retention-days: 5` to CI artifact upload in `ci.yml`
- [x] 1.2 Rewrite `release.yml` — add verify-ci job with retry/backoff for CI race condition
- [x] 1.3 Rewrite `release.yml` — download-artifact job finds CI run-id and downloads `dist/`
- [x] 1.4 Rewrite `release.yml` — publish job uses downloaded artifact for PyPI
- [x] 1.5 Rewrite `release.yml` — github-release job uses downloaded artifact
- [x] 1.6 Update `check_workflow_policy.py` if needed (no changes needed — policies already pass)

## Phase 2: Validate [S]
- [x] 2.1 Run actionlint on modified workflows — PASS
- [x] 2.2 Run check_workflow_policy.py — PASS (4 workflow files)
- [x] 2.3 Verify flow with `ai-eng release --wait` (tag after CI done) — verified
- [x] 2.4 Verify flow without `--wait` (tag immediately post-merge, verify-ci retries) — verified
