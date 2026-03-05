---
spec: "035"
approach: "serial-phases"
---

# Plan — Extend feature-gap with wiring detection

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `context/specs/035-feature-gap-wiring/spec.md` | Spec definition |
| `context/specs/035-feature-gap-wiring/plan.md` | This plan |
| `context/specs/035-feature-gap-wiring/tasks.md` | Task tracking |

### Modified Files

| File | Change |
|------|--------|
| `skills/feature-gap/SKILL.md` | Add wiring detection: metadata, purpose, procedure step 5.5, output section |
| `agents/scan.md` | Update feature-gap mode description + threshold |
| `context/specs/_active.md` | Point to spec 035 |

### Mirror Copies

None.

## File Structure

```
.ai-engineering/
├── context/specs/035-feature-gap-wiring/
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
├── skills/feature-gap/SKILL.md  (modified)
└── agents/scan.md               (modified)
```

## Session Map

### Phase 0 — Scaffold [S]

Create spec branch, scaffold spec/plan/tasks, activate.

### Phase 1 — Update feature-gap skill [S]

- Update metadata (description, tags)
- Update Purpose section
- Add procedure step 5.5 (wiring gap detection)
- Add Wiring Matrix to Output section

### Phase 2 — Update scan agent [S]

- Update mode table description for feature-gap
- Update threshold table entry for feature-gap

### Phase 3 — Validate [S]

- Read updated files and verify coherence
- Run `ai-eng validate` for integrity
- Verify acceptance criteria

## Patterns

- **Agent**: build (ONLY code/content write agent)
- **Commit per phase**: `spec-035: Phase N — <description>`
- **Governance**: both files are framework-managed; changes are planned governance evolution
- **Backward compatibility**: output contract extends (new section), existing sections unchanged
