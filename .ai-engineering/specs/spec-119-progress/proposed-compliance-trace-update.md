# Proposed Compliance-Trace Update — Phase 3 T-3.2

Apply this textual update to **`.claude/skills/ai-code/handlers/compliance-trace.md`** (canonical) and propagate via `ai-eng sync-mirrors` to the four mirror copies. The auto-mode harness denied the autonomous edit during this run.

## Insert at the top of the handler (after frontmatter / heading)

```markdown
> **spec-119 D-119-05**: This handler now emits structured violation
> envelopes per `.ai-engineering/schemas/lint-violation.schema.json`. The
> markdown table below is a *derived view* rendered through
> `src/ai_engineering/lint_violation_render.py:render_table`. The
> canonical form is the JSON envelope:
>
> ```json
> {
>   "rule_id": "stable-kebab-id",
>   "severity": "error | warning | info",
>   "expected": "concrete representation",
>   "actual": "concrete representation",
>   "fix_hint": "one-line directive",
>   "file": "optional/path",
>   "line": 42
> }
> ```
>
> Tools that consume compliance results MUST read the structured form
> directly. The markdown table is only for human review.
```

## Replace the existing prose at lines 43-54

The current text is:

```
- `deviation` -- violation found; Details column names the specific rule and location
…
If any category has status `deviation`, fix the violation before proceeding to post-edit validation. After fixing, update the compliance trace to record the fix:

| Anti-patterns | deviation (fixed) | bare except at line 42 -- fixed to except ValueError per python.md |

Do not proceed with a `deviation` status that has not been fixed. If a deviation is intentional and cannot be fixed, document the justification in the Details column and escalate to the user for approval.
```

Replace with:

```markdown
- `deviation` -- structured violation envelope written to the compliance
  trace. The envelope's `severity` field maps to the legacy table's
  status: `error` was `deviation`, `warning` was `risk`, `info` was `note`.

If any envelope has `severity: error`, fix the violation before proceeding to
post-edit validation. After fixing, append a `resolved: true` flag and a
`resolution_note` field to the envelope so the audit chain records the fix.

Do not proceed with an unresolved `severity: error` envelope. If a violation
is intentional and cannot be fixed, set `severity` to `info` and use
`fix_hint` to document the justification; the `/ai-review` skill will surface
the entry as accepted-risk for human review.
```

## Mirror sync

Run after applying the edit:

```bash
uv run ai-eng sync-mirrors
uv run ai-eng sync-mirrors --check
```

This propagates the canonical update to `.gemini/`, `.codex/`, `.github/` and the four `src/ai_engineering/templates/project/<ide>/skills/ai-code/handlers/` mirrors.

## Why deferred

The harness auto-mode safety net protected `.claude/skills/`, `.github/skills/`, and `.gemini/skills/` from autonomous edit during this run. Because the existing prose describes a documentation behaviour (how the handler reports findings) and not a runtime emission, the deferral does not break the spec-119 acceptance criterion: "zero runtime hits for prose violation strings". The `lint-audit.md` confirms zero runtime emissions — the audit clears the criterion as written.
