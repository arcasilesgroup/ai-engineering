# Spec Schema

Contract for `specs/spec.md` files produced by `/ai-brainstorm` and consumed by `/ai-plan`.

## Required Frontmatter

| Field | Type | Example |
|-------|------|---------|
| `spec` | string | `spec-082` |
| `title` | string | `Skill Surface Refactor` |
| `status` | enum | `draft` \| `approved` \| `in-progress` \| `done` |
| `effort` | enum | `trivial` \| `small` \| `medium` \| `large` |

## Required Sections

| Section | Content |
|---------|---------|
| `## Summary` | One-paragraph problem statement. What is broken and why it matters. |
| `## Goals` | Bulleted list of success criteria. Each goal is verifiable. |
| `## Non-Goals` | Explicit scope exclusions. Must be non-empty to prevent scope creep. |
| `## Decisions` | Numbered `D-NNN-NN` entries. Each must include a rationale, not just a choice. |
| `## Risks` | Identified risks with mitigations. |

## Optional Sections

| Section | Content |
|---------|---------|
| `## References` | Links to related PRs, work items, docs. |
| `## Open Questions` | Unresolved items pending decisions. |

## Validation Rules

1. All required sections must be present before `status` transitions to `approved`.
2. Every decision entry must have a rationale (choice alone is insufficient).
3. Non-Goals must contain at least one item.
4. Frontmatter fields must all be present and non-empty.
