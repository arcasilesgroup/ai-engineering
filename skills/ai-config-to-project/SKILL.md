---
name: ai-config-to-project
description: >-
  Adapts a governed project's layer rules, config, overrides, and AGENTS.md after
  ai-eng init, and again as the code grows. Manual only. Analyses the real dependency
  graph and the stack's guidelines, writes a proposal page and stops until the person
  says yes; the person applies it outside the governed agent session. Trigger for
  "/ai-config-to-project", "adapt this project", "propose layer rules", "the init rules
  are wrong for this repo".
disable-model-invocation: true
license: Apache-2.0
---

# Adapt this project to ai-engineering

If the person did not invoke this skill by name, stop. Do not write a file. Do not run a command.

This skill is the manual door. `disable-model-invocation: true` is the Claude Code latch. The sentence above is the latch for every other host. Do not claim that Cursor, Pi, or Codex honor the frontmatter field.

`ai-eng doctor` points here when a repo has code and no layer rules. Run it again whenever a new top-level code folder appears or a layer contract changes: the rules grow with the code.

## What you may change, and how

Read the tree. Propose. Stop. The person says approve, ok, or go. The person applies the approved changes manually outside the governed agent session.

Do not Edit or Write these files yourself. The session fence denies the first three, and the rule covers the rest:

- `.ai-engineering/config.toml`
- `.ai-engineering/overrides.toml`
- `.ai-engineering/ai-eng.lock`
- the layer-rules config and the manifest line that runs it

`ai-eng adapt apply` is intentionally disabled: a same-user agent can create a matching hash, so the hash cannot prove human approval. The person applies the reviewed changes manually outside the governed agent session.

## Layer rules

Choosing layers is judgement. Base it on evidence, in this order:

1. **The real graph.** Map who imports whom with CodeGraph (`/ai-codegraph`) when the repo is indexed, otherwise with the language's own tool. Name the folders that exist and the directions that already hold.
2. **The stack's guidelines.** Look up how this language and framework layer an application (`/ai-research`): the framework's own docs first, then Clean or hexagonal architecture where the project's size earns it. Cite each source on the page.
3. **The project's documents.** AGENTS.md, DECISIONS.md and the README say what the people here already decided. They win over a general guideline.

Write the rules for the standard tool of the language, never for a tool of ai-engineering's own:

| Language | Tool | Rules live in | Runs from |
| --- | --- | --- | --- |
| TypeScript / JavaScript | dependency-cruiser | `.dependency-cruiser.cjs` | an `arch` script in `package.json` |
| Python | import-linter | `[tool.importlinter]` in `pyproject.toml`, or `.importlinter` | `lint-imports` |
| Go | depguard in golangci-lint | `.golangci.yml` | `golangci-lint run` |

Another language: propose its standard tool and name it as a new choice on the page. In a JavaScript project the ai-eng check workflow runs a declared `arch` script, so the `package.json` line is enough. For any other language, the workflow does not run the tool: put the command in a CI step the project already has, and say on the page which step that is.

Layers come from folders that exist here. Each rule forbids a direction that is clean today, so the first run passes and the next wrong import fails. A rule the code already breaks goes on the page as a finding, with the imports that break it, never as a rule that fails on day one. A second run starts from the files on disk and adds only what changed.

## The page

Write `.ai-engineering/config-proposal.html` in the artifact shell (the same tokens as `templates/brainstorm.html.tpl`, including the scroll-spy script). The page shows each diff in words a person can refuse, the evidence behind every layer, and the install line for the tool.

The machine-readable payload is one JSON object inside the page, keyed by repository path and sorted. Only these paths:

- `AGENTS.md`
- `.ai-engineering/config.toml`
- `.ai-engineering/overrides.toml`
- the layer-rules config from the table above
- the manifest that runs it (`package.json`, `pyproject.toml`, `Makefile`)

```html
<meta name="ai-eng-proposal-sha256" content="<sha256 of the script body>">
<script type="application/json" id="payload">…</script>
```

The sha256 is the hex digest of the exact script body. `<` inside that body is the six characters `<`. If you change the body after stamping the hash, apply refuses.

## Survivors

Survivors that a proposal must keep: Security, Lifecycle, Anti-drift, Voice.

Security is the hook, linter, and secrets floor. Lifecycle is the spoken yes and the agent running the command. Anti-drift is the line that deletes a rule the code already states. Voice is the pointer to `ai-write`, not a copy of the standard.

KISS, YAGNI, DRY, SOLID, and Clean Code stay only when the proposal names the check that fails when they are broken. A slogan with no check leaves.

Build and test commands come from this tree. Run them. Do not copy another repo's command line.

## Overrides

Every `[[guard.off]]` block in the proposal has `name`, `reason`, and `until` (a date). Show that block on the page as the dangerous one. No `until` means you do not include the block. Apply will refuse it anyway.

## After the yes

The person manually applies the approved files from outside the governed agent session, installs the tool, and runs the command once to see it pass. Do not run `ai-eng adapt apply` or pass `--no-verify`. If the person asks about that command, explain that it is disabled because it cannot authenticate approval.

The page uses the artifact design system in [ai-brainstorm › references/artifact-design.md](../ai-brainstorm/references/artifact-design.md). Copy that document's whole CSS block and the scroll-spy script verbatim — tokens, layout rules and components, not tokens alone. Do not invent a second style.

## Lifecycle

Lane: any
Writes: .ai-engineering/config-proposal.html
Read by: the person who reviews and manually applies the proposal
Dies: when the next run rewrites the page
Next: none

Source: ai-engineering (own), Apache-2.0.
