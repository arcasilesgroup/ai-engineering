# Release Gate

## Purpose

Executes a structured GO/NO-GO checklist across all quality dimensions for release readiness. Aggregates results from contract compliance, security enforcement, command reliability, ownership safety, test confidence, documentation coherence, and packaging integrity into a single verdict with blocking issues and residual risk.

## Trigger

- Command: agent invokes release-gate skill or user requests release readiness check.
- Context: pre-release milestone, version tagging, merge-to-main decision.

## Procedure

### Phase 1: Gate Dimensions

1. **Contract compliance** — verify framework contracts are satisfied.
   - Invoke `govern/contract-compliance.md` or review most recent compliance report.
   - Gate: no FAIL clauses (PARTIAL acceptable with risk acceptance).

2. **Security enforcement** — verify security posture.
   - Invoke `review/security.md` checks or review most recent security report.
   - Gate: no critical/high findings. Medium findings documented.
   - Check: hooks installed, gitleaks clean, pip-audit clean, semgrep clean.

3. **Command reliability** — verify all commands work as contracted.
   - Review verify-app results for command contract compliance.
   - Gate: all commands execute their contracted step sequence.
   - Check: /commit, /commit --only, /pr, /pr --only, /acho, /acho pr.

4. **Ownership safety** — verify update flows respect boundaries.
   - Invoke `govern/ownership-audit.md` or review most recent ownership report.
   - Gate: no ownership violations, updater safety confirmed.

5. **Test confidence** — verify test coverage meets thresholds.
   - Invoke `quality/test-gap-analysis.md` or review most recent gap analysis.
   - Gate: ≥80% overall, ≥90% governance-critical, no untested critical paths.
   - Check: all tests passing, no skipped governance tests.

6. **Documentation coherence** — verify docs are current and correct.
   - Invoke `quality/docs-audit.md` or review most recent docs report.
   - Gate: no misplaced files, no stale critical content, template compliance.

7. **Packaging integrity** — verify distribution readiness.
   - Invoke `quality/install-check.md` or review most recent install check.
   - Gate: clean install works, doctor passes, all artifacts bundled.
   - Check: wheel builds, pip install succeeds, template tree complete.

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

- `skills/govern/contract-compliance.md` — contract compliance gate.
- `skills/govern/ownership-audit.md` — ownership safety gate.
- `skills/govern/integrity-check.md` — structural integrity gate.
- `skills/quality/audit-code.md` — code quality gate.
- `skills/quality/test-gap-analysis.md` — test confidence gate.
- `skills/quality/docs-audit.md` — documentation coherence gate.
- `skills/quality/install-check.md` — packaging integrity gate.
- `skills/review/security.md` — security enforcement gate.
- `agents/platform-auditor.md` — orchestrator that uses this skill.
- `agents/verify-app.md` — command reliability source.
- `standards/framework/quality/core.md` — quality thresholds.
