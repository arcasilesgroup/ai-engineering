---
name: ai-write
description: "Writes technical documentation for this repository: a README, a wiki page, product documentation, API docs or a technical post. Applies the framework's single writing standard (`references/documentation-writer.md`, spec 039) and verifies every document against the tree. Trigger for \"write the README\", \"update the wiki\", \"document this API\", \"write a technical post about\", \"refresh the docs\". Not for the changelog. Not for a spec or a plan — use /ai-plan. Not for a finding — use /ai-note. Not for an issue or incident report — use /ai-issue-report."
license: Apache-2.0
---

# Write documentation with the framework's gates

## What it produces

One document — a README, a wiki page, product documentation, API docs or a technical post —
written against the framework's single standard and verified against the tree: every named
file `exists`, nothing restates what the environment already says, and each section ends on
a checkable completion criterion. A document that cannot be verified exits `not-covered: <reason>`.

## Steps

1. Read the writing standard (spec 039): [references/documentation-writer.md](references/documentation-writer.md)
   in this skill's folder. If it is missing, stop and say `INCOMPLETE: writing standard absent`.
2. Read the tree the document is about. Not from memory, not `--help`. The README names
   commands that exist. The API doc names endpoints in the code. The wiki names
   directories on disk. Every claim traces to a file or a command.
3. Write and keep it a document, not a cache. Never restate the environment (config, CLI
   output, directory layout). Never repeat the spec or the ADR it points at. One idea per
   sentence. One meaning per word. Every section ends on a checkable criterion ("the
   command in section 2 runs", never "the reader understands").
4. Verify before done. Walk every named file and command. A missing file or a command that
   does not run is a finding against the document. A passage that could not be verified
   exits `not-covered: <reason>`. Never invent to make a section pass.
5. Write only into the homes the user named (README.md, docs/, a wiki dir). The change
   lands through the normal review. This skill never approves its own document.

## What this is not

Not the changelog; not a spec or plan (/ai-plan); not a finding (/ai-note); not an issue
or incident report (/ai-issue-report). And it is not a licence to repeat the environment: a
document that restates `--help` or the config is a cache, and a cache earns its load only
when the lookup is expensive.

- "The reader will understand it from context" — a completion criterion is not a feeling:
  if a section cannot be checked against a file or a command, it gets a `not-covered`
  reason, and a doc that claims to be verified when it is not is the false-green this
  framework exists to stop.

## Done when

Every named file exists and every named command runs, no passage restates the environment,
every section ends on a checkable criterion, anything unverifiable carries a `not-covered:
<reason>` exit, and the user's named home was the only place written. The doc is a claim;
the tree is the evidence.

## The ai-engineering seam

1. The writing standard itself ([references/documentation-writer.md](references/documentation-writer.md))
   is the prose standard for every ai-engineering surface that writes for humans: incident
   reports (/ai-issue-report), AGENTS.md authoring (/ai-agents-md), and any README the
   framework plants.
2. ai-write never writes into `.ai-engineering/` — governance artifacts are not product
   docs. Its home is the tree the user names: README.md, docs/, a wiki directory.
3. The verdict on whether a draft is good belongs to the `decide` tier; the mechanical
   checks (every named file exists, every named command runs) belong to `verify`
   (`.ai-engineering/config.toml` pin).