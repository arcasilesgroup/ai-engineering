---
name: ai-agents-md
description: >-
  Creates, audits and maintains the AGENTS.md a repository owes its coding agents, following
  the agents.md convention (https://agents.md/). Decides root-only versus nested AGENTS.md
  files from the repo's real shape, interviews the tree (not the user) for build/test/lint
  commands, and writes only what an agent cannot deduce from the code. Audits a set that
  already exists: a rule the code states, a child repeating its parent, a command that no
  longer runs, a zone with no route in. Also the in-session maintenance path: a governed agent
  MAY edit AGENTS.md directly (blueprint §9.2 — it is not sacred) when the repo's real state
  made a rule stale. Trigger for "create AGENTS.md", "update AGENTS.md", "audit AGENTS.md",
  "split AGENTS.md", "AGENTS.md is too long", "the agent reads the wrong file", "the agent
  ignores our conventions", "set up agent instructions", "edit AGENTS.md". Not for runtime
  agent contracts (goals, gates, budgets) — use /ai-goal. Not for documentation users read —
  use /ai-write.
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

Two more tests decide a line. **Enforcement**: an always or a never names the mechanism that
holds it (a hook, a test, a CI job), because an unenforced rule rots. **Cost**: the root file
loads on every turn, so overflow moves behind a pointer in a nested file or a reference, never
into the always-loaded one; `doctor` warns once the root passes 80 lines.

## Steps

1. Interview the tree: manifests, CI files, existing lint configs, the test layout, README.
   Every command you write must exist — run it or read it, do not recall it.
2. Decide root-only versus nested from the shape test above.
3. Write the file (or the deltas) against the section order. One idea per line. If the
   repository already has an AGENTS.md, edit it — never start a parallel one. Every
   `AGENTS.md` gets its sibling `CLAUDE.md`: a relative symlink to `AGENTS.md` in the same
   directory, the mechanism `ai-eng init` uses, or a one-line `@AGENTS.md` import where the
   OS refuses a symlink.
4. Verify every named command by running it. A command that fails as written is a finding
   against the file, not against the repo.
5. Hand the prose to /ai-write when the repository has adopted the ai-engineering writing
   standard — the same one-idea-per-sentence, verify-against-tree discipline applies.

## Auditing a set that already exists

A repo that already has guidance has a set, not a file: the root, whatever nested files grew
with it, and the instruction files other tools read. Audit the set against the tree before
changing any of it.

1. Inventory, from the tree and never from memory: every file named `AGENTS.md` under the root,
   and every instruction file the repo ships today (`CLAUDE.md`, a Cursor rules directory, a
   Copilot instructions file). State the shape in one sentence: root only, or root plus N
   nested.
2. Judge every line of every file by four findings, and quote the line when you report one:
   - **Deduced**: the code, a manifest or CI already states it. It goes.
   - **Duplicated**: a nested file repeats its parent, or the parent carries detail only one
     subtree needs. It moves down, or it goes.
   - **Dead**: a named command no longer runs as written. Run it; the failure is the finding.
   - **Unrouted**: a zone an agent must work in with nothing saying what to read and what to
     skip. Missing guidance is a finding too, not a blank.
3. Decide the shape with the test above, out loud. A repo that does not diverge keeps one file,
   even if it arrived with four.
4. **Stop and propose**: the findings, and the target set file by file (the count, the
   sections, the lines that go, the lines that move where). Write nothing before the answer.
   These files are prose the team owns; the audit earns the edit by showing what it changes.
5. Write the set: edit the root in place, create or trim the nested files, delta only. Never a
   parallel file under another name, and never a section that both a parent and a child carry.
6. Mirror and align: apply the sibling rule from Steps to every file the audit writes or keeps.
   An instruction file another tool reads that states what the set no longer says gets the same
   edit, or is named as a finding and left alone.
7. Verify the result: every command in the set runs as written, no line is carried by both a
   parent and a child, and every file follows the section order above.

## Done when

- Every command in the file runs as written.
- The file states only what the tree cannot tell the agent.
- Root-only or root+nested is a decision the tree shape justifies, and nested files carry
  deltas only.
- The file lives at the root (and only where needed below), named exactly `AGENTS.md`, with its
  sibling `CLAUDE.md` resolving to it.
- A repo that arrived with a set was audited, not overwritten: every surviving line is a
  decision the tree justifies, and nothing was written before the proposal was approved.

## Keeping it alive from inside a governed session

`AGENTS.md` is a prose contract the team owns — NOT machinery. A governed agent may edit it
in-session (blueprint §9.2: it is not sacred); `self-protect` only denies the wiring
(`.ai-engineering/`, surface settings, git hooks, the global canon, an approved spec.html).
Edit it when the repo's real state made a rule stale, never to bend a rule this task dislikes:

1. The trigger is evidence: a rule that no longer matches the tree (a command that fails, a
   convention the code now states by itself, a workflow the team changed). Say what you
   observed, at file:line, before touching the file.
2. Edit, never rewrite: change the stale lines, keep the section order, one idea per line.
   The status convention and the Security section are not yours to delete.
3. Every edit lands as a visible diff (git diff) and survives review — the file is committed
   like any other source. If the change is contentious, propose it instead of pushing it.
4. After editing, run `ai-eng doctor`: the anti-drift check flags any rule the code now
   states — delete that line while you are there.

## The ai-engineering seam

1. `ai-eng init` installs this file once (never overwritten by update — 3-way diff if you
   edited it). This skill is how you rewrite it deliberately.
2. The governed agent edits it in-session when the tree moved on (section above);
   `self-protect` guards the wiring instead — the file is prose the team owns.
3. `ai-eng doctor` checks the anti-drift rule: a rule that the code now states is flagged
   as removable.
4. Keep the governed sections (Security, Workflow status convention) aligned with the
   guards: the guards enforce `--no-verify` and linter silencing at hook time; the file
   tells the agent before the hook has to.

## Lifecycle

Lane: any
Writes: AGENTS.md, CLAUDE.md
Read by: the surfaces, by name convention
Dies: when the shape of the repository changes — the tree is the source and the file follows it
Next: none

Source: the agents.md convention (https://agents.md/, https://github.com/agentsmd/agents.md)
plus the sample layouts published there; adapted as the ai-engineering authoring skill.
