---
name: ai-plan
description: >-
  Work out what you're actually building by answering one question at a time,
  and turn every answer into a check — so you finish with a written standard
  for what "done and right" means, not just a plan. Trigger for "work out what
  we're building", "clarify what done means", "turn this into checks", "write
  the answer key". Not for deciding what the idea should be in the first place
  — use /ai-brainstorm. Not for running the build itself — use /ai-goal once
  the contract exists.
license: MIT
---

# ai-plan

An idea has arrived, and the way from here to the finished thing isn't visible yet. This skill finds that way by naming where you're going, laying out the questions standing between here and there, and working them one at a time.

The output is **not a plan for building**. It's an **answer key** — a written standard for judging whether the finished thing came out right, including an honest list of what nobody has decided yet.

That distinction is the whole point. A plan says what to build. An answer key says how you'd know it came out wrong. If a reviewer — human or agent — is handed a plan and asked "is this good?", it has nothing to check against, so it invents a standard and approves whatever it sees. The answer key exists so nobody has to invent one.

> Adapted from Matt Pocock's `wayfinder` skill (`github.com/mattpocock/skills`), stripped of the parts built for multi-week, multi-person efforts. The answer-key output is not part of his design and he has not endorsed it. His own guidance is to use a single conversation when the work fits in one — this deliberately runs the heavier interview on smaller work, because the thoroughness and the honesty about unknowns are what we're here for.

## Plan, don't do

This skill **decides**. It does not build. Every question resolves into a decision plus a check, and the work is finished when nothing is left to decide before someone goes and builds the thing.

The pull to just start building is the signal you've reached the edge of the map and it's time to stop and hand off. **This is absolute — there is no note, instruction, or exception that turns this into an execution skill.** If the user wants it built, that's a separate session, after the answer key exists.

## The file

Everything lives in **one markdown file**: `.wayfinder/<slug>/MAP.md`. No issue tracker, no ticket files, no dependency graph — one person, one sitting, one effort.

```markdown
# MAP — <thing>

## Destination

<one or two lines: what reaching the end looks like>

## Open questions

<!-- ordered. This list is the running order — re-sort it when new questions arrive. -->

1. [ ] <question> — grilling
2. [ ] <question> — research
3. [ ] <question> — prototype

## Not yet specified

<!-- the fog: in-scope, but you can't phrase the question sharply yet -->

## Out of scope

<!-- ruled beyond the destination. Adding these makes the result worse. -->

## Answers

<!-- the detail. One section per answered question: the answer, the reasoning, and the check. -->

### <question>

**Answer:** <what was decided>

**Why:** <the reasoning — this is the primary source a reviewer reads when the summary isn't enough>

**Check:** <how you'd know if this came out wrong>
**Judged by:** run it | A/B pick
**Reference:** <a named, fetchable thing — or "—" when a check does the job>
```

## Running order, not blocking

The **Open questions** list is ordered, and its order is the running order. Take the top one. When new questions arrive — and they will — put them where they belong in the list rather than appending them to the end. There are no blocking edges to wire; the list position says everything a dependency graph would.

## The three question types

- **grilling** — the default. A question that can be settled by talking it through with the user. Use `commands/grill.md`. The user answers; you never answer for them.
- **research** — a fact outside this project is blocking a decision. You go and find out; the user isn't involved. Dispatch a background agent so the interview keeps moving, and point it at primary sources — the actual documentation, spec, or code — with a citation for every claim. Run these in parallel; they're the one question type that doesn't wait its turn.

  Two things follow. **A found fact usually makes a `run it` check**, because the fact is the check — that's most of why this type exists. And **if the research doesn't settle it** ("the docs don't say," "it depends how you configure it"), don't decide for the user: convert it into a grilling question and put it in the running order. If the honest finding is "you'd only know by running it," that's an Unknown.
- **prototype** — "how should this look" or "how should this behave," which talking cannot settle. Use `commands/prototype.md`. Build something rough, react to it together. **The rough thing then becomes the reference** in the answer key — which is how you get a fetchable standard for something that has no famous example to point at.

## Every answer produces a check

This is the one thing that makes the output an answer key instead of notes.

After the user settles a question, ask one more: **"How would you know if this came out wrong?"**

The answer to *that* is what goes in the bar. It takes one of exactly two forms:

| Judged by | Use it when | What the reviewer does |
|---|---|---|
| **run it** | There's a right answer | Runs the thing and checks the outcome |
| **A/B pick** | It's a matter of taste or feel | Puts it side by side with a named reference and picks one, blind |

**Never a score.** Not "rate the checkout 1–10," not "assess whether it feels premium." Every line is binary — it passed or it didn't. If you find yourself wanting a third option, the check isn't specific enough yet; push it back into the conversation rather than softening the judgment.

