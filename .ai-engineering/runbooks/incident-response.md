---
owner: operate
---

# Runbook: Incident Response

## Purpose

Structured response to production incidents. Diagnose, contain, fix, and document.

## Procedure

1. **Acknowledge**: Confirm the incident scope and severity.
2. **Contain**: Identify the blast radius. Rollback if safe.
3. **Diagnose**: Check logs, metrics, recent deployments, recent config changes.
4. **Fix**: Apply the minimum change to resolve the incident.
5. **Verify**: Confirm the fix resolves the issue without side effects.
6. **Document**: Record timeline, root cause, fix, and follow-up actions in an issue.
7. **Post-mortem**: Schedule if severity >= P1.

## Severity Levels

| Level | Criteria | Response Time |
|-------|----------|---------------|
| P0 | Service down, data loss | Immediate |
| P1 | Major degradation, security breach | < 1 hour |
| P2 | Minor degradation, workaround exists | < 4 hours |
| P3 | Cosmetic, non-blocking | Next business day |

## Checklist

- [ ] Incident acknowledged and severity assigned
- [ ] Blast radius identified
- [ ] Containment action taken (rollback, feature flag, etc.)
- [ ] Root cause identified
- [ ] Fix applied and verified
- [ ] Incident documented
- [ ] Follow-up actions created as issues
