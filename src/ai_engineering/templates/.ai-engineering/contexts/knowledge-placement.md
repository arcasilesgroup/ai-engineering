# Framework Knowledge Placement

Shared reference for where durable framework knowledge belongs. This file captures the phase-1 placement contract from spec-116 so later cleanup tasks promote rules into the right governed surface instead of copying them across lessons, contexts, overlays, and generated mirrors.

## Placement Matrix

| Knowledge class | Canonical home | Use this home when | Retain elsewhere when |
|---|---|---|---|
| Skill contracts | Canonical `SKILL.md` for the relevant skill | The rule changes trigger conditions, procedure, inputs, outputs, or tool expectations for one skill | The rule is cross-skill guidance, temporary discovery, or team-local policy |
| Agent orchestration | The relevant agent definition | The rule changes delegation, boundaries, handoffs, review order, write scope, or execution mode for one agent | The rule is a user-facing workflow contract or reusable framework guidance |
| Machine-readable metadata | `.ai-engineering/manifest.yml` | The content is structured, bounded, and consumed by validators, sync, install, hooks, or runtime logic | The content is explanatory prose, rationale, or operator guidance |
| Cross-IDE governance rules | `AGENTS.md` or the relevant framework-owned root entry-point overlay | The rule governs root startup, host-specific behavior, mirror expectations, or the cross-IDE operating contract | The rule is reusable framework guidance or a mirror-path detail that does not need separate governance |
| Reusable framework guidance | Shared root context under `.ai-engineering/contexts/` | The rule is durable across multiple skills, agents, or IDE surfaces and is best read as guidance rather than schema | The rule is team-specific or belongs in Constitution-level hard rules |
| Learning funnel artifacts | `.ai-engineering/LESSONS.md`, `.ai-engineering/instincts/instincts.yml`, `.ai-engineering/instincts/proposals.md` | The content is newly observed, heuristic, disputed, incomplete, or waiting for a better governed home | The rule has become repeatable and a canonical surface can own it |
| Decision and risk records | `.ai-engineering/state/decision-store.json` | The entry is a formal architecture or governance decision, or an active or accepted risk that needs lifecycle metadata | The content is a solved implementation note, style advice, or temporary audit finding |
| Team-local conventions | `.ai-engineering/contexts/team/**` | The rule is project-specific, organization-specific, or intentionally overrides framework defaults | The rule generalizes across repositories and should move to a framework-owned surface |

## Decision Rules

- Place by enforcement target, not by where the rule was first discovered.
- Use one neutral canonical home. Generated mirrors, copied templates, and IDE-specific projections are distribution surfaces, not separate knowledge classes.
- Do not promote mirror-source drift into this matrix. If root-surface ownership is already governed elsewhere, reference that contract instead of creating a second source-of-truth rule here.

## Promotion Test

Move a finding out of `.ai-engineering/LESSONS.md`, `.ai-engineering/instincts/instincts.yml`, or `.ai-engineering/instincts/proposals.md` only when all of these are true:

1. The pattern repeated across more than one task, review, or framework surface.
2. A governed canonical home can own or validate it today.
3. Leaving it in the funnel would force future work to guess where the rule belongs.

Retain the finding in the funnel when any condition fails. Drop it instead of promoting it when it is obsolete, superseded, or already covered by an existing canonical rule.

## Governance Notes

- Rationale: give spec-116 a single placement contract before cleanup moves content.
- Expected gain: later tasks can classify rules consistently and avoid recreating mirror or ownership drift.
- Potential impact: future promotion, cleanup, and metadata tasks should use this matrix before moving content between governed surfaces.