---
name: ai-agents-md
description: >-
  Creates and maintains the AGENTS.md a repository owes its coding agents, following the
  agents.md convention (https://agents.md/). Decides root-only versus nested AGENTS.md files
  from the repo's real shape, interviews the tree (not the user) for build/test/lint commands,
  and writes only what an agent cannot deduce from the code. Trigger for "create AGENTS.md",
  "update AGENTS.md", "the agent ignores our conventions", "set up agent instructions".
  Not for runtime agent contracts (goals, gates, budgets) — use /ai-goal. Not for
  documentation users read — use /ai-write.
license: Apache-2.0
---

# AGENTS.md for this repository, sized to its shape

`AGENTS.md` is the file coding agents read before working in a repo (https://agents.md/ and
https://github.com/agentsmd/agents.md). It is instructions for the agent, in the open, owned
by the team. ai-engineering governs the format; your repo owns the content.

## One file or many

The default is ONE `AGENTS.md` at the repository root: most agents read the nearest file up
the tree, so a single root file covers every package. Add nested files only when a
subproject genuinely needs different instructions — monorepos where packages have different
toolchains, test runners, or review rules. The test is mechanical:

- One toolchain, one test command repo-wide → root only.
- Two or more packages with different commands, lint rules, or conventions → one root file
  with what is shared, one nested file per divergent package with what differs.
- A nested file must not repeat its parents: repetition drifts. State only the delta.

Say the decision out loud when you write the file: "single root AGENTS.md" or "root + N
nested, one per package that diverges".

## What goes in (and what never does)

Sections that earn their place, in this order when present:

1. **Security** — hook-skip and linter-silence prohibitions, secrets/personal-data rules.
2. **Code style** — only the rules the linter cannot check (the linter checks its own).
3. **Build and test commands** — the exact commands, detected from the tree (package.json
   scripts, Cargo.toml, go.mod, pyproject.toml...), never from memory.
4. **Workflow** — the definition of done: green gate before "done", status conventions.
5. **Pull requests** — title format, pre-commit checks, test expectations.
6. **Session hygiene** — context-economy conventions the repo expects.

Never include: anything `--help` or a config file already says; a tutorial; rules a
newcomer can deduce from one look at the tree. Anti-drift rule: if a line becomes obvious
from reading the code, delete the line.

## Steps

1. Interview the tree: manifests, CI files, existing lint configs, the test layout, README.
   Every command you write must exist — run it or read it, do not recall it.
2. Decide root-only versus nested from the shape test above.
3. Write the file (or the deltas) against the section order. One idea per line. If the
   repository already has an AGENTS.md, edit it — never start a parallel one.
4. Verify every named command by running it. A command that fails as written is a finding
   against the file, not against the repo.
5. Hand the prose to /ai-write when the repository has adopted the ai-engineering writing
   standard — the same one-idea-per-sentence, verify-against-tree discipline applies.

## Done when

- Every command in the file runs as written.
- The file states only what the tree cannot tell the agent.
- Root-only or root+nested is a decision the tree shape justifies, and nested files carry
  deltas only.
- The file lives at the root (and only where needed below), named exactly `AGENTS.md`.

## The ai-engineering seam

1. `ai-eng init` plants this file once (`AGENTS.md` written once, never overwritten by
   update — 3-way diff if you edited it). This skill is how you rewrite it deliberately.
2. `ai-eng doctor` checks the anti-drift rule: a rule that the code now states is flagged
   as removable.
3. Keep the governed sections (Security, Workflow status convention) aligned with the
   guards: the guards enforce `--no-verify` and linter silencing at hook time; the file
   tells the agent before the hook has to.

Source: the agents.md convention (https://agents.md/, https://github.com/agentsmd/agents.md)
plus the sample layouts published there; adapted as the ai-engineering authoring skill.
