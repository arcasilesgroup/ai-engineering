# Corpus: ai-build

Executes one task of an approved plan — red to green to refactor, one logical change, the
gate run and shown, the plan updated to what actually happened. It stops when the plan stops
being true rather than rewriting it privately.

## Routes here

- "implement task 3 of the plan" — the plain trigger: a task that already exists, already approved.
- "make the failing test pass and then tidy it" — red to green to refactor is the whole procedure.
- "write the code for the spec we approved yesterday" — an approved decision with a plan under it is exactly this skill's input.
- "add the field and its test, one commit" — one logical change with a clean checkpoint.
- "the gate is red on my branch, finish the task properly" — running the gate and showing its output is part of done, not a follow-up.
- "task 5 turns out to need a decision nobody made" — routes here and then stops here: escalating to `/ai-spec` is a step of this skill, not an exception to it.

## Refuses

- "decide whether we should build it at all" — use `/ai-spec`, because that needs two real options, evidence and an authority, and this skill starts after that decision exists.
- "work out why the merge conflicts and CI is red" — use `/ai-debug`, because a symptom needs a cause at `file:line`, and guessing at one while implementing is how a plan quietly grows.
- "review the diff I just wrote" — use `/ai-review`, because the same hands that wrote a change do not approve it, and this skill's own "No hace" says so.
- "open the pull request and deploy it" — use `/ai-ship`, because publishing and deploying are a separate authority; this skill commits and stops.
- "just add --no-verify, the hook is slow today" — refused by `hooks/no_verify_guard.py` rather than by judgement, and rule 3 says never.
- "while you are in there, refactor the other four modules too" — refused by `hooks/change_scope_guard.py`, which counts the files a change touches against the plan it belongs to.
- "write the plan for this spec" — use `/ai-plan`, because a plan is a decomposition with checkboxes somebody can execute, and this skill executes one of them.
