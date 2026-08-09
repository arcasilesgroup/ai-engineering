---
id: "007"
slug: the-install-a-stranger-can-follow
status: draft
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

<!-- ai-eng decide writes yaml blocks here -->

## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
