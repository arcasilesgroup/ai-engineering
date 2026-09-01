# to-bar — emit the answer key

Turn the finished map into the answer key the reviewer judges against. In ai-engineering
the checks land in gates format in `.ai-engineering/spec.html` (the WHAT) alongside
`.ai-engineering/plan.html` (the HOW); the format below is that contract's source.

Don't interview here. Everything in this document was already decided; you're rewriting it into the form a reviewer can use.

## The one rule

**This is not a spec.** A spec tells someone what to build. An answer key tells someone how to know it came out wrong. They are different documents and the failure mode is drifting from the second into the first.

The test, applied to every single line before you write it:

> Could a stranger who has never seen this project **check** this against a finished thing, and get a yes or a no?

If the line describes what to build — "add a login page," "the schema stores a plan tier," "as a customer I want to see my balance" — it has drifted. Cut it or rewrite it into something checkable.

Do not add a problem statement, a solution section, user stories, implementation decisions, or a module list. Not as a header, not as helpful context, not "just so the reviewer understands." Every one of those is build-instruction, and every one of them gives a reviewer something to nod along to instead of something to check.

## The format

````markdown
# ANSWER KEY — <thing>

## How to use this document

You are judging finished work against this standard. Read these rules before you judge anything.

1. Judge **only** the checks in "The bar" below. Do not judge anything else, however obviously good or bad it looks.
2. Every check is **binary** — it passes or it fails. Never give a score, a rating, or a percentage. There is no partial credit.
3. Do not invent a standard. If something matters and isn't on this list, that is deliberate — it is either out of scope or undecided, both of which are listed below.
4. **Items under "Unknown" may not be judged.** They are numbered `U1`, `U2`, and so on. If the work touches one, report `U<number>: CANNOT JUDGE` and stop on that item. Do not guess, do not infer what was probably intended, do not pass it because it looks reasonable. Reporting that you cannot judge something is a correct and expected outcome, not a failure.
5. Items under "Out of scope" must not be rewarded. Work that adds them is **worse**, not better, no matter how impressive it looks.
6. If a check looks arbitrary, open the map file in this same folder. It holds the reasoning behind every check, linked from the last column. Read the reasoning before deciding a check is wrong.
7. If you built any of this work yourself, stop and say so. Judging your own output is not judging.

### Report your verdict exactly like this

One line per bar check, in order, then one line for each Unknown item the work touched. Nothing else:

```
1: PASS
2: FAIL — <what was wrong, in one line>
3: PASS
U2: CANNOT JUDGE
```

`PASS`, `FAIL` and `CANNOT JUDGE` are the only three verdicts. Bar checks are numbered plain (`1`, `2`); Unknown items carry their `U` (`U1`, `U2`). A bar check is never `CANNOT JUDGE` — every one of them was written to be gradeable, so if you can't grade one, say which and why in a `FAIL` line rather than inventing a verdict.

Then one final line:

```
RESULT: PASS                  — every bar check passed and no Unknown was touched
RESULT: FAIL                  — any bar check failed
RESULT: BLOCKED — U2, U5      — no bar check failed, but the work touched these Unknowns
```

`BLOCKED` means the work cannot be signed off until a person decides the listed items. It is **not** a failure of the work, and it is **not** something you can resolve by looking harder — looking harder is exactly what produces an invented answer. If you are running in a loop, `BLOCKED` ends the loop and hands back to a human; it does not mean try again.

## Destination

<one or two lines: what done looks like>

## The bar

