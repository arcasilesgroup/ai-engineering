# Iteration and Maintenance

## Update Metadata

- Rationale: codify maintenance-agent and decision-reuse behavior.
- Expected gain: sustained context quality with less prompt fatigue.
- Potential impact: periodic reviews become part of normal operations.

## Cadence

- weekly: maintenance agent local report.
- bi-weekly: sprint retrospective and backlog adjustments.
- monthly: governance KPI review.

## Maintenance Agent Contract

- audits context bloat, redundancy, stale decisions, and source alignment.
- proposes safe simplifications with rationale, expected gain, and potential impact.
- outputs local report first.
- creates PR only after explicit approval.

## Decision Reuse Rules

- check `state/decision-store.json` before prompting users again.
- skip repeat prompts when a valid decision matches scope and context.
- re-prompt only on expiration or material context/policy/severity change.

## Core KPIs

- gate compliance rate.
- mean remediation time for failed checks.
- context redundancy delta.
- command success rates by flow.

## Telemetry

- strict opt-in only.
- no secrets or source payload collection.
