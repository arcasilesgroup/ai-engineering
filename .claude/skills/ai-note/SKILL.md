---
name: ai-note
description: "Saves persistent technical discoveries (debugging insights, non-obvious behaviors, workarounds, integration gotchas) and searches them across sessions. Trigger for 'save this', 'note that', 'remember this finding', 'what did we find about', 'do we have notes on'. Rule of thumb: if it took more than 30 minutes to figure out, save it. Not for cross-session learning patterns; use /ai-session-watch or /ai-learn instead."
effort: cheap
argument-hint: "find [query]|[slug]"
---

# Note

Saves technical discoveries — debugging insights, non-obvious behaviors,
integration gotchas that cost 30+ minutes — as flat files searchable
across sessions, and searches them on demand.

```
/ai-note find ruff          # search notes mentioning ruff
/ai-note find               # list all notes
/ai-note gitleaks-staged    # create/update note with this slug
```

Not for: architecture decisions (`decision-store.json` via
`/ai-governance`), incident analysis (`/ai-postmortem`), customer issues
(`/ai-support`), cross-session patterns (`/ai-learn`).

## Workflow

§10.4 DRY — search before create; one flat note per slug at
`.ai-engineering/notes/{slug}.md` (kebab-case, <= 50 chars).

**Mode `find [query]`:**
1. Scan `.ai-engineering/notes/*.md` for filename/title/content matches.
2. Rank by relevance (title > content > date).
3. Present title + date + first-line summary.

**Mode create/update (by slug):**
1. Check `.ai-engineering/notes/{slug}.md`; load if it exists.
2. Extract from the session: problem solved, what failed, what worked + why.
3. Write using the template below.
4. Validate: Problem and Findings MUST be non-empty (a note without
   findings is not a note).

```markdown
# {Title}

**Discovery Date**: YYYY-MM-DD
**Context**: {What triggered this investigation}
**Spec**: {spec-NNN if applicable, otherwise "N/A"}

## Problem
{What was expected vs what happened}

## Findings
{The non-obvious insight — be specific, include versions/configs}

## Code Examples
{Minimal reproduction or working solution}

## Pitfalls
{What looks right but is wrong — save future-you from the same trap}

## Related
- {Links to docs, issues, PRs, other notes}
```

### Save or skip

| Signal | Action |
|--------|--------|
| Took 30+ min to figure out | Save |
| Contradicts official docs | Save |
| Required reading source to understand | Save |
| Workaround for an upstream bug | Save |
| Standard usage documented in README | Skip |
| One-off config for this machine | Skip |

## Examples

### Example — save a debugging insight

User: "save this finding: pip-audit returns exit 1 even with no
vulnerabilities when --dry-run is set"

```
/ai-note pip-audit-dry-run-exit-code
```

Writes `.ai-engineering/notes/pip-audit-dry-run-exit-code.md` with
Problem / Findings / Code Examples / Pitfalls sections.

## Integration

Called by: user directly. Reads + writes: `.ai-engineering/notes/`. See
also: `/ai-learn` (synthesize patterns), `/ai-session-watch` (in-session
corrections), `/ai-debug`, `/ai-postmortem`.

$ARGUMENTS
