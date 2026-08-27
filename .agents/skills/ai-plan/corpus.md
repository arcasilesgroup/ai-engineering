# Corpus: ai-plan

Turns an approved spec into a numbered task list where every task names one file, one check
that fails today and passes after, and how to undo it. When the spec adds anything that gets
a URL, the plan must carry a CI/CD task and an observability task; they are not optional. It
produces `specs/NNN-slug/plan.md` beside the spec it implements, and no code is written
until a person approves it.

## Routes here

- "the spec is approved, break this down into tasks" — the decision is already made and what is missing is the order of work, one commit per task.
- "what tasks do we need for the export format spec?" — asking for the task list, each with a file, a check, a rollback and a "done when".
- "let's start implementing, where do we begin?" — the tasks have to be ordered so the first failing check appears as early as possible, and that ordering is planning, not coding.
- "the scope changed, re-plan it" — re-planning against a spec that is still right is this skill; a spec that is wrong goes back to /ai-spec instead.
- "this one gets a public URL, what does the plan have to cover?" — a deployable spec makes the CI/CD task and the observability task mandatory and named, and a plan without them is not finished.
- "what are we deliberately not doing in this one?" — the omissions belong in the plan, where a reviewer can see them.

## Refuses

- "what's the best approach for this?" — use `/ai-spec`, because there is nothing to plan until at least two real options have been weighed and a person approved the recommendation.
- "actually I think we picked the wrong storage engine" — use `/ai-spec`, because re-planning around a wrong spec is the most expensive mistake available here.
- "the deploy is failing, plan the fix" — use `/ai-debug`, because a cause has to be named at `file:line` and a failing check written before there is a fix to break into tasks.
- "look over my PR and tell me what you'd change" — use `/ai-review`, because judging what was built is a different pass from listing what to build.
- "walk me through how the dispatcher works first" — use `/ai-explore`, because reading this repository and answering at `file:line` is a tour, and this skill reads the spec and only the specs it names.
- "commit this and open the pull request" — use `/ai-ship`, because a task list is not commits, a changelog entry or a pull request.
- "the plan should just be sensible about it" — refused, and every task is written against `.agents/skills/ai-report/references/documentation-writer.md`: a task whose done-when cannot fail is a task whose completion is a feeling.
