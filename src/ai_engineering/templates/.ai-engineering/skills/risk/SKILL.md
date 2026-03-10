---
name: risk
description: "Manage risk acceptances: accept (record with severity/expiry), resolve (close after remediation), or renew (extend before expiry, max 2)."
metadata:
  version: 1.0.0
  tags: [governance, risk, acceptance, remediation, renewal, decision]
  ai-engineering:
    scope: read-write
    token_estimate: 1400
---

# Risk Lifecycle

## Purpose

Unified procedure for the risk acceptance lifecycle: accepting new risks, resolving them after remediation, and renewing when more time is needed. Ensures every risk is tracked, time-limited, auditable, and subject to governance enforcement.

## Trigger

- Command: `/govern:risk-lifecycle accept|resolve|renew` or agent determines risk action is needed.
- Context: a security/compliance finding needs acceptance, closure, or extension.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"risk"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Finding can be fixed now** — fix it directly, do not accept risk.
- **Policy change needed** — use `adaptive-standards` to evolve the standard.
- **Finding is a false positive** — document as such in decision-store, do not use risk acceptance.

## Mode: Accept

Record a time-limited risk acceptance when immediate remediation is not feasible.

### Procedure

1. **Classify** — identify the finding (source tool, description, affected scope).
2. **Determine severity** — `critical` (exploitable, user-exposed), `high` (exploitable, limited mitigation), `medium` (conditional), `low` (informational).
3. **Assess remediation** — if fixable now, fix it instead. If deferred, document why.
4. **Register** — create decision in `decision-store.json`:
   - `risk_category`: `"risk-acceptance"`
   - `severity`: from step 2
   - `criticality`: derive from severity — `critical` → `critical`, `high` → `high`, `medium` → `medium`, `low` → `low`
   - `follow_up_action`: **mandatory** concrete remediation plan
   - `accepted_by`: actor accepting the risk
   - `acknowledgedBy`: array of all stakeholders who reviewed (e.g., `["user@domain"]`)
   - `expires_at`: ISO 8601 date, auto from severity (Critical 15d, High 30d, Medium 60d, Low 90d) or explicit override
5. **Log** — append `risk-acceptance-created` to audit log.
6. **Verify** — confirm in `ai-eng maintenance risk-status` as `active`.

### Output

- Decision in store with severity, expiry, follow-up action.
- Audit event logged. Gates pass (not yet expired).

## Mode: Resolve

Close a risk acceptance after the finding has been remediated.

### Procedure

1. **Locate** — find decision by ID. Must be `active` or `expired`.
2. **Validate fix** — confirm code change committed, security scan clean, no regression.
3. **Run checks** — `ai-eng gate risk-check` passes, tool-specific scan no longer flags finding.
4. **Close** — mark decision as `remediated` (remains in store for audit trail).
5. **Log** — append `risk-acceptance-remediated` to audit log.
6. **Verify** — decision shows `remediated` in status. Gates green.

### Output

- Decision status `remediated`. Audit event logged. Gates clean.
- Decision NOT deleted — retained for compliance audit.

## Mode: Renew

Extend a risk acceptance before expiry (maximum 2 renewals).

### Procedure

1. **Locate** — find decision by ID. Check `renewal_count`.
2. **Check eligibility** — if `renewal_count >= 2`: **deny**. Remediation is mandatory.
3. **Justify** — require concrete justification (not generic). Update `follow_up_action` if plan changed.
4. **Extend** — create new decision: `renewed_from` = original ID, `renewal_count` + 1, recalculated expiry. Original marked `superseded`.
5. **Log** — append `risk-acceptance-renewed` with renewal count and justification.
6. **Warn on final** — if renewal count = 2: "Final renewal. No further extensions."
7. **Verify** — new decision `active`, original `superseded`, gates pass.

### Output

- New decision linked to original with incremented count.
- Warning on final renewal. Audit event logged.

## Governance Notes

- Risk acceptances are **time-limited** — expire by severity.
- Expired acceptances **block pre-push**, **warn in pre-commit**.
- Maximum **2 renewals** per chain — non-negotiable.
- `follow_up_action` is **mandatory** — no acceptance without remediation plan.
- After 2 renewals: remediate or start a new acceptance chain with fresh justification.
- Partial fixes: do not resolve. Complete the fix or renew.

## References

- `skills/security/SKILL.md` — security assessment procedure.
- `standards/framework/core.md` — risk acceptance non-negotiables.
