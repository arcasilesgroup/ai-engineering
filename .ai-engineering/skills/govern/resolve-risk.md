# Resolve Risk

## Purpose

Procedure for closing a risk acceptance after the underlying finding has been remediated. Marks the decision as `remediated` in the decision store, logs the resolution, and verifies that governance gates pass cleanly.

## Trigger

- Command: agent invokes resolve-risk skill or user reports a risk finding has been fixed.
- Context: a previously accepted risk has been remediated — the vulnerability patched, dependency updated, or policy violation corrected.

## Procedure

### Phase 1: Locate

1. **Identify the decision** — find the risk acceptance by ID in the decision store.
   - Use `ai-eng maintenance risk-status` to list active risk acceptances.
   - Confirm the decision ID, severity, and context match the resolved finding.

2. **Verify the decision is active** — only active or expired decisions can be resolved.
   - Status must be `active` or `expired`. Cannot resolve already-remediated or revoked decisions.

### Phase 2: Validate

3. **Confirm remediation** — verify the fix is actually implemented.
   - Code change committed and tested.
   - Security scan passes clean for the specific finding.
   - Dependency updated to non-vulnerable version (if applicable).
   - No regression introduced by the fix.

4. **Run verification checks** — execute relevant gate checks.
   - `ai-eng gate risk-check` should pass after remediation.
   - Tool-specific check (e.g., `pip-audit`, `semgrep`) should no longer flag the finding.

### Phase 3: Close

5. **Mark as remediated** — update decision store.
   - Use `mark_remediated()` from `decision_logic.py`.
   - Sets `status` to `"remediated"`.
   - Decision remains in store for audit trail.

6. **Log audit event** — append `risk-acceptance-remediated` to audit log.
   - Detail: decision ID, original severity, remediation description.

### Phase 4: Verify

7. **Confirm resolution** — verify the decision no longer appears as active risk.
   - `ai-eng maintenance risk-status` should show status as `remediated`.
   - Pre-push gate should pass without risk-related warnings.
   - If this was the last expired risk, all gates should be green.

## Output Contract

- Decision status updated to `remediated` in `decision-store.json`.
- Audit event `risk-acceptance-remediated` logged.
- Gate checks pass cleanly (no expired risk warnings/blocks).
- Decision remains in store for historical audit trail.

## Governance Notes

- Resolving a risk acceptance is the **expected outcome** — every risk should be remediated.
- The decision is NOT deleted — it stays in the store with `remediated` status for compliance audit.
- If the fix is partial, do not resolve. Either complete the fix or renew the risk acceptance.
- After resolution, the risk no longer counts toward gate enforcement or health score.

## References

- `skills/govern/accept-risk.md` — creating risk acceptances.
- `skills/govern/renew-risk.md` — extending risk acceptances.
- `skills/review/security.md` — security assessment procedure.
- `standards/framework/core.md` — risk acceptance non-negotiables.
