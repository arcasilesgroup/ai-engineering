---
id: "007"
slug: the-install-a-stranger-can-follow
status: shipped
date: 2026-08-09
ref: ""
supersedes: ""
---

# The install a stranger can follow, and the diagnosis that says what to type

## Context and problem

Spec 006 built a renderer and drew the screens through it. The operator installed the
result, ran `ai-eng`, `ai-eng init` and `ai-eng doctor` in a real terminal, and sent six
screenshots back. None of the six is a defect in the renderer. Every one of them is the
product saying something true in a form nobody can act on.

**The banner does not enclose itself.** The frame is twenty-six columns and the wordmark
inside it is thirty-two, so the corners sit inside the text they are drawn around. It has
been that way for as long as the drawing has existed and the test that pins it pinned the
mistake byte for byte, because bytes are not a shape.

**`Global ready — 8 skills, 9 entries, v1.0.0 (/Users/…/machine.json)`.** One sentence,
a hundred columns, four facts and a path folded into it. The `8` is a literal: it is a
fact about the wheel that shipped the line and not about the machine reading it, and it
cannot be right after a ninth skill ships.

**`Paste these lines into .github/workflows/check.yml`.** The workflow was printed at the
reader to install by hand. It is the only file this product asks a person to place
themselves, which makes it the only step of an install nothing afterwards can verify — and
the `justfile` written beside it carries `@echo "TODO: your linter"` to every project in
every language, which is a file nobody edits and a `just check` that passes while checking
nothing.

**The last screen ends on a command.** Four steps: fill in the markers, run `doctor`,
paste the block, write a spec. Nothing on it says where the product is actually used. The
guards were just loaded into Claude Code and OpenCode and the install never mentions
either, which is the difference between a thing installed and a thing adopted.

**`doctor` does not say whether it passed.** Twenty-one rows of `ok`, `FAIL` and `?`, and
then, below eight rows of coverage, one unframed line in the same weight as the table above
it. The operator read the whole screen and asked: did it go well, did it fail, what failed
exactly, why, can it be fixed. Four of the twenty-one checks name their cure inside their
prose and seventeen name nothing, so which failures are one command away and which are a
person's work is a judgement every reader has to make again.

**The coverage block is vocabulary all the way down.** `T2 cursor not installed UNPROVEN`.
Four tiers and four verdict words, each of them exact, none of them defined anywhere the
person running the command will see. The operator's words: *no entiendo nada, qué ayuda eso
a los usuarios, y sobre todo cómo se resuelve.*

Underneath all six is one complaint, and it is not about looks. The product is honest and
unreadable. An honest report nobody can act on buys exactly as much as a dishonest one.

## Options considered

1. **Treat it as six independent cosmetic fixes.** Cheapest. It also leaves the shape that
   produced them: a screen is finished when what it says is true, and nobody asks whether
   what it says can be acted on. The banner is the proof — it was wrong in a way that only
   looking catches, and looking was never part of done.
2. **Rewrite the screens against a "what do I type next" rule.** Every failure carries the
   command that repairs it or says in as many words that no command does. Every piece of
   vocabulary arrives with the sentence that defines it. Every file the install needs is
   written by the install. Costs a reversal of ADR 0002 and a fourth column in the coverage
   block, and it is the only option that changes what "done" means for the next screen.
3. **Ship documentation instead.** A page explaining tiers, verdict words and cures. Costs
   least in the product and moves the whole problem to a file nobody opens at the moment
   they need it, which is while the terminal is still on the screen.

## Decision

Option 2.

The rule the six fixes are drawn from: **a screen that reports a problem names what to do
about it, in the vocabulary of the person reading, at the moment they are reading it.** A
failure with no command says so. A word that means something exact is defined on the line
it appears on. A file the install needs is written by the install, not described to a
person as homework.

The reversal is real and it is written down separately: ADR 0002 refused `doctor --fix`
three days ago and ADR 0003 supersedes it. The argument that changed is not the ask. It is
that `--fix` here calls the consented verbs by name and in this process — `ai-eng update`
keeps its dirty-tree refusal, its no-keyboard refusal and its typed `y`, because `--fix`
runs the verb rather than a copy of what the verb does. ADR 0002 examined a `--fix` that
reimplemented the writes with the gates removed, and it was right about that one.

## Decisions

