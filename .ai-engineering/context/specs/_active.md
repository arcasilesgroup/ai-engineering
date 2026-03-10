---
active: "048-snyk-optional-cicd"
updated: "2026-03-10"
---

# Active Spec

**Spec 048 — Snyk Optional CI/CD Integration**

Add Snyk as optional CI/CD security steps (snyk test + snyk code test + snyk monitor) conditional on SNYK_TOKEN secret. Non-gating, complementary to existing gitleaks/semgrep/pip-audit gates.

## Quick Resume

- Spec: [spec.md](specs/048-snyk-optional-cicd/spec.md)
- Plan: [plan.md](specs/048-snyk-optional-cicd/plan.md)
- Tasks: [tasks.md](specs/048-snyk-optional-cicd/tasks.md)
- Branch: `feat/048-snyk-optional-cicd`
- Next: Phase 1 — CI Workflow
