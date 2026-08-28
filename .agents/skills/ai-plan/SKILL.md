---
name: ai-plan
description: >-
  Turns an approved spec into a numbered task list where every task names one file, one
  check that fails, and how to undo it. When the spec adds anything deployable, the plan
  must carry a CI/CD task and an observability task; they are not optional. Trigger for
  "break this down", "what tasks do we need", "let's start implementing", "the scope
  changed, re-plan". Not for exploring the problem — use /ai-spec. Not for writing the
  code — say go once this is approved. Not for judging what was built — use /ai-review.
license: Apache-2.0
compatibility: needs git; an approved spec under specs/
disable-model-invocation: true
---

# Turn the spec into tasks

## What it produces

`specs/NNN-slug/plan.md`, beside the spec it implements.

## Steps

1. Read the spec, and only the specs it names — the one it supersedes, the ones it depends
   on. Nothing else. A hundred specs cost the index plus the ones you were told about.
2. Write tasks small enough that each one is a commit, each one numbered and each one
   opening with an empty box: `1. [ ] **Title** —`. For every task, four things:
   **file** (the one it touches), **check** (the command that fails today and passes
   after), **rollback** (how to undo it), **done when** (in one sentence, testable).
   Never write `[x]`. The box is filled by `ai-eng spec show <id> --task <n> --tick`,
   which runs the check and seals what it measured; an empty box means no command has
   run over these bytes yet, which is not the same as "not done".
3. A check is a command, never a judgement. "Looks right" is not a check. If a task's
   check reads "the agent decides X", say in one line why a script cannot do it — and if
   you cannot say why, write the script instead. That is rule 12, and it applies here
   first because here is where the cost is decided.
4. If the spec adds anything that gets a URL, two tasks are mandatory and named:
   - a **CI/CD** task: build, lint, test and security analysis on every push, deploy from
     the default branch, zero manual steps;
   - an **observability** task covering the eight signals the spec lists, each passing with
     a command.
   Without them the plan is not finished, whatever else is in it.
5. Order the tasks so that the first failing check appears as early as possible. A plan
   whose first six tasks cannot fail is a plan that finds out too late.
6. Say what you are not doing, and why. The deliberate omissions are the part reviewers
   most often need and least often get.

## Done when

- Every task has a file, a check, a rollback and a "done when".
- The deployable tasks exist if the spec is deployable, and are absent if it is not.
- The person has approved it, recorded as an ADR at the spec and plan digests. That record is the gate: no code before it.
- The reviewer got `ai-eng report view --spec <NNN>`'s `file://` link beside the Markdown;
  the ADR at the two digests stays the gate, and the page is how it is read.

## What this is not

Not an estimate, not a schedule, and not a place to redesign. If planning uncovers that
the spec is wrong, stop and go back to `/ai-spec`. Re-planning around a wrong spec is the
most expensive mistake available here.

- "A check that reads 'the agent decides X' is honest for this task" — a check is a command, never a judgement: if you cannot say why a script cannot decide it, write the script instead.