```yaml
adr: 0003
title: A diagnostic may run the consented verb that cures what it found
```
```yaml
decision: A screen that reports a problem names what to do about it
date: 2026-08-09
rationale: six screens were true and unusable at once: a banner whose frame was twenty-six
  columns around a wordmark of thirty-two, one hundred-column sentence carrying four facts and a
  literal skill count that could not be right after a ninth skill shipped, a workflow printed at
  the reader to install by hand, a last screen that never said where the product is actually
  used, twenty-one rows of ok and FAIL with no verdict over them, and a coverage block of four
  tiers and four verdict words defined nowhere the person running the command would see. The
  rule the six fixes are drawn from is that a screen reporting a problem names what to do about
  it, in the vocabulary of the person reading, at the moment they are reading it: a failure with
  no command says in as many words that a person does this one, a word that means something
  exact is defined on the line it appears on, and a file the install needs is written by the
  install rather than described to somebody as homework. An honest report nobody can act on buys
  exactly as much as a dishonest one.
```
```yaml
decision: init writes the pin when it is absent and never rewrites it
date: 2026-08-09
rationale: spec 005 decided a re-run would back the pin up and rewrite it, printing a line,
  which is safe enough while the only way to reach it is typing the command; doctor --fix made
  it reachable from a diagnostic, and that is ai-eng update with its dirty-tree refusal, its
  no-keyboard refusal and its typed y all removed, which is precisely and literally the
  objection ADR 0002 raised and ADR 0003 claims does not apply to a --fix that calls the
  consented verb by name. The fix is the rule and not the caller: init writes .ai/config.toml
  and .ai/.gitignore when they are absent, says on its own line which of them was already there
  and names update as the only verb that changes the pin, so a rewrite that reset the pinned
  version, the guard windows and the observability endpoint somebody's alerts point at stops
  being something any caller can reach. This reverses spec 005's decision in the other
  direction, which is written here rather than left implicit.
```
```yaml
decision: Every file the install needs is written by the install
date: 2026-08-09
rationale: the CI workflow was printed at the reader under paste these lines into, which made it
  the one file this product asked a person to place by hand and therefore the one step of an
  install nothing afterwards could verify, and the justfile written beside it carried a TODO:
  your linter recipe into every project in every language, which is a file nobody edits and a
  just check that passes while checking nothing. The workflow joins OFFERS, so it is written
  when absent and goes through the same picker and the same dated backup when it is not;
  skeletons.justfile fills lint, test and build from RECIPES for every stack detected and leaves
  the TODO only for a stack it cannot name; and init gains --no-project, because --no-global
  existed and its opposite did not, which is what doctor --fix needs to rewire a machine without
  also deciding to set up whatever repository the person happened to be standing in.
```
```yaml
decision: A renderer without a decorated test has no test
date: 2026-08-09
rationale: the suite reads the undecorated stream on purpose so that every assertion holds the
  bytes a user with no colour sees, and the cost of that is that a style name and a stream flag
  are both invisible to it: every colour in three new renderers and four new screens could be
  deleted, and every line moved from stdout to stderr, with the whole thing green. The mutation
  floor found 358 lines of exactly that in one branch and spec 006 had already paid for the same
  lesson without writing it down, so a renderer is asserted decorated at least once, and a verb
  whose every line is the report asserts the other stream is empty rather than asserting thirty
  lines one at a time.
```
<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

```yaml
id: R-007-02
finding: fix-never-run-off-linux
severity: medium
accepted_by: soydachi
accepted: 2026-08-09
expires: 2026-11-07
renewals: 0
justification: doctor --fix writes to the machine: it runs init in this process with -y
  appended, then asks the whole question again, and the only job that installs the wheel on
  macOS and Windows runs doctor and doctor --paths and never the flag that repairs, so the one
  verb in this product that both diagnoses and writes ships exercised by unit tests and on a
  developer's Linux and macOS shell alone; the blast radius is bounded by what init writes,
  which overwrites nothing of yours because -y leaves the picker with nothing ticked, and the
  two ways the recursion could go wrong are asserted here rather than there
follow_up: the install matrix grows one ai-eng doctor --fix line per platform after the existing
  doctor call, or this is renewed once with the reason and then fixed
```
```yaml
id: R-007-01
finding: shipped-counts-recipe-reports-todo
severity: low
accepted_by: soydachi
accepted: 2026-08-09
expires: 2026-11-07
renewals: 0
justification: the justfile this install writes now fills lint, test and build from RECIPES for
  every stack it detected, and its counts recipe still emits RAN lint=TODO in every language, so
  the one line whose whole job is to prove a tool read the files it counted proves nothing in
  somebody else's repository; the number has to come from the tool that did the work and there
  is no cross-language way to ask for it that is not a guess, and a guess there is exactly the
  green nobody earned that the recipe exists to prevent
follow_up: either RECIPES grows a counting command for each stack that can answer one, and the
  marker survives only for the stacks that cannot, or the recipe is deleted rather than shipped
  hollow
```
<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [x] CI/CD — `just check`, run by `.github/workflows/check.yml` on every push; this spec is also what writes that file into somebody else's repository, and `.github/workflows/release.yml` is what publishes the wheel
- [x] Logs — `ai-eng digest`: `--fix` runs each cure through `cli.main`, so a repair leaves one command event per verb it ran and not one line claiming it ran them
- [x] Traces — not applicable, and that is the rule: one process, no second hop, no trace
- [x] Errors — `cli.main` emits an event of the error class before it re-raises, and `repair` stops at the first cure that exits non-zero and says the rest was not attempted rather than continuing over a broken machine
- [x] Health and data age — `ai-eng doctor` is the subject of this spec: 20 assertions, a verdict that says whether it passed, and `ai-eng doctor --fix` for the ones a command reaches
- [x] External check — `.github/workflows/install-matrix.yml` runs the built wheel on three platforms against a repository it has never seen; what it cannot check is R-007-02, because it runs `doctor` and never `doctor --fix`
- [x] Second path — `repair` re-runs the whole diagnosis with the flag removed and reports the new verdict, so what a repair claims is recomputed by the same twenty assertions rather than inferred from the cures having exited 0: `ai-eng doctor --fix`
- [x] Security — `just security`: gitleaks, semgrep and trivy on every push
