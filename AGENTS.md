# How work happens here

This file is always loaded. It holds only facts that are true in every session and that
you cannot work out by reading the repository. Everything else is a skill, and a skill
costs nothing until it is invoked.

Project identity — mission, vocabulary, prohibitions — is in `CONSTITUTION.md`. Read it
once per session. `CLAUDE.md` is one line that imports this file.

## The twelve rules

1. No code before an approved plan (more than 3 files).
2. One commit, one change.
3. Never `--no-verify`. Never silence a linter (`noqa`, `@ts-ignore`, `nosec`).
4. No compatibility shims. Hard rename, hard delete; say it in the changelog.
5. Delete before you abstract.
6. Green gate before "done" — show the output.
7. Stuck twice, stop and say so.
8. No secrets, no personal data, no machine paths in committed files.
9. Explain it so somebody who does not code can follow.
10. KISS, YAGNI, DRY, SOLID, TDD, Clean Code, Clean Architecture — the criteria a review
    judges a diff by and a spec justifies a decision with, one line each.
11. Monitoring, metrics and observability first. Nothing gets a URL until CI/CD, logs,
    traces, errors, health and data age, an external check, a second path and security all
    pass, and each one passes with a command rather than an assertion.
12. A decision that always comes out the same is code, not a prompt. The third time the
    same judgement resolves the same way it becomes a script, and the prompt that made it
    goes away in the same commit. The script lives in this repository, has one check, runs
    inside `just check`, and fails closed. If it cannot fail closed, it stays a prompt and
    you write down why.

## What this project is

A wheel on PyPI that carries eight skills, eight guards and a ten-verb CLI. One command
places the skills and registers the guards in the settings file each surface already
reads, so they are present in every project on a machine without a single file landing in
any of them. It writes specs, plans, decisions and dated risk acceptances as plain text in
the user's repository, and verifies them with a command that exits non-zero.

## The shape of the tree

- `hooks/` — the dispatcher, the two decorators, five guards, two telemetry hooks. Standard
  library only, executed by path, never importing the package: on the hot path that import
  costs about 110 ms, and a slow guard is a disabled guard.
- `src/ai_engineering/` — the ten verbs. This half may import freely.
- `policy/` — data, not code: the IOC catalogue, the surface wiring table, the semgrep
  rules, the plain-language glossary.
- `surfaces/` — the OpenCode plugin. Everything else is wired by writing JSON.
- `.agents/skills/` — the only skill tree. No mirrors, no sync, no second copy.
- `specs/`, `docs/adr/` — the record. Committed, reviewed in a pull request.
- `.ai/` — disposable, except `config.toml` and `.gitignore`, which are the pin.

## The two contracts that must not bend

**A hook declares its class at the top of its own file.** `@guard` fails closed: if it
cannot decide, nothing passes, including when it crashes. `@telemetry` fails open and
never opines. You cannot write a fail-open guard without noticing, because "fails open"
lives in a decorator called telemetry. A test reads the dispatcher table and turns CI red
if a hook on a blocking event is not a guard.

**Every file class has one home.** Framework files live in `.ai/`, `specs/` or
`docs/adr/`, and nowhere else. `ai-eng doctor` prints one line per class with its exact
path, and fails when something appears outside them. That check is the first step back
from 528 files, which is where the previous version ended up.

## Working here

- `just check` is what CI runs. Run it before saying anything is done, and show the output.
- The line ceiling lives in `contract.REPO_CEILING` and CI fails the build on the line
  after it. When it is genuinely too low, raise it in a commit whose message says why —
  that commit is the conversation you would otherwise never have had. It has moved once,
  from 5,000 to 5,600, and specs/001-v1-from-scratch records the arithmetic.
- `AGENTS.md` is capped at 150 lines by a test. Everything that is not true in every
  session belongs in a skill.
- Every `SKILL.md` is capped at 80 lines. Longer means it is a procedure that should be a
  script, which is rule 12 applied to our own files.
- Three surfaces read UNPROVEN in the coverage line and they stay that way until a denial
  actually executes there. A green nobody has earned is the failure this product cures.

## How to run it

```
uv sync                       # or: pip install -e .
just check                    # the gate, exactly as CI runs it
python tests/adversarial/run.py   # twelve attacks and a clean control
```
