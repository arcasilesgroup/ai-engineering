---
spec: "003"
approach: "serial-phases"
---

# Plan — Governance Enforcement

## Architecture

### New Files

| File | Type | Purpose |
|------|------|---------|
| `skills/lifecycle/create-spec.md` | Skill | Spec creation with branch-first workflow |
| `skills/lifecycle/delete-skill.md` | Skill | Safe skill removal with dependency checks |
| `skills/lifecycle/delete-agent.md` | Skill | Safe agent removal with dependency checks |
| `skills/lifecycle/content-integrity.md` | Skill | 6-category governance content validation |

### Modified Files

| File | Change |
|------|--------|
| `agents/verify-app.md` | Add content integrity capability + behavior step |
| `standards/framework/core.md` | Add Spec-First and Content Integrity Enforcement sections |
| `context/product/framework-contract.md` | Add steps 0 and 7 to section 9.5 |
| `manifest.yml` | Add `validate_content_integrity` to close_actions |
| `skills/lifecycle/create-skill.md` | Add refs to delete-skill, content-integrity |
| `skills/lifecycle/create-agent.md` | Add refs to delete-agent, content-integrity |
| 6 instruction files | Add 4 new lifecycle skills |
| `context/product/product-contract.md` | Update counters 21→25 skills |
| `CHANGELOG.md` | Add 4 new skill entries |

### Mirror Copies

Each new skill gets a byte-identical mirror in `src/ai_engineering/templates/.ai-engineering/skills/lifecycle/`.
Modified canonical files with mirrors get their mirrors updated.

## File Structure

```
.ai-engineering/
  skills/lifecycle/
    create-spec.md       (NEW)
    delete-skill.md      (NEW)
    delete-agent.md      (NEW)
    content-integrity.md (NEW)
  agents/
    verify-app.md        (MODIFIED)
  standards/framework/
    core.md              (MODIFIED)
  context/
    product/
      framework-contract.md (MODIFIED)
      product-contract.md   (MODIFIED)
    specs/
      003-governance-enforcement/
        spec.md    (NEW)
        plan.md    (NEW)
        tasks.md   (NEW)
        done.md    (NEW — at closure)
```

## Session Map

Single-agent serial execution. All 8 phases are serial.

| Phase | Scope | Size | Description |
|-------|-------|------|-------------|
| 0 | Scaffold | S | Spec files, branch, _active.md |
| 1 | create-spec | L | New skill + registration |
| 2 | delete-skill + delete-agent | L | Two new skills + registration |
| 3 | content-integrity | L | New skill + registration |
| 4 | verify-app expansion | S | Agent update + mirror |
| 5 | Enforcement rules | M | core.md, framework-contract.md, manifest.yml |
| 6 | Update existing lifecycle skills | S | Cross-refs in create-skill, create-agent |
| 7 | Integration | M | Instruction files, counters, changelog, cross-refs |
| 8 | Verify + Closure | S | Dogfooding, done.md |

## Patterns

- Each phase = atomic commit: `spec-003: Phase N — <description>`.
- Skills follow `create-skill.md` registration procedure.
- All mirrors byte-identical after every phase.
- Cross-references bidirectional.
