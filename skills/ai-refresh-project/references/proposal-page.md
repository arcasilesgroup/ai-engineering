# The governance proposal page

Load this in phase (e), before you write `.ai-engineering/config-proposal.html`.

The session may not write `.ai-engineering/config.toml`, `.ai-engineering/overrides.toml`, `.ai-engineering/ai-eng.lock`, or the layer-rules config and the manifest line that runs it. The page is how those changes reach the person, who applies them outside the governed session.

## What the page shows

- One section per file, each with the exact diff and, in plain words, what changes and why.
- The evidence behind every layer rule: the imports found, the guideline cited, the decision quoted.
- The install line for the layer tool, and the command that proves the rules pass today.
- Every `[[guard.off]]` block in its own section, marked as the dangerous one.

Each change can be refused on its own. The page is a proposal, not a payload: no hash, no machine-readable block, nothing a tool applies by itself.

## Overrides

Every `[[guard.off]]` block in the proposal has `name`, `reason` and `until` (a date). A block without an `until` is not proposed at all.

## The shell

The page uses the artifact design system in [ai-brainstorm › references/artifact-design.md](../../ai-brainstorm/references/artifact-design.md). Copy that document's whole CSS block and the scroll-spy script verbatim: tokens, layout rules and components. Do not invent a second style.

## After the yes

The person applies the approved changes outside the governed session, installs the layer tool, and runs its command once to see it pass. Never pass `--no-verify` to land them.
