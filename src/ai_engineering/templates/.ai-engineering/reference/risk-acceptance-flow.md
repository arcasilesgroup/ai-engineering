# Risk acceptance flow (spec-105)

End-to-end lifecycle for `ai-eng risk *` -- the canonical CLI surface that
records, lists, renews, resolves, and revokes governance bypass decisions
written to `.ai-engineering/state/decision-store.json`.

## When to accept a risk

Accept a finding only when:

1. The pre-push or pre-merge gate emits a blocking finding.
2. The remediation cannot land before the publish window closes.
3. A defensible audit trail is acceptable (justification, spec ref,
   follow-up plan, owner, TTL).

Examples that justify acceptance:

- Critical CVE in a transitive dependency upstream-patched but unreleased
  -- accept, follow up when the next release lands.
- Legacy module flagged by a new semgrep rule that fires repository-wide
  -- accept the batch, schedule a sweep refactor next sprint.

Examples that do NOT justify acceptance:

- "Tests are flaky." Fix the flake.
- "I don't understand the finding." Read the rule docs first.
- "We always disable this rule." Change the project's ruleset, not the
  per-finding acceptance log.

## CLI surface (D-105-05)

`ai-eng risk` exposes seven subcommands. All of them mutate
`state/decision-store.json` through `decision_logic` -- never edit the
JSON file by hand.

| Command | Purpose |
|---|---|
| `accept` | Record a single risk-acceptance for one finding. |
| `accept-all` | Bulk-accept every finding in a `gate-findings.json` artefact, sharing one `batch_id`. |
| `renew` | Extend a DEC entry's TTL by reissuing it (capped at `_MAX_RENEWALS=2`). |
| `resolve` | Mark an acceptance as remediated (the underlying finding is fixed). |
| `revoke` | Revoke an active acceptance with a reason (e.g., justification was wrong). |
| `list` | List acceptances filtered by status, severity, or expiry window. |
| `show` | Print a single DEC entry's full detail. |

### `accept-all` -- the most common entry point

```bash
ai-eng risk accept-all .ai-engineering/state/gate-findings.json \
  --justification "Q3 cutoff; remediation tracked in JIRA-1234." \
  --spec spec-NNN \
  --follow-up "Resolve all findings in 2026-Q3 sprint." \
  [--max-severity medium] \
  [--expires-at 2026-07-01T00:00:00Z] \
  [--accepted-by alice@example.com] \
  [--dry-run]
```

Behaviour:

- Reads the findings artefact (schema v1 or v1.1).
- Generates one shared `batch_id` (uuid4) for all entries created in this
  invocation.
- Writes one `DEC-*` entry per finding to `state/decision-store.json`
  with TTL from `_SEVERITY_EXPIRY_DAYS` (critical=15d, high=30d,
  medium=60d, low=90d) unless `--expires-at` overrides.
- Emits `category=risk-acceptance, control=finding-bypassed` telemetry
  per acceptance.
- Prints a compact summary table to stdout.

`--dry-run` prints the summary without writing any DEC entries -- useful
to preview what `accept-all` would do.

`--max-severity low` caps the bulk operation to findings whose severity
is at most `low`, leaving any higher-severity findings unaccepted.

### Single-finding `accept`

```bash
ai-eng risk accept FIND-001 \
  --severity high \
  --justification "Pinned upstream CVE; awaiting release." \
  --spec spec-NNN \
  --follow-up "Bump dependency in 2026-Q3."
```

Use when only one finding needs an acceptance and bulk semantics would be
misleading. Identical lifecycle to `accept-all`-created entries.

## Lifecycle: renew / resolve / revoke

Once a DEC entry exists, three operations can change its state.

### Renew (extend TTL)

```bash
ai-eng risk renew DEC-XXX \
  --justification "Upstream release slipped to 2026-Q4." \
  --spec spec-NNN
```

Increments `renewal_count`, sets `renewed_from = DEC-XXX-PRIOR`, recomputes
`expires_at` from current severity TTL. Capped at `_MAX_RENEWALS=2` per
chain -- a third renewal is rejected with exit 2 to force a human
re-evaluation.

### Resolve (the finding is fixed)

```bash
ai-eng risk resolve DEC-XXX --note "pygments bumped to 2.18.0; CVE-2026-1234 patched."
```

Sets `status = remediated`. The next `gate run` no longer matches this DEC
because the underlying finding is gone. The entry stays in
`decision-store.json` for audit history.

### Revoke (the acceptance was wrong)

```bash
ai-eng risk revoke DEC-XXX --reason "Justification did not actually apply; finding remains unaddressed."
```

Sets `status = revoked`. The next `gate run` re-blocks the matching
finding because revoked acceptances are not honoured.

