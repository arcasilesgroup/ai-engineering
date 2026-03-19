# Handler: validate

## Purpose

Post-creation validation. Verifies a skill or agent is correctly configured across all surfaces.

## Procedure

### 1. CSO Description Quality
- Does description start with "Use when"?
- Does it describe a trigger condition, not a summary?
- Is it specific enough to distinguish from other skills?

### 2. Frontmatter Order
- Check field order matches canonical:
  - Agents: name, description, color, model, tools
  - Skills: name, description, [optional fields], argument-hint

### 3. Mirror Parity
- Verify skill/agent exists in all 3 surfaces:
  - `.claude/skills/ai-<name>/SKILL.md` or `.claude/agents/ai-<name>.md`
  - `.agents/skills/<name>/SKILL.md` or `.agents/agents/ai-<name>.md`
  - `.github/prompts/ai-<name>.prompt.md` or `.github/agents/<name>.agent.md`
- Verify handlers are mirrored too (if any)

### 4. Manifest Registration
- Verify skill/agent is in `.ai-engineering/manifest.yml`
- Verify `total` count matches actual count

### 5. Cross-Reference Integrity
- All Referenced Skills paths point to existing files
- No ghost skill references

### 6. Report
```
✓ CSO description: PASS
✓ Frontmatter order: PASS
✓ Mirror parity: 3/3 surfaces
✓ Manifest registered: PASS
✓ Cross-references: PASS (0 broken)
```
