# Accept Risk

## Purpose

Procedure for accepting a security or compliance risk when immediate remediation is not feasible. Records the acceptance in the decision store with severity classification, mandatory follow-up action, and time-limited expiry. Ensures every risk acceptance is tracked, auditable, and subject to governance enforcement.

## Trigger

- Command: agent invokes accept-risk skill or user requests accepting a security finding.
- Context: a security scan (gitleaks, semgrep, pip-audit) or review has identified a finding that cannot be remediated immediately, and the team decides to accept the risk temporarily.

## Procedure

### Phase 1: Classify

1. **Identify the finding** — determine the exact vulnerability, CVE, or policy violation.
   - Source: which tool or review flagged it (gitleaks, semgrep, pip-audit, manual review).
   - Description: concrete description of the risk.
   - Affected scope: which files, packages, or components are impacted.

2. **Determine severity** — classify as `critical`, `high`, `medium`, or `low`.
   - Critical: exploitable vulnerability with no mitigation, exposed to users.
   - High: exploitable vulnerability with limited mitigation or internal exposure.
   - Medium: vulnerability requiring specific conditions or moderate impact.
   - Low: informational finding or minimal impact.

### Phase 2: Evaluate

3. **Assess immediate remediation** — can the finding be fixed now?
   - If yes: fix it. Do not accept risk. Use standard fix → commit → push flow.
   - If no: document why remediation is deferred (dependency not available, breaking change required, upstream fix pending).

### Phase 3: Document

4. **Register in decision store** — create risk acceptance decision.
   - Use `create_risk_acceptance()` from `decision_logic.py`.
   - Required fields:
     - `risk_category`: `"risk-acceptance"`
     - `severity`: determined in Phase 1
     - `follow_up_action`: **mandatory** — concrete remediation plan
     - `accepted_by`: actor accepting the risk
     - `expires_at`: auto-calculated from severity (Critical 15d, High 30d, Medium 60d, Low 90d) or explicit override
   - Context should include: tool name, finding description, affected scope.

5. **Log audit event** — append `risk-acceptance-created` to audit log.
   - Detail: decision ID, severity, expiry date, follow-up action.

### Phase 4: Verify

6. **Confirm registration** — verify the decision appears in `ai-eng maintenance risk-status`.
   - Decision should show as `active` with correct severity and expiry.
   - Follow-up action should be documented.

7. **Verify gates pass** — the pre-push gate should pass (risk is not expired yet).

## Output Contract

- Decision registered in `decision-store.json` with all risk fields populated.
- Audit event `risk-acceptance-created` logged.
- Follow-up action documented (mandatory, non-empty).
- Expiry date set according to severity.
- Risk visible in `ai-eng maintenance risk-status` output.

## Governance Notes

- Risk acceptances are **time-limited** — they expire based on severity.
- Expired risk acceptances **block pre-push** and **warn in pre-commit**.
- Maximum 2 renewals allowed. After that, remediation is mandatory.
- `follow_up_action` is mandatory — cannot accept risk without a remediation plan.
- Follow the `resolve-risk` skill to close after remediation.
- Follow the `renew-risk` skill to extend if more time is needed.

## References

- `skills/lifecycle/resolve-risk.md` — closing a risk acceptance after fix.
- `skills/lifecycle/renew-risk.md` — extending a risk acceptance.
- `skills/swe/security-review.md` — security assessment procedure.
- `standards/framework/core.md` — risk acceptance non-negotiables.