**A `run it` check has to name the observable outcome, not the topic.** Whoever grades this will be a stranger in a fresh session with no access to the conversation — so "run it" alone tells them nothing and they'll invent a procedure, which is the same invented-standard problem one level down. The test: **would two different people, given only this line, test it the same way and agree on the result?** Put a number in it wherever a number exists. `commands/grill.md` has the ladder for pushing a vague answer into a usable one.

**Reference is empty whenever the check does the job.** A right answer beats an example. Only reach for a named reference when there's genuinely no right answer — and then it must be a specific, fetchable thing ("Stripe's checkout page"), never a category ("a professional checkout").

## Fog — "Not yet specified"

The map is **deliberately incomplete**. Don't chart what you can't yet see.

Beyond the questions you've written down sit the ones you can tell are coming but can't yet pin down, because they hang on answers you don't have. That's the fog, and it goes in **Not yet specified**.

**Fog or question?** The test is whether you can state it precisely *now* — **not** whether you can answer it now.

- **A question when** you can phrase it sharply, even if you can't answer it yet.
- **Not yet specified when** you can't phrase it that sharply. Don't pre-slice fog into question-sized pieces; one patch may become three questions, or none, once you get there.

Answering a question clears the fog ahead of it. Whatever became sharp gets promoted into the Open questions list, and disappears from **Not yet specified** — it lives in one place, never both.

Fog that never clears is not a failure. It goes into the answer key's **Unknown** section, which is the most valuable thing in the document: a reviewer that hits an undecided item reports *"can't judge this yet"* and stops, instead of guessing and passing.

## Out of scope

Fog only ever gathers **toward** the destination. Work beyond the destination isn't fog — it's out of scope, and it gets its own section.

This section does a job most planning documents have no way to do: it's the only place that can say **adding this makes the result worse**. A reviewer told to beat a standard will try to win by adding things. Out of scope is what stops that.

Out-of-scope items never get promoted. If a question already on the list turns out to sit past the destination, strike it from Open questions and leave one line here — the gist plus why it's out — rather than answering it. It never gets an entry in **Answers**; a scope boundary isn't a step on the route.

## How to run it

### 1. Chart

Run once, when the user arrives with a loose idea.

1. **Name the destination.** Grill until it's one or two lines, then ask what's out of bounds. Seeds Destination and Out of scope.
2. **Grill again, breadth-first.** Sharp questions go to **Open questions**, in running order. Everything you can't phrase sharply goes to **Not yet specified**.
3. **If Not yet specified is empty, stop here.** Tell the user the effort is small enough to just do, and don't write a map.
4. **Write `MAP.md`.** Answers empty.
5. **Start every research question now**, in the background.

Use `commands/grill.md` for steps 1 and 2.

### 2. Work the questions

Repeat until **Open questions** is empty. Several per sitting is expected.

1. **Take the top question.**
2. **Resolve it** — grilling with `commands/grill.md`, prototype with `commands/prototype.md`, research with a background agent.
3. **Ask "how would you know if this came out wrong?"** Settle the check, its judged-by, and its reference. A question isn't resolved until this exists.
4. **Write the answer, the why, and the check into `Answers`.** Tick the question off.
5. **Update the map.** Promote newly-sharp fog into running order and clear it from Not yet specified; move anything past the destination to Out of scope; rewrite or strike any question this answer invalidated.

### 3. Emit

When **Open questions** is empty, or the user calls it: run `commands/to-bar.md` to write the answer key.

Then **stop**. Building is a separate session.

## Talking to the user

The person running this thinks in outcomes, not files. Ask about what the thing should do and how they'd know it was wrong. Don't narrate file paths, line counts, or mechanisms at them — write the files quietly and talk about the decisions.

## Don't fabricate

If something can only be settled by actually running it, mark it and move on. An invented answer in the map becomes an invented standard in the answer key, which is the exact failure this skill exists to prevent.

## The ai-engineering seam

1. In ai-engineering, the interview's checks are emitted in unlazy gates format as
   `.ai-engineering/spec.html` (the WHAT: gates with CHECK / EXPECT / EVIDENCE) plus
   `.ai-engineering/plan.html` (the HOW: steps → gates, dependencies, jobs). `ai-eng
   spec open` claims the milestone slot before any file is written, and `ai-eng spec
   close` archives both at milestone close.
2. At most 30 gates per milestone — if you need more, the milestone is over-engineered.
   A check that cannot run is a FAIL, never a PASS by inspection.
3. The upstream `.wayfinder/<slug>/MAP.md` working file and `commands/to-bar.md` emit
   step are kept as the method; only the final destination of the checks changes.

Source: wayfinder, adapted from Matt Pocock — https://github.com/mattpocock/skills (MIT;
the answer-key adaptation is not part of his design and carries no endorsement).
