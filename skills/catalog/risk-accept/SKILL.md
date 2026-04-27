---
name: risk-accept
description: Use to log-accept a finding that blocks a gate but the team accepts the risk — interrogates for finding-id, severity, justification, owner, spec-ref, then writes an audit log entry per ADR-0002. Logged-acceptance with TTL, never weakening. Trigger for "accept this risk", "I'll fix this later", "TTL accept", "log this finding for now".
effort: medium
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: true
---

# /ai-risk-accept

Promotes the `ai-eng risk accept` CLI verb to a first-class skill.
Interrogates the user for the metadata that distinguishes
**logged-acceptance** from **weakening**, writes a hash-chained entry
to `decision-store.json`, and emits an immutable audit-log line per
ADR-0002.

> **Logged-acceptance is NOT weakening.** Weakening is modifying
> severity thresholds, adding suppression comments, or disabling hooks.
> Logged-acceptance is recording an explicit decision with TTL, owner,
> and spec ref so the next gate run sees the entry.

## When to use

- A `/ai-verify` or `/ai-security` finding blocks merge, but the team
  decides to ship and remediate later
- A `governance` boundary check flags scope drift that the spec author
  intentionally introduced
- A dependency CVE has no available patch and the exploit path is mitigated
  by another control
- A `/ai-eval` regression is acknowledged (e.g. provider outage) and
  shouldn't block release

## Required interrogation

The skill REFUSES to write an entry without all six fields:

| Field | Validation |
|-------|------------|
| `finding-id` | matches an ID in the latest verify/security/governance run |
| `severity` | one of `critical | high | medium | low` |
| `justification` | ≥ 1 sentence, must answer "why ship over fix" |
| `owner` | human accountable; not a team alias |
| `spec-ref` | active spec id (`spec-NNN`) or explicit `non-spec-emergency` |
| `ttl` | derived from severity unless overridden with maintainer approval |

## TTL by severity

| Severity | Default TTL |
|----------|-------------|
| `critical` | 7 days |
| `high` | 30 days |
| `medium` | 90 days |
| `low` | 180 days |

Overriding TTL requires maintainer approval AND a separate
`risk-accept` for the override decision (recursion intentional — no
silent extensions).

## Process

1. **Resolve finding-id** — read the latest run state. Reject if the
   ID isn't present or is already accepted.
2. **Interrogate** the six fields. Cap at 6 questions, one at a time.
3. **Compute TTL** from severity. Confirm with user before persisting.
4. **Write decision-store entry** — hash-chained append:

   ```json
   {
     "id": "FIN-2026-0427-0001",
     "finding-id": "GITLEAKS-AWS-KEY-1284",
     "severity": "high",
     "justification": "Test fixture key, not live; rotated in 90d sweep.",
     "owner": "ana@example.com",
     "spec-ref": "spec-073",
     "accepted-at": "2026-04-27T18:00:00Z",
     "expires-at": "2026-05-27T18:00:00Z",
     "follow-up": "spec-073 task T-09 rotates all fixture creds"
   }
   ```

5. **Emit audit event** — `risk.accepted` to `framework-events.ndjson`
   with the entry id and hash.
6. **Return entry id** so the user can reference it in PR / commit body.

## Hard rules

- NEVER accept without all six required fields. Skill refuses.
- NEVER override default TTL without maintainer approval AND a nested
  `risk-accept` for the override.
- NEVER edit `decision-store.json` outside this flow — the hash chain
  breaks and audit invalidates (Article VII).
- Owner MUST be a human, not a team alias — accountability requires a
  name.
- Justification MUST answer "why ship now". "fix later" is not a
  justification.

## Common mistakes

- Treating risk-accept as suppression ("we'll just accept the risk")
- Owner = "@platform-team" — alias, not human; auditors reject this
- Empty / vague justification ("known issue, will address")
- Forgetting `spec-ref` — orphaned acceptances expire silently
- Letting TTL expire without renewal or remediation — governance audit
  flags this in `risk.expired`
- Hand-editing `decision-store.json` to "fix" an entry — breaks the
  hash chain
