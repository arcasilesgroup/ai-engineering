---
name: ai-note
description: "Saves persistent technical discoveries (debugging insights, non-obvious behaviors, workarounds, integration gotchas) and searches them across sessions. Trigger for 'save this', 'note that', 'remember this finding', 'what did we find about', 'do we have notes on'. Rule of thumb: if it took more than 30 minutes to figure out, save it. Not for cross-session learning patterns; use /ai-instinct or /ai-learn instead."
effort: medium
argument-hint: "find [query]|[slug]"
mode: agent
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-note/SKILL.md
edit_policy: generated-do-not-edit
---



# Note

## Purpose

Knowledge management for technical discoveries. Captures debugging insights, non-obvious behaviors, and integration gotchas that would cost 30+ minutes to re-discover. Notes persist across sessions and are searchable.

## Trigger

- Command: `/ai-note <slug>` (create/update) or `/ai-note find [query]` (search)
- Context: discovery during debugging, research, or investigation that should be preserved.

## When to Use

- Discovery cost exceeds 30 minutes of investigation
- Non-obvious behavior that contradicts documentation or expectations
- Debugging insight that required multiple attempts to isolate
- Integration gotcha between tools, libraries, or services
- Workaround for a known issue with no upstream fix

## When NOT to Use

- **Architecture decisions** -- use `state.db.decisions` via `/ai-governance`
- **Incident analysis** -- use `/ai-postmortem`
- **Customer issues** -- use `/ai-support`

## Workflow

### Mode: find

1. **Search notes** -- scan `.ai-engineering/notes/*.md` for files matching the query in filename, title, or content.
2. **Rank results** -- sort by relevance (title match > content match > date).
3. **Present** -- list matching notes with title, date, and first-line summary.

### Mode: create/update (by slug)

1. **Check existing** -- look for `.ai-engineering/notes/{slug}.md`. If found, load for update.
2. **Gather context** -- from the current session, extract:
   - What problem was being solved
   - What was tried and failed
   - What actually worked and why
3. **Write note** -- create/update at `.ai-engineering/notes/{slug}.md` using template:

```markdown
# {Title}

**Discovery Date**: YYYY-MM-DD
**Context**: {What triggered this investigation}
**Spec**: {spec-NNN if applicable, otherwise "N/A"}

## Problem

{What was expected vs what happened}

## Findings

{The non-obvious insight -- be specific, include versions/configs}

## Code Examples

{Minimal reproduction or working solution}

## Pitfalls

{What looks right but is wrong -- save future-you from the same trap}

## Related

- {Links to docs, issues, PRs, other notes}
```

4. **Validate** -- ensure Problem and Findings sections are non-empty. A note without findings is not a note.

## Decision: Save or Skip

| Signal | Action |
|--------|--------|
| Took 30+ min to figure out | Save |
| Contradicts official docs | Save |
| Required reading source code to understand | Save |
| Workaround for upstream bug | Save |
| Standard usage documented in README | Skip |
| One-off configuration for this machine | Skip |

## Quick Reference

```
/ai-note find ruff          # search notes mentioning ruff
/ai-note find               # list all notes
/ai-note gitleaks-staged    # create/update note with slug "gitleaks-staged"
```

## Storage

- Location: `.ai-engineering/notes/{slug}.md`
- Naming: kebab-case slugs, descriptive, max 50 chars
- Index: notes are flat files, searched by content -- no separate index needed

## Examples

### Example 1 — save a debugging insight

User: "save this finding: pip-audit returns exit 1 even with no vulnerabilities when --dry-run is set"

```
/ai-note pip-audit-dry-run-exit-code
```

Writes `.ai-engineering/notes/pip-audit-dry-run-exit-code.md` with Problem / Findings / Code Examples / Pitfalls sections.

### Example 2 — search past discoveries

User: "do we have notes on flaky tests in CI?"

```
/ai-note find flaky tests
```

Scans `.ai-engineering/notes/`, ranks by relevance, presents matching slugs + summaries.

## Integration

Called by: user directly. Reads + writes: `.ai-engineering/notes/`. See also: `/ai-learn` (synthesize patterns), `/ai-instinct` (in-session corrections), `/ai-debug`, `/ai-postmortem`.

$ARGUMENTS
