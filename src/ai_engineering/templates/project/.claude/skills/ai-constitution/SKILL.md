---
name: ai-constitution
description: "Interviews the operator to produce a project-identity CONSTITUTION.md (Mission / Stakeholders / Vocabulary / Prohibitions / Compliance gates / Anti-goals / Boundaries / Escalation / Language / Lifecycle phase). Trigger for 'set up the constitution', 'define project identity', 'who is this project for', 'what does this project never do', 'amend the constitution'. Not for AI-behaviour rules — those live in CANONICAL.md / AGENTS.md. Not for spec governance; use /ai-governance instead."
effort: mid
model_tier: sonnet
argument-hint: "[generate|update|amend]"
---

# Constitution

## Quick start

```
/ai-constitution generate   # interview + write CONSTITUTION.md from scratch
/ai-constitution update     # change a single section (Mission, Prohibitions, etc.)
/ai-constitution amend      # formal amendment with version bump + audit event
```

## Workflow

Apply §10.6 (SDD) — every CONSTITUTION.md write is traceable to a spec
decision (D-131-04 anchored this rewrite). Apply §10.4 (DRY) — project
identity lives ONCE in CONSTITUTION.md; AI-behaviour content lives in
CANONICAL.md. The two never overlap.

1. **Auto-detect** — read `.ai-engineering/manifest.yml`, package files
   (`pyproject.toml` / `package.json` / `Cargo.toml`) to seed the
   interview with project name, stack, version.
2. **Read existing** — if `CONSTITUTION.md` exists, load it and show
   the operator the diff BEFORE any overwrite. NEVER overwrite without
   diff + explicit confirm (R-131-03 mitigation).
3. **Interview the 10 sections** — see "Interview" below.
4. **Write** — emit `CONSTITUTION.md` using the 10-section skeleton.
   Refuse to write any header from
   `tools/skill_lint/checks/md_mirror.py:FORBIDDEN_CONSTITUTION_HEADERS`
   (those are AI-behaviour headers; CONSTITUTION owns project identity
   only).
5. **Rotate** — when `update` or `amend` replaces operator-authored
   content, copy the pre-write body to
   `.ai-engineering/specs/_history-constitution-<YYYY-MM-DD>.md` so
   the prior identity is recoverable.
6. **Verify + record** — run `python -m skill_lint --check` after the
   write to confirm CONSTITUTION.md passes the md_mirror sweep. Emit a
   `constitution_updated` audit event to
   `.ai-engineering/state/framework-events.ndjson`.

## Interview

| Section | Question |
|---------|----------|
| Mission | What does this project do, and what does it never do? |
| Stakeholders | Who relies on this project? Who pays the cost when it breaks? |
| Vocabulary | What domain terms must every contributor use precisely? |
| Prohibitions | What must the AI / contributors NEVER do? |
| Compliance gates | What pipelines / audits / certifications gate releases? |
| Anti-goals | What use cases are explicitly out of scope (and why)? |
| Boundaries | Which surfaces are framework-owned vs team-owned? |
| Escalation | Who is paged when prohibitions / gates fail? |
| Language | Project natural language for docs / commits. |
| Lifecycle phase | greenfield · stabilising · mature · sunset. |

## Examples

### Example 1 — first install, no prior CONSTITUTION

User: "set up the constitution for this project"

```
/ai-constitution generate
```

Interviews the 10 sections, seeds defaults from `manifest.yml`, writes
`CONSTITUTION.md` v1.0.0 with the ratified date stamped. Emits one
`constitution_updated` audit event.

### Example 2 — formal amendment with version bump

User: "amend the constitution to add 'no LLM-generated production
secrets' to prohibitions"

```
/ai-constitution amend
```

Loads the existing body, presents the diff for the Prohibitions
section, applies the amendment, bumps the minor version, records the
amendment row in the governance footer, rotates the pre-amendment
body into `_history-constitution-<date>.md`.

## Integration

Called by: `ai-eng install` (governance phase), `/ai-start` (cold-load
identity context). Reads: `manifest.yml`, package files, existing
`CONSTITUTION.md`, `decision-store.json`. Writes: `CONSTITUTION.md`,
`_history-constitution-<date>.md` (when rotating). Audited by:
`tools/skill_lint/checks/md_mirror.py:check_constitution_clean` (any
AI-behaviour header rejects the write). Consumed by: every skill at
Step 0. See also: `/ai-governance` (compliance against the
constitution), CANONICAL.md (AI-behaviour layer — never written by
this skill).

$ARGUMENTS