| # | check | judged by | reference | from decision |
|---|-------|-----------|-----------|---------------|
| 1 | <what must be true, stated so it can be checked> | run it | — | [<question>](<map file>#<anchor>) |
| 2 | <what must be true> | A/B pick | <named, fetchable thing> | [<question>](<map file>#<anchor>) |

## Out of scope

Adding any of these makes the result **worse**. Do not reward them.

1. <thing> — <why it's out>

## Unknown

**These are not gradeable.** Nobody has decided them yet. If the work touches one, report `U<number>: CANNOT JUDGE` and stop on that item.

- **U1** — <the undecided question, stated plainly>
- **U2** — <the undecided question, stated plainly>
````

## Filling in the columns

**check** — one thing that must be true, phrased so someone can verify it without asking a follow-up question. Take it from the decision's **Check** line in the map. If a decision produced no check, it does not go on the bar; if it produced two, it's two rows.

Assume the reader is a stranger in a fresh session who will never see the conversation this came from, and who will read this file again on every round of a loop. So:

- **Name the observable outcome, not the topic.** "Billing works correctly" is a topic. "Upgrading to annual on day 10 of a 30-day month charges the annual price minus two-thirds of the monthly price already paid" is a check. The test: **would two different people, given only this line, test it the same way and agree on the result?**
- **Put a number in it wherever a number exists** — amounts, counts, timings, limits. A number is the cheapest way to make a check unarguable, and it's why the `BAR.md` format this borrows from uses numeric thresholds.
- **One thing per row.** A row with "and" in it can half-pass, and half-pass is the score you just banned.
- **Keep it to one line.** This file is re-read every round; length is a running cost and long rows get skimmed.

**judged by** — exactly `run it` or `A/B pick`. Nothing else is a legal value. Not "review," not "inspect," not a number. If a check doesn't fit either, it isn't finished — leave it off the bar rather than inventing a third kind of judgment, and say which one you dropped and why.

**reference** — `—` for every `run it` row, always. For `A/B pick`, a specific thing that **opens without a build step**: a live URL, a single self-contained file, or a screenshot. A prototype from the interview qualifies only in the form `prototype.md` requires — one double-clickable file or an image. Anything needing a server, a database, or the right branch checked out is a dead link by the time someone grades this.

Never a category. "A clean modern dashboard" is not a reference; it's an invitation to invent one, which is the failure this whole document exists to stop.

An A/B row is judged **blind** — whoever sets up the comparison shows both artifacts unlabelled and asks which is better. Knowing which one is the reference is enough to decide the answer on its own.

**from decision** — a link back to that decision's section in the map file. This is the part people skip and it does real work: a reviewer that can read *why* a decision was made judges better than one reading a one-line summary. When a check looks arbitrary, the link is what explains it.

## Unknown is the most important section

Everything else on the page has an equivalent somewhere. This doesn't.

It's a **pre-registered, enumerated list of what nobody has decided**, written before any judging starts. A reviewer with no such list, handed something it can't properly assess, will assess it anyway — that's the whole problem. This makes not-judging an available, legitimate, named outcome.

Fill it from two places:

- **Not yet specified** in the map — fog that never cleared.
- Any decision where the honest check was "you'd only know by running it with real users."

Number them `U1`, `U2`, … — the `U` prefix keeps them from colliding with the bar's numbering when a verdict names one. State each as a plain question, and don't soften them into things that sound decided. "How aggressively to retry failed payments" is right. "Retry behaviour to be refined" is not — it reads like a plan and a reviewer will grade it.

**An empty Unknown section is a warning sign.** It usually means the interview stopped early or the fog got quietly filled in with plausible answers. Say so rather than shipping a document that claims certainty nobody has.

## Before you write the file

Check each of these, and report anything that fails rather than fixing it silently:

- Every `judged by` is `run it` or `A/B pick`. No exceptions.
- Every `run it` row names an observable outcome, not a topic — two strangers would test it the same way and agree. Numbers wherever numbers exist.
- No row contains "and". One thing per row, or it can half-pass.
- Every `A/B pick` has a reference that opens without a build step — a URL, one self-contained file, or a screenshot. No categories.
- Every `run it` has `—` in the reference column.
- Every row links back to a decision.
- Every row is one line. This file is re-read on every round of the loop.
- Unknown items are numbered `U1`, `U2`, … so a verdict can name one without colliding with a bar number.
- Nothing on the bar describes what to build rather than how to check it.
- Out of scope isn't empty — if it is, the destination was never scoped and a reviewer has nothing stopping it from rewarding scope creep.
- Unknown isn't empty — if it is, say so out loud.

Then write the file and stop. Building is a separate session.
