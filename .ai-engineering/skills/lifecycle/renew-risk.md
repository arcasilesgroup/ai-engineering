# Renew Risk

## Purpose

Procedure for extending (renewing) a risk acceptance when remediation has not been completed before expiry. Creates a new decision linked to the original, with mandatory justification and enforcement of the maximum renewal limit (2 renewals). Ensures temporary deferrals do not become permanent.

## Trigger

- Command: agent invokes renew-risk skill or user requests extending a risk acceptance.
- Context: a risk acceptance is about to expire or has expired, and the team needs additional time to complete remediation.

## Procedure

### Phase 1: Locate

1. **Identify the decision** — find the risk acceptance by ID in the decision store.
   - Use `ai-eng maintenance risk-status` to list active and expiring risk acceptances.
   - Confirm the decision ID, severity, and current `renewal_count`.

2. **Verify renewal eligibility** — check that max renewals has not been reached.
   - Maximum allowed: 2 renewals.
   - If `renewal_count >= 2`: renewal is **denied**. Remediation is mandatory.
   - Communicate clearly to the user that no more extensions are possible.

### Phase 2: Justify

3. **Require justification** — document why remediation could not be completed.
   - Justification must be concrete and actionable (not generic excuses).
   - Examples: "Upstream dependency v3.0 release delayed to March 2026", "Breaking change requires coordinated deployment across 3 services".
   - The justification becomes part of the new decision's text.

4. **Review follow-up action** — confirm the remediation plan is still valid.
   - If the plan changed, update the `follow_up_action` accordingly.
   - If no viable plan exists, escalate — do not renew.

### Phase 3: Extend

5. **Create renewed decision** — use `renew_decision()` from `decision_logic.py`.
   - Creates a new decision with:
     - `renewed_from`: ID of the original decision.
     - `renewal_count`: original count + 1.
     - `expires_at`: recalculated from severity.
     - `status`: `active`.
   - Marks the original decision as `superseded`.

6. **Log audit event** — append `risk-acceptance-renewed` to audit log.
   - Detail: original decision ID, new decision ID, renewal count, justification.

### Phase 4: Escalate

7. **Issue warning on final renewal** — if this is the 2nd (last) renewal:
   - Emit explicit warning: "This is the final renewal. No further extensions will be granted."
   - Ensure the team understands that remediation MUST complete before this renewal expires.
   - Consider escalating to security reviewer or architect.

### Phase 5: Verify

8. **Confirm renewal** — verify in `ai-eng maintenance risk-status`.
   - New decision should appear as `active` with incremented `renewal_count`.
   - Original decision should show as `superseded`.
   - Pre-push gate should pass (new expiry is in the future).

## Output Contract

- New decision created with `renewed_from` link and incremented `renewal_count`.
- Original decision marked as `superseded`.
- Audit event `risk-acceptance-renewed` logged with renewal count.
- Warning issued if final renewal (count = 2).
- Gates pass with new expiry date.

## Governance Notes

- Maximum 2 renewals per risk acceptance chain. This is **non-negotiable**.
- After 2 renewals, the only options are: remediate (resolve-risk) or accept a new risk (accept-risk) with fresh justification and a new 0-count chain.
- Each renewal resets the expiry timer based on the original severity.
- Renewals create a traceable chain: original → renewal 1 → renewal 2.
- The justification requirement ensures conscious, documented decisions.

## References

- `skills/lifecycle/accept-risk.md` — creating risk acceptances.
- `skills/lifecycle/resolve-risk.md` — closing risk acceptances.
- `skills/swe/security-review.md` — security assessment procedure.
- `standards/framework/core.md` — risk acceptance non-negotiables.
