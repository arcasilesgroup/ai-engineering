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
| `## References` | Links to related PRs, work items, docs, and research artifacts. Each entry uses a `<prefix>:` convention so downstream tooling can route by source: `pr:`, `work-item:`, `doc:`, `research:`, etc. Research artifacts produced by `/ai-research` are cited as `- research: .ai-engineering/research/<artifact>.md` (relative to repo root). |
| `## Open Questions` | Unresolved items pending decisions. |

### Reference Prefix Convention

The `## References` section accepts entries of the form `- <prefix>: <target>` where `prefix` names the source class. Recognized prefixes:

| Prefix | Target shape | Source |
|--------|--------------|--------|
| `pr` | `<owner>/<repo>#<number>` or full URL | Pull request |
| `work-item` | platform-native id (e.g., `GH-123`, `AB#456`) | GitHub Issues / Azure Boards |
| `doc` | URL or repo-relative path | External or in-repo documentation |
| `research` | `.ai-engineering/research/<artifact>.md` | `/ai-research` artifact |

New prefixes must follow the same shape so tooling can resolve them uniformly.

## Validation Rules

1. All required sections must be present before `status` transitions to `approved`.
2. Every decision entry must have a rationale (choice alone is insufficient).
3. Non-Goals must contain at least one item.
4. Frontmatter fields must all be present and non-empty.
