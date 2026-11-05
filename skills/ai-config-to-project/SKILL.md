---
name: ai-config-to-project
description: >-
  Adapts a governed project's architecture rules, config, overrides, and AGENTS.md
  after ai-eng init. Manual only. Writes a proposal page and stops until the person
  says yes, then the person applies it manually outside the governed agent session. Trigger for "/ai-config-to-project",
  "adapt this project", "the init rules are wrong for this repo".
disable-model-invocation: true
license: Apache-2.0
---

# Adapt this project to ai-engineering

If the person did not invoke this skill by name, stop. Do not write a file. Do not run a command.

This skill is the manual door. `disable-model-invocation: true` is the Claude Code latch. The sentence above is the latch for every other host. Do not claim that Cursor, Pi, or Codex honor the frontmatter field.

## What you may change, and how

Read the tree. Propose. Stop. The person says approve, ok, or go. The person applies the approved changes manually outside the governed agent session.

Do not Edit or Write these files yourself. The session fence denies it, and that denial stays:

- `.ai-engineering/arch.rules.json`
- `.ai-engineering/config.toml`
- `.ai-engineering/overrides.toml`
- `.ai-engineering/ai-eng.lock`

`ai-eng adapt apply` is intentionally disabled: a same-user agent can create a matching hash, so the hash cannot prove human approval. The person applies the reviewed changes manually outside the governed agent session.

## The page

Write `.ai-engineering/config-proposal.html` in the artifact shell (the same tokens as `templates/brainstorm.html.tpl`, including the scroll-spy script). The page shows each diff in words a person can refuse.

The machine-readable payload is one JSON object inside the page. Keys, only these, sorted:

- `AGENTS.md`
- `.ai-engineering/arch.rules.json`
- `.ai-engineering/config.toml`
- `.ai-engineering/overrides.toml`

```html
<meta name="ai-eng-proposal-sha256" content="<sha256 of the script body>">
<script type="application/json" id="payload">…</script>
```

The sha256 is the hex digest of the exact script body. `<` inside that body is the six characters `\u003c`. If you change the body after stamping the hash, apply refuses.

## Survivors

Survivors that a proposal must keep: Security, Lifecycle, Anti-drift, Voice.

Security is the hook, linter, and secrets floor. Lifecycle is the spoken yes and the agent running the command. Anti-drift is the line that deletes a rule the code already states. Voice is the pointer to `ai-write`, not a copy of the standard.

KISS, YAGNI, DRY, SOLID, and Clean Code stay only when the proposal names the check that fails when they are broken. A slogan with no check leaves.

Build and test commands come from this tree. Run them. Do not copy another repo's command line.

Layer names come from directories that exist here. A second run starts from the files on disk. It does not restore the framework's `cli` / `guards` / `chain` layers.

## Overrides

Every `[[guard.off]]` block in the proposal has `name`, `reason`, and `until` (a date). Show that block on the page as the dangerous one. No `until` means you do not include the block. Apply will refuse it anyway.

## After the yes

The person manually applies the approved files from outside the governed agent session. Do not run `ai-eng adapt apply` or pass `--no-verify`. If the person asks about that command, explain that it is disabled because it cannot authenticate approval.

The page uses the artifact design system in [ai-brainstorm › references/artifact-design.md](../ai-brainstorm/references/artifact-design.md). Copy that document's whole CSS block and the scroll-spy script verbatim — tokens, layout rules and components, not tokens alone. Do not invent a second style.

## Lifecycle

Lane: any
Writes: .ai-engineering/config-proposal.html
Read by: the person who reviews and manually applies the proposal
Dies: when the next run rewrites the page
Next: none

Source: ai-engineering (own), Apache-2.0.
