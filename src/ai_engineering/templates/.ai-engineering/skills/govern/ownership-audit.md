# Ownership Audit

## Purpose

Validates ownership boundary enforcement, updater safety, and decision/audit-log integrity. Ensures that framework update flows respect ownership levels, that the decision store schema is consistent, and that audit-log events reconcile with recorded decisions.

## Trigger

- Command: agent invokes ownership-audit skill or user requests ownership boundary review.
- Context: post-update validation, pre-release safety check, governance integrity audit.

## Procedure

### Phase 1: Ownership Boundary Validation

1. **Load ownership model** — read `manifest.yml` ownership section.
   - Extract all ownership levels: framework_managed, team_managed, project_managed, system_managed.
   - Extract external_framework_managed paths.
   - Build a complete ownership map of every governed path.

2. **Verify boundary correctness** — for each file in `.ai-engineering/`, confirm ownership assignment.
   - Every file must map to exactly one ownership level.
   - No file should fall outside the ownership model (orphaned files).
   - Report any ambiguous or conflicting ownership assignments.

3. **Audit updater safety** — verify that framework update behavior respects ownership.
   - Framework-managed files: updater MAY overwrite.
   - Team-managed files: updater MUST NOT overwrite without explicit merge.
   - Project-managed files: updater MUST NOT touch.
   - System-managed files: updater MUST NOT overwrite (append-only for logs, schema-safe for JSON).
   - Check installer/updater code paths for overwrite safety.

4. **Verify idempotency** — confirm that running install/update twice produces identical results.
   - No duplicate entries, no file corruption, no state drift.
   - Template files remain byte-identical to canonical after re-install.

### Phase 2: Decision Store Integrity

5. **Validate schema** — verify `state/decision-store.json` structure.
   - Schema version must be present and valid.
   - Required fields per decision: id, context, decision, decidedAt, spec.
   - Optional fields must match allowed types when present.
   - No duplicate decision IDs.

6. **Check decision consistency** — validate decision content coherence.
   - Referenced specs must exist (or be "none" for global decisions).
   - Decision dates must be valid ISO 8601.
   - No contradictory decisions (same context, opposing conclusions).

### Phase 3: Audit Log Integrity

7. **Validate audit-log structure** — check `state/audit-log.ndjson` format.
   - Each line must be valid JSON (NDJSON format).
   - Required fields per event: timestamp, event, details.
   - Timestamps must be chronologically ordered.

8. **Cross-check events vs decisions** — verify event-to-decision consistency.
   - Risk acceptance events should have corresponding decision-store entries.
   - Decision revocations should have corresponding audit-log events.
   - No orphan events (events referencing non-existent decisions).

### Phase 4: Report

9. **Produce ownership audit report** — structured findings.
   - Boundary validation results per ownership level.
   - Updater safety assessment.
   - Decision store integrity status.
   - Audit log consistency status.
   - Overall compliance verdict.

## Output Contract

```
## Ownership Audit Report

### Boundary Validation
- Status: PASS | FAIL
- Files audited: N
- Ownership violations: [list]

### Updater Safety
- Status: PASS | FAIL
- Overwrite risks: [list]
- Idempotency: VERIFIED | VIOLATED

### Decision Store Integrity
- Status: PASS | FAIL
- Decisions: N total, N valid, N invalid
- Issues: [list]

### Audit Log Consistency
- Status: PASS | FAIL
- Events: N total
- Orphan events: N
- Issues: [list]

### Overall: PASS | FAIL (N/4 sections passed)
```

## Governance Notes

- Ownership boundaries are a security-critical governance control — violations are blocker severity.
- Team-managed and project-managed content must never be overwritten by framework update flows.
- Decision store is system-managed — only governed workflows may modify it.
- Audit log is append-only — any evidence of modification or deletion is a critical finding.
- This skill complements `integrity-check` (structural) with behavioral and semantic validation.

## References

- `manifest.yml` — ownership model definition.
- `standards/framework/core.md` — ownership levels and update safety rules.
- `skills/govern/integrity-check.md` — structural validation (complementary).
- `skills/govern/accept-risk.md` — risk acceptance workflow that writes to decision store.
- `skills/govern/resolve-risk.md` — risk resolution workflow.
- `skills/govern/renew-risk.md` — risk renewal workflow.
- `agents/platform-auditor.md` — orchestrator that invokes this skill.
