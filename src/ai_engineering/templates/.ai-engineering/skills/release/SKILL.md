---
name: release
version: 1.0.0
description: Aggregated GO/NO-GO release readiness gate; use before version tagging
  or merge-to-main to verify all quality dimensions pass.
argument-hint: '[version]'
tags: [quality, release, gate, go-no-go]
---

# Release Gate

## Purpose

Executes a structured GO/NO-GO checklist across all quality dimensions for release readiness. Aggregates results from contract compliance, security enforcement, command reliability, ownership safety, test confidence, documentation coherence, and packaging integrity into a single verdict with blocking issues and residual risk.

## Trigger

- Command: agent invokes release-gate skill or user requests release readiness check.
- Context: pre-release milestone, version tagging, merge-to-main decision.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"release"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Code quality only** (coverage, complexity, lint) — use `audit` instead. Release-gate aggregates all dimensions; audit focuses on code quality.
- **Security only** (OWASP, secrets, dependencies) — use `sec-review` instead.
- **Test coverage analysis** — use `test-gap` instead.
- **Full platform audit** (8+ dimensions with scoring) — use `agent:review` instead. Release-gate covers 7 dimensions; review agent covers all 8+ with weighted scoring.

## Procedure

### Phase 1: Gate Dimensions

1. **Contract compliance** — verify framework contracts are satisfied.
   - Invoke `compliance/SKILL.md` or review most recent compliance report.
   - Gate: no FAIL clauses (PARTIAL acceptable with risk acceptance).

2. **Security enforcement** — verify security posture.
   - Invoke `sec-review/SKILL.md` checks or review most recent security report.
   - Gate: no critical/high findings. Medium findings documented.
   - Check: hooks installed, gitleaks clean, pip-audit clean, semgrep clean.

3. **Command reliability** — verify all commands work as contracted.
   - Review verify-app results for command contract compliance.
   - Gate: all commands execute their contracted step sequence.
   - Check: /commit, /commit --only, /pr, /pr --only.

4. **Ownership safety** — verify update flows respect boundaries.
   - Invoke `ownership/SKILL.md` or review most recent ownership report.
   - Gate: no ownership violations, updater safety confirmed.

5. **Test confidence** — verify test coverage meets thresholds.
   - Invoke `test-gap/SKILL.md` or review most recent gap analysis.
   - Gate: 100% coverage, no untested critical paths.
   - Check: all tests passing, no skipped governance tests.

6. **Documentation coherence** — verify docs are current and correct.
   - Invoke `docs-audit/SKILL.md` or review most recent docs report.
   - Gate: no misplaced files, no stale critical content, template compliance.

7. **Packaging integrity** — verify distribution readiness.
   - Invoke `install/SKILL.md` or review most recent install check.
   - Gate: clean install works, doctor passes, all artifacts bundled.
   - Check: wheel builds, pip install succeeds, template tree complete.

8. **Sonar quality gate** (optional) — verify Sonar analysis passes.
   - Invoke `sonar/SKILL.md` or review most recent Sonar report.
   - Gate: Sonar quality gate status is PASS or SKIP (not configured).
   - Check: coverage, duplication, blocker/critical issues match framework contract.
   - **Silent skip**: if Sonar is not configured, this dimension is auto-PASS.

### Phase 2: Aggregate Verdict

8. **Collect gate results** — compile pass/fail for each dimension.
   - Record: dimension name, status, blocking issues, residual risk.

9. **Determine verdict** — apply GO/NO-GO logic.
   - **GO**: all 7 dimensions pass (no blocking issues).
   - **CONDITIONAL GO**: all dimensions pass except non-critical items with risk acceptance.
   - **NO-GO**: one or more blocking issues without risk acceptance.

10. **Define closure path** — for NO-GO, list minimum actions to reach GO.
    - Prioritize by blocking severity.
    - Estimate effort per action.
    - Identify parallel vs sequential work.

## Examples

### Example 1: Final release readiness decision

User says: "Run release gate before tagging v1.6.0."
Actions:

1. Aggregate gate evidence across compliance, security, quality, ownership, testing, docs, and packaging dimensions.
2. Determine GO, CONDITIONAL GO, or NO-GO and list blocking actions if needed.
   Result: Release decision is documented with explicit blockers, risks, and closure path.

## Output Contract

```
## Release Readiness Report

### Verdict: GO | CONDITIONAL GO | NO-GO

### Gate Results
| Dimension | Status | Blocking Issues | Residual Risk |
|-----------|--------|-----------------|---------------|
| Contract Compliance | PASS/FAIL | ... | ... |
| Security Enforcement | PASS/FAIL | ... | ... |
| Command Reliability | PASS/FAIL | ... | ... |
| Ownership Safety | PASS/FAIL | ... | ... |
| Test Confidence | PASS/FAIL | ... | ... |
| Documentation Coherence | PASS/FAIL | ... | ... |
| Packaging Integrity | PASS/FAIL | ... | ... |
| Sonar Quality Gate | PASS/FAIL/SKIP | ... | ... |

### Blocking Issues (if NO-GO)
- [Prioritized list with severity and remediation]

### Closure Path (if NO-GO)
- [Minimum actions to reach GO with effort estimates]

### Residual Risk Statement
- [Accepted risks with decision-store references]
```

## Governance Notes

- Release gate is the final quality checkpoint before version tagging or merge to main.
- NO-GO verdict blocks release — no override without explicit risk acceptance for each blocking issue.
- CONDITIONAL GO requires all risk acceptances recorded in `state/decision-store.json`.
- This skill provides the procedural complement to the `platform-auditor` agent's orchestrated assessment.
- Each gate dimension maps to a specific skill — this skill aggregates, it does not duplicate their procedures.

## References

- `skills/governance/SKILL.md` — compliance, ownership, integrity gates.
- `skills/quality/SKILL.md` — code quality gate.
- `skills/test/SKILL.md` — test confidence gate.
- `skills/document/SKILL.md` — documentation coherence gate.
- `skills/security/SKILL.md` — security enforcement gate.
- `agents/operate.md` — orchestrator that uses this skill and command reliability source.
- `standards/framework/quality/core.md` — quality thresholds.
