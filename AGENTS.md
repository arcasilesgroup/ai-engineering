# How work happens here

This file is always loaded. It holds only facts that are true in every session and that
you cannot work out by reading the repository. Everything else is a skill, and a skill
costs nothing until it is invoked.

Project identity — mission, vocabulary, prohibitions — is in `CONSTITUTION.md`. Read it
once per session. `CLAUDE.md` is one line that imports this file.

## The twelve rules

1. No code before an approved spec and plan (more than 3 files).
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

A wheel on PyPI that carries seventeen skills, four guards and a ten-verb CLI. One command
places the skills and registers the guards in the settings file each surface already
reads, so they are present in every project on a machine without a single file landing in
any of them. It writes specs, plans, decisions and dated risk acceptances as plain text in
the user's repository, and verifies them with a command that exits non-zero.

## The shape of the tree

- `hooks/` — the dispatcher, the two decorators, four guards, two telemetry hooks. Standard
  library only, executed by path, never importing the package: on the hot path that import
  costs about 110 ms, and a slow guard is a disabled guard.
- `src/ai_engineering/` — the ten verbs. This half may import freely.
- `policy/` — data, not code: the IOC catalogue, the surface wiring table and the semgrep rules.
- `surfaces/` — the OpenCode plugin. Everything else is wired by writing JSON.
- `.agents/skills/` — the only skill tree. No mirrors, no sync, no second copy.
- `specs/`, `docs/adr/` — the record. Committed, reviewed in a pull request.
- `.ai/intent.md` — the user-owned, non-disposable canonical Intent.
- `.ai/` — otherwise disposable, except `config.toml` and `.gitignore`, which are the pin.

## One writer, and readers only when independence is what you are buying

Every commit is made by one agent, in order, with the gate green after each. No block of
work is split between parallel writers, and this is not a performance opinion: two writers
share an index, and `git add -A` from either takes the other's work into its commit.

The five critics — `/ai-challenge`, `/ai-council`, `/ai-review`, `/ai-verify` and
`/ai-security` — are the exception, and they are marked the same way in their frontmatter:
`context: fork`, `background: false`. They run apart because what a separate reader buys is
independence, not speed. A critic that sees the author's reasoning inherits it.

The fan-out is only paid in wall-clock if something waits on it. Where the host can start
several at once it does; where it cannot, they run one after another, and the output is
identical either way — which is what stops anybody claiming a parallelism they did not have.

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
- Size is bounded by `contract.TEST_RATIO_MAX`, and by nothing else. A total-line ceiling
  was tried and deleted: it was obliged to follow the tree it bounded, so it moved in fifty
  of fifty commits and never caught a defect. Every number this file needs is named here and
  stored elsewhere; this file names the home and never the value, because a doctrine that
  quotes a number is a doctrine that goes stale without a test.
- `AGENTS.md` is capped by a test at the length in `tests/test_contracts.DOCTRINE_CEILING`.
  Everything that is not true in every session belongs in a skill.
- Every `SKILL.md` is bounded by how hard it reads, at `contract.SKILL_FOG_CEILING`,
  and by nothing else. A line cap was tried and deleted: it was spent on frontmatter and
  blank lines, it bound one file, and nothing bounds length now.
- No surface reads BLOCKS until a denial has receipted there, and none has. The word is
  read from a receipt and there is no field left that can assert it. A green nobody has
  earned is the failure this product cures.

## How to run it

```
uv sync                       # or: pip install -e .
just check                    # the gate, exactly as CI runs it
python tests/adversarial/run.py   # every attack, and a clean control it must not fire on
```
