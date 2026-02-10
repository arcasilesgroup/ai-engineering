---
spec: "003"
closed: "2026-02-10"
---

# Done — Governance Enforcement

## Summary

Spec 003 closes the two critical governance gaps: spec-first enforcement and content integrity validation.

## Delivered

### New Skills (4)

| Skill | Purpose |
|-------|---------|
| `lifecycle/create-spec.md` | Spec creation with branch-first workflow (feat/*, bug/*, hotfix/*) |
| `lifecycle/delete-skill.md` | Safe skill removal with dependency checks |
| `lifecycle/delete-agent.md` | Safe agent removal with dependency checks |
| `lifecycle/content-integrity.md` | 6-category governance content validation |

### Enforcement Rules

- **Spec-First Enforcement** section added to `standards/framework/core.md` — non-trivial changes require active spec.
- **Content Integrity Enforcement** section added to `standards/framework/core.md` — post-change validation mandatory.
- **Session Contract** updated with spec-first fallback and post-change validation rules.
- **Framework-contract 9.5** updated: step 2 (spec-first check), step 7 (content-integrity).
- **manifest.yml** `close_actions` includes `validate_content_integrity`.

### Agent Expansion

- `verify-app.md` expanded with content integrity capability and behavior step 9.

### Integration

- All 6 instruction files list 6 lifecycle skills.
- Product-contract counters: 25 skills, 8 agents.
- CHANGELOG updated with 7 new entries.
- Cross-references bidirectional across all new and modified skills/agents.

## Verification Results

| Check | Result |
|-------|--------|
| Canonical/mirror pairs byte-identical | 9/9 PASS |
| 6 instruction files × 6 lifecycle skills | 6/6 PASS |
| Product-contract counter = 25 skills, 8 agents | PASS |
| All 6 instruction files consistent (25 skills, 8 agents) | PASS |

## Deferred

- Automated hook-based content integrity enforcement (D4 — content-first principle, skill for now).
- Python implementation of content-integrity checks (future spec).
