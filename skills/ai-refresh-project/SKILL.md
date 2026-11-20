---
name: ai-refresh-project
description: >-
  Brings a governed repository's own guidance back in line with its tree: AGENTS.md and the
  PRD, the docs/ folder, stale ai-eng artifacts, orphan branches and worktrees, and the
  governance files (layer rules, config, overrides). Manual only. Reads the tree, proposes,
  and stops; the person approves each change and applies the governance files themselves.
  Trigger for "/ai-refresh-project", "refresh this project", "update AGENTS.md", "audit
  AGENTS.md", "propose layer rules", "the init rules are wrong for this repo".
disable-model-invocation: true
license: Apache-2.0
---

# Refresh this project

If the person did not invoke this skill by name, stop. Do not write a file. Do not run a command.

This skill is the manual door. `disable-model-invocation: true` is the Claude Code latch. The sentence above is the latch for every other host. Do not claim that Cursor, Pi, or Codex honor the frontmatter field.

Run it after `ai-eng init`, and again when the repository has moved on: a new top-level code folder, a changed toolchain, a release. `ai-eng doctor` points here when a repo has code and no layer rules.

## The rule for every phase

The tree is the source. Every line you propose names the file, command or folder that proves it, and every command you name, you ran. Propose, then stop for the person's yes before writing anything. One phase at a time, in this order; a phase with nothing to change says so in one line and moves on.

## (a) AGENTS.md and the PRD

Audit the set of instruction files against the tree, then propose the edit. Read [references/agents-md.md](references/agents-md.md) before you start: the section order, what never goes in, the four findings, and when a nested file earns its place.

Then the PRD (`.ai-engineering/PRD.html` when the repo has one): every claim it makes about what exists must still be true of the tree. A claim the tree contradicts is a finding with the file that contradicts it.

After the yes, edit AGENTS.md in place. It is prose the team owns, so the session may write it. Run every command it names, and run `ai-eng doctor` to see the line count and the anti-drift check.

## (b) docs/

Judge each page in `docs/` against the writing standard of `/ai-write` (its `references/documentation-writer.md`): a dead link, a command that does not run, a version or path the tree no longer has, a page that repeats another. Propose what to fix, merge or delete; after the yes, edit with that standard. A page under `docs/history/` is a record: report it, never rewrite it.

## (c) Stale artifacts

Run `ai-eng doctor --gc`. It removes what ai-eng left behind and git no longer needs. Report what it removed and what it kept, in its own words. Do not delete anything by hand that the command kept.

## (d) Orphan branches and worktrees

Run `ai-eng work`. For each lane that is not active, ask the person one question with three answers:

- **Land** it: open the pull request, or `ai-eng worktree merge <slug>` where there is no forge.
- **Park** it: `ai-eng work park <branch> "<reason>"`.
- **Drop** it: `ai-eng work drop <branch>` (the tip is kept in `refs/archive/`).

Never decide for the person, and never touch a lane another session is writing in.

## (e) Governance files

Layer rules, `.ai-engineering/config.toml` and `.ai-engineering/overrides.toml` are policy. The session fence denies writing them, and that denial stays. Propose them on a page the person reads and applies outside the governed session.

- Layer rules belong to the standard tool of the language, never to a tool of ai-engineering's own. Read [references/layer-rules.md](references/layer-rules.md): how to find the layers, the tool per language, and how the rules reach CI.
- The page format, the overrides rule and what the page must show: [references/proposal-page.md](references/proposal-page.md). Its shell is the artifact design system in [ai-brainstorm › references/artifact-design.md](../ai-brainstorm/references/artifact-design.md).

## Survivors

A proposal keeps these sections of AGENTS.md: Security, Lifecycle, Anti-drift, Voice. Security is the hook, linter and secrets floor. Lifecycle is the spoken yes and the agent running the command. Anti-drift is the line that deletes a rule the code already states. Voice is the pointer to `ai-write`, not a copy of the standard.

KISS, YAGNI, DRY, SOLID and Clean Code stay only when the proposal names the check that fails when they are broken. A slogan with no check leaves.

## Done when

- Every phase reported a change, approved and applied, or "nothing to change".
- Every command named in AGENTS.md and the docs runs as written.
- `ai-eng doctor` is green, or each warning left is named with the reason it stays.
- The governance proposal page exists when phase (e) has changes, and nothing in `.ai-engineering/` was written by the session.

## Lifecycle

Lane: any
Writes: AGENTS.md, docs/, .ai-engineering/config-proposal.html
Read by: the person who reviews each phase and applies the governance files
Dies: when the next run rewrites the proposal page
Next: none

Source: ai-engineering (own), Apache-2.0, with the agents.md convention (https://agents.md/).
