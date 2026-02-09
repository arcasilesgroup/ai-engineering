# Product Vision

## Update Metadata

- Rationale: synchronize product intent with locked governance and command decisions.
- Expected gain: consistent implementation direction across teams and agents.
- Potential impact: old assumptions are retired in favor of enforceable defaults.

## Problem

AI-assisted delivery is fast but inconsistent without enforceable governance. Teams need one practical framework that keeps speed while preventing drift, weak security, and context sprawl.

## Product Goal

Build `ai-engineering` as an OSS framework that provides:

- one canonical governance root: `.ai-engineering/`.
- strict local enforcement (non-bypassable hooks + mandatory security checks).
- governed agentic execution for Claude, Codex, and Copilot.
- low token/context overhead through compact, high-signal docs.

## Non-Negotiables

- Lifecycle is enforced: Discovery -> Architecture -> Planning -> Implementation -> Review -> Verification -> Testing -> Iteration.
- Security and quality checks run locally and must be fixed locally.
- Framework updates never overwrite team-managed or project-managed content.
- Remote skills are allowed by default but locked, cached, and integrity-checked.

## Personas

- Platform engineer: defines reusable governance and rollout at scale.
- Team lead: needs predictable quality and auditable decisions.
- Developer: wants fast workflows with guardrails that are clear and consistent.
- Security/AppSec: requires verifiable local controls and traceability.
- DevEx owner: tracks adoption, friction, and quality impact.

## Command UX Contract

- `/commit`: stage + commit + push current branch.
- `/commit --only`: stage + commit.
- `/pr`: stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`).
- `/pr --only`: create PR; warn if branch is not pushed and propose auto-push.
- `/acho`: stage + commit + push current branch.
- `/acho pr`: stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`).

## Success Metrics

- 100 percent mandatory gate execution on governed operations.
- 0 ungated sensitive operations.
- Time to first governed commit under 5 minutes.
- Context compaction trend improving release-over-release.
