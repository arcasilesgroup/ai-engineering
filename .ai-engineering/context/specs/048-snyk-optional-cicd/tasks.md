---
spec: "048"
total: 8
completed: 0
last_session: "2026-03-10"
next_session: "Phase 1 — CI Workflow"
---

# Tasks — Snyk Optional CI/CD Integration

## Phase 0: Scaffold [S]
- [ ] 0.1 Create spec.md, plan.md, tasks.md
- [ ] 0.2 Activate spec in _active.md

## Phase 1: CI Workflow [M]
- [ ] 1.1 Add `snyk-security` job to `.github/workflows/ci.yml` with SNYK_TOKEN conditional
- [ ] 1.2 Add `snyk test` step for dependency vulnerability scanning
- [ ] 1.3 Add `snyk code test` step for SAST analysis
- [ ] 1.4 Add `snyk monitor` step conditional on main branch push

## Phase 2: Framework Registration [S]
- [ ] 2.1 Add `snyk` to `tooling.optional.security` in `manifest.yml`
- [ ] 2.2 Add snyk to optional CI checks in `standards/framework/cicd/core.md`
- [ ] 2.3 Reference snyk as optional tool in `skills/security/SKILL.md` (static + deps modes)

## Phase 3: Validation [S]
- [ ] 3.1 Run actionlint + content integrity validation