## Prototyping vs regulated mode interaction (D-105-02 / D-105-03)

| Mode | Tier 0 (always) | Tier 1 (always) | Tier 2 (governance) | Risk acceptance |
|---|---|---|---|---|
| `regulated` (default) | runs + blocks | runs + blocks | runs + blocks | applies through `apply_risk_acceptances` to all tiers |
| `prototyping` | runs + blocks | runs + blocks | skipped | applies to Tier 0+1 findings that DID run |

Branch-aware escalation: when `current_branch` matches a protected
pattern (e.g., `main`, `master`, `release/*`), the framework forces
regulated mode regardless of `manifest.gates.mode`. CI environments (any
of `CI`, `GITHUB_ACTIONS`, `TF_BUILD` set truthy) also force regulated
mode. So a project that declares `gates.mode: prototyping` in its
manifest can still benefit from acceptances on Tier 0+1 findings during
spike work, but will execute the full tier matrix the moment a push
targets a protected branch or a CI run starts.

## Audit trail

Every operation writes to two places:

1. **Decision store** -- `.ai-engineering/state/decision-store.json`.
   Each DEC carries the full lineage: kind, context (`finding:<rule_id>`),
   severity, justification, spec ref, follow-up plan, accepted_by,
   created_at, expires_at, status, renewal_count, renewed_from, batch_id.
   Auditors read this file directly.

2. **Framework events** -- `.ai-engineering/state/framework-events.ndjson`.
   Each operation emits a `kind=control_outcome` event with
   `category=risk-acceptance` and a `control` field naming the action
   (`finding-bypassed`, `acceptance-renewed`, `acceptance-resolved`,
   `acceptance-revoked`, `bulk-accept-summary`). Downstream tooling
   (Slack/email notifications, compliance dashboards) tails this NDJSON
   stream.

`ai-eng risk list --format json --status active` emits a structured view
of every active acceptance. `--expires-within 7` filters to entries
expiring in the next 7 days -- run as a weekly hygiene cron.

## End-to-end scenario A: bulk acceptance for a publish window

```bash
# 1. Run the gate; it fails with 3 findings.
ai-eng gate run --json
# exit 1; gate-findings.json contains 3 findings (1 medium pip-audit, 2 low ruff).

# 2. Determine all 3 are tracked elsewhere and the publish window is now.
ai-eng risk accept-all .ai-engineering/state/gate-findings.json \
  --justification "Q2 publish cutoff; remediation tracked in JIRA-EPIC-42." \
  --spec spec-NNN \
  --follow-up "Sprint of 2026-Q3 closes all 3 findings."

# 3. Re-run the gate; 0 blocking findings.
ai-eng gate run --json
# exit 0; gate-findings.json shows accepted_findings[] with 3 entries
# and an expiring_soon[] banner if any DEC is within 7d of expiry.

# 4. Publish.
gh pr create ...
```

## End-to-end scenario B: renewal then resolution

```bash
# Day 0: accept a critical CVE (15d TTL).
ai-eng risk accept FIND-CVE-2026-1234 \
  --severity critical \
  --justification "Upstream patch ETA 2026-05-15." \
  --spec spec-NNN \
  --follow-up "Bump dependency when patch ships."

# Day 14: patch slipped. Renew (now 30d TTL on the renewal chain).
ai-eng risk renew DEC-001 \
  --justification "Upstream slipped to 2026-Q3." \
  --spec spec-NNN

# Day 40: dependency bumped, CVE patched.
ai-eng risk resolve DEC-001 --note "pygments==2.18.0 patched CVE-2026-1234."
```

`ai-eng risk show DEC-001 --format json` after resolution shows the full
lineage (created_at, renewal_count=1, status=remediated, renewed_from
chain) for auditor review.

## End-to-end scenario C: revoke a wrong acceptance

```bash
# Acceptance was created in haste; on second look the justification
# does not actually apply.
ai-eng risk revoke DEC-002 \
  --reason "Justification cited JIRA-9999 but that ticket covers a different finding."

# Next gate run re-blocks the matching finding.
ai-eng gate run --json
# exit 1; finding is back in blocking[].
```

## Cross-references

- `.ai-engineering/contexts/gate-policy.md` -- how the orchestrator
  consumes risk acceptances during gate runs.
- `.ai-engineering/specs/spec.md` D-105-01..D-105-14 -- the underlying
  decisions.
- `CLAUDE.md` Don't #9 -- risk acceptance via `accept` / `accept-all` is
  logged-acceptance with TTL, owner, spec ref, and follow-up. It is NOT
  weakening a gate, threshold, or severity level (which would require
  the full protocol with `state/decision-store.json` risk acceptance,
  framework-events emission, etc.).
