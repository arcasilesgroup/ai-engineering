---
name: ai-prompt-tune
description: "Optimizes prompts, system messages, and skill descriptions using explicit-over-implicit, show-do-not-tell, and rationale-embedding techniques. Trigger for 'this prompt is not working', 'optimize this skill description', 'improve triggering', 'rewrite this instruction', 'CSO-optimize'. Pass `--skill name` to optimize any skill's description field. Not for creating new skills; use /ai-scaffold instead. Not for evolving the entire skill body; use /ai-skill-improve instead."
effort: mid
argument-hint: "[text]|--skill [name]"
tags: [meta, optimization, prompts]
---

# Prompt Tune

Improves prompts, skill `description` fields, and agent instructions using proven techniques. Run `/ai-prompt-tune "<text>"` to optimize arbitrary text, or `/ai-prompt-tune --skill <name>` to CSO-optimize a skill's `description` field.

## Optimization Techniques (apply in order of impact)

**1. Explicit over implicit** — replace vague directives with concrete, observable instructions.

| Before | After |
|--------|-------|
| "Handle errors properly" | "Wrap DB calls in try/except, log the exception with stack trace, return a structured error with HTTP 500" |
| "Follow best practices" | "Guard clauses for early return, extract methods over 20 lines, name variables by intent not type" |

**2. Show, do not tell** — one concrete example beats five abstract rules. Bad: "Use descriptive names." Good: name by what it represents — `user_count` not `n`, `is_valid` not `flag`, `retry_delay_seconds` not `delay`.

**3. Structure with XML tags or Markdown** — clear structural markers per section; group related instructions; tables for multi-dimensional comparisons.

**4. Explain WHY per rule** — rules without rationale get ignored or misapplied. Bad: "Max 3 retries." Good: "Max 3 retries (beyond 3 the issue is systemic, not transient — escalate instead of retrying)."

**5. Positive framing** — state what TO do, not what NOT to do (the brain processes positive instructions faster). Bad: "Don't use generic error messages." Good: "Include the specific operation, input value, and expected format in every error message."

**6. CSO optimization (skill descriptions)** — the `description` is a search-query match surface; optimize for triggering conditions, not capability summaries. Pattern: `"Use when [specific situation + observable trigger]"`. Bad: "Database migration planning tool." Good: "Use when planning schema changes, assessing migration locking impact, or designing rollback procedures."

**7. Cialdini principles (discipline-enforcing skills — guard, verify, commit)** — **Authority**: cite specific standards + rationale. **Consistency**: reference past decisions and established patterns. **Social proof**: "teams that skip this step spend 3x longer debugging."

## Workflow

**Optimizing text:**
1. **Analyze** — identify which techniques are missing from the input.
2. **Apply** — rewrite applying all relevant techniques.
3. **Compare** — present before/after with annotations explaining each change.
4. **Validate** — confirm the optimized version is no longer than necessary (concise beats comprehensive).

**Optimizing a skill description (`--skill`):**
1. **Read skill** — load `.claude/skills/ai-{name}/SKILL.md`.
2. **Extract** the current `description` from frontmatter.
3. **CSO-optimize** using the triggering-condition pattern.
4. **Present** before/after for approval.
5. **Apply** — update the frontmatter if approved.
6. **Sync mirrors** — run `python scripts/sync_command_mirrors.py` to propagate the updated description to `.github/`, `.codex/`, and `.agents/` mirrors. Verify no tests break.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Hedging language ("try to", "if possible") | Be direct: state the expected behavior |
| Removing context while shortening | Keep the WHY, remove the fluff |

## Examples

User: "optimize the description for /ai-governance" → `/ai-prompt-tune --skill ai-governance`. Reads `.claude/skills/ai-governance/SKILL.md`, rewrites the description with explicit triggers + negative scoping, presents before/after, applies on approval, runs `sync_command_mirrors.py`.

## Integration

Called by: user directly, `/ai-skill-improve` (Phase 4 rewrite). Calls: `python scripts/sync_command_mirrors.py` (after `--skill` updates). See also: `/ai-scaffold` (new skills), `/ai-skill-improve` (full skill rewrite from pain).

$ARGUMENTS
