# AGENTS.md, sized to the repository

Load this in phase (a), before you judge or write any instruction file.

`AGENTS.md` is the file coding agents read before working in a repo (https://agents.md/). It is instructions for the agent, in the open, owned by the team. ai-engineering governs the format; the repo owns the content. Claude Code reads AGENTS.md when there is no CLAUDE.md, so no bridge file is needed.

## One file or many

The default is one `AGENTS.md` at the repository root: agents read the nearest file up the tree, so one root file covers every package. A nested file earns its place only when a subproject needs different instructions. The test is mechanical:

- One toolchain, one test command repo-wide: root only.
- Two or more packages with different commands, lint rules or conventions: one root file with what is shared, one nested file per divergent package with what differs.
- A nested file never repeats its parents. Repetition drifts; state only the delta.

Say the decision out loud: "single root AGENTS.md" or "root + N nested, one per package that diverges".

## What goes in, in this order when present

1. **Security**: hook-skip and linter-silence prohibitions, secrets and personal-data rules.
2. **Code style**: only the rules the linter cannot check.
3. **Build and test commands**: the exact commands, read from the tree (package.json scripts, Cargo.toml, go.mod, pyproject.toml), never from memory.
4. **Project config**: a short fill-in (domain, roles, paths, commands, URLs, sign-in, do-not-touch paths; n/a when absent).
5. **Architecture rules**: lines the critic treats as blockers, and where the layer rules live.
6. **Shared helpers**: CodeGraph for call chains, and the project's own helpers.
7. **Git workflow**: the feature branch, explicit paths, no `--no-verify`, no push unless asked.
8. **Workflow**: the definition of done, the status convention, the verification floor (never weaken a test, an assertion or a type to make a check pass), and scope discipline.
9. **Unattended runs**: no mid-run questions, a full-suite baseline before the first edit, hang-proof commands. Drop it when the repo never runs long unattended work.
10. **Pull requests**: title format, pre-commit checks, test expectations.
11. **Session hygiene**: the context-economy conventions the repo expects.

Never include: anything `--help` or a config file already says; a tutorial; a rule a newcomer deduces from one look at the tree; a progress file of its own (name the memory the repo already keeps). A generated AGENTS.md tends to make agents worse, so the edit leans toward deleting lines.

Two more tests decide a line. **Enforcement**: an always or a never names the mechanism that holds it (a hook, a test, a CI job). **Cost**: the root file loads on every turn, so overflow moves into a nested file or a reference; `doctor` warns once the root passes 120 lines.

## Auditing the set

A repo with guidance has a set, not a file: the root, the nested files that grew with it, and the instruction files other tools read (a CLAUDE.md, a Cursor rules folder, a Copilot instructions file).

1. Inventory it from the tree: every `AGENTS.md` under the root and every other instruction file. State the shape in one sentence.
2. Judge every line by four findings, quoting the line:
   - **Deduced**: the code, a manifest or CI already states it. It goes.
   - **Duplicated**: a nested file repeats its parent, or the parent carries detail one subtree needs. It moves down, or it goes.
   - **Dead**: a named command does not run as written. Run it; the failure is the finding.
   - **Unrouted**: a zone an agent works in with nothing saying what to read and what to skip.
3. Decide the shape with the test above. A repo that does not diverge keeps one file, even if it arrived with four.
4. Propose the findings and the target set, file by file. Write nothing before the yes.
5. Write the set: edit the root in place, create or trim the nested files, delta only. Never a parallel file under another name.
6. Align: another tool's instruction file that states a rule absent from the set gets the same edit, or is named as a finding and left alone.
7. Verify: every command runs, no line is carried by both a parent and a child, every file follows the section order.

## Editing it from a governed session

The trigger is evidence: a rule that does not match the tree. Say what you observed, at file:line, before touching the file. Change the stale lines, keep the section order, one idea per line. The status convention and the Security section are not yours to delete. The edit lands as a visible diff and goes through review like any other source.
