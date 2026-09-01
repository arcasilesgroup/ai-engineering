---
name: handshake
description: Interrogate the user about an idea, project, or vision, one question at a time, until you can explain the whole thing so simply a 3rd grader would get it, then capture it in a self-contained doc ready to hand to a researcher agent and a planner agent. Use whenever the user says "handshake", "get on the same page", "align on this idea", "let me explain my vision", or brings a fuzzy new idea that needs to be pinned down before any research or planning starts. Do NOT use for network or protocol handshakes (TCP, TLS, SSL, OAuth, WebSocket, API connections); those are debugging tasks, not vision alignment.
---

# Handshake

Goal: reach true shared understanding of the user's idea, then write it down in a doc that a researcher agent and a planner agent can run with, without needing to ask the user anything.

Do not start building, researching, or planning the idea itself. The handshake ends at the doc.

## The bar

You are done understanding only when you can explain the FULL idea back to the user in language a 3rd grader would get. This is not dumbing the idea down. If you cannot say it simply, you do not understand it yet; there is a gap, and your job is to find that gap and ask about it.

What "3rd grader would get it" means concretely:

- Everyday words only. No term the reader would have to look up.
- Short sentences, one thought each.
- The mechanism is visible: who does what, and what happens next.

**Passing read-back:** "You want to sell little bags of drinking cacao to cafes. The cafe melts one bag into hot milk and sells it as a special drink. You earn money on every bag, and the cafe gets a new drink with almost no work."

**Failing read-back:** "You want a B2B wholesale channel for single-serve cacao units, leveraging existing cafe infrastructure to drive recurring revenue." (Sounds smart, explains nothing. Every noun is jargon.)

## Protocol

### 0. Check what already exists

Before asking anything:

- **Scan this conversation.** If the user already explained the idea, in full or in part, do not ask them to repeat it. Extract everything said so far, build your gap list from it, and open with either your first targeted question or an early read-back of what you understood.
- **Look for an existing handshake doc** on this idea in the project. If one exists, read it, treat it as current truth, and interrogate only what is new, changed, or still marked open. Update that same file; never start a parallel doc.
- **Decide the mode: fresh idea or building into something that exists.** If it is unclear whether the idea lands inside an existing repo or project, make that one of your first questions. This gates how you treat the code around you:
  - **Existing repo or project** → the code is a primary source. Explore it to ground "What exists today", and cross-check what the user says against it. When they contradict, surface it: "You said users can already do X, but the code has no X. Which is it?"
  - **Fresh idea** → leave the code alone. The repo you happen to be sitting in is not part of this idea; reading it wastes time and pollutes the doc with irrelevant facts. Only touch files the user points you to.

### 1. Listen

Only if the idea is not in the conversation yet: "Tell me the whole idea, messy is fine." Let the user empty their head in whatever order it comes out. Do not interrupt the dump with questions.

### 2. Open the draft doc on disk immediately

As soon as you have the dump (or the extraction from chat), create the doc file using the structure below: fill in what you know, mark every gap with `TODO`. Update the file as each answer lands, not at the end.

Why: a handshake can run 30+ questions and outlive the session. The file is the memory. If a session dies mid-interview, the next session reads the draft, sees the remaining TODOs, and continues instead of restarting.

Path: follow the project's doc conventions; otherwise `handshake_<idea>.md` in the project root or docs folder. Tell the user where the draft lives in your first message so they can find it. Renaming later is cheap.

### 3. Interrogate

Keep the gap list in the doc's TODOs. Each question targets the biggest gap, not random curiosity.

- Ask **one question at a time** and wait for the answer. Multiple questions at once are bewildering.
- With each question, offer your **recommended answer** when you have one, so the user can just say "yes" or correct you.
- **Facts vs decisions**: if a fact can be found by exploring the environment (files, tools, a quick search, and the codebase when the mode from step 0 says it is in play), look it up instead of asking. The vision and the decisions belong to the user; put each of those to them and wait.
- **Call out contradictions the moment you spot them.** Quote both statements back: "Earlier you said X, now you said Y. Which one is true?" Never write down two versions of the truth and hope the reader sorts it out.
- **Stress-test with concrete scenarios.** Fuzzy spots hide behind abstractions and show up in stories. Ask "walk me through it: a customer does X, then what happens?" and watch where the story stalls; that stall is your next question.
- If the AskUserQuestion tool is available and a question has a few clear options, use it with your recommendation first.

Gaps that almost always exist, in rough order of importance:

1. **Why** · what itch does this scratch, why now
2. **Who it's for** · who feels the difference when it exists
3. **What success looks like** · how the user will know it worked
4. **What exists today** · current state, prior attempts, assets already in hand
5. **Constraints** · money, time, people, hard rules that must never be broken
6. **Out of scope** · what this is explicitly NOT
7. **Decided vs open** · which choices are locked and which are still up in the air

### 4. Read-back test

Every 5 to 7 questions, and whenever the TODO list looks empty, attempt the read-back: explain the entire idea in 3rd-grader language, a few short paragraphs, then ask "Did I miss anything or get anything wrong?"

- Any correction, however small → back to step 3. The correction reveals a gap you did not know you had.
- A clean pass with nothing missing → step 5.

Attempt the read-back early even if gaps remain; a wrong read-back surfaces misunderstandings faster than ten more questions.

### 5. Early exit

If the user says "enough", "just write it", or clearly wants to stop:

- Offer one last read-back first (it is cheap and catches the worst errors), but respect a no.
- Write the doc with what you have. Every unanswered **decision** goes under `## Decisions still open`, each with your recommended default so the planner is never stuck. Every unknown **fact** goes under `## Open questions for research`. Never silently drop an unanswered question; a visible hole is useful, an invisible one is a trap.
- Set the status line to `handshake incomplete` so downstream agents know to trust it accordingly.

### 6. Finish the doc

After a clean read-back: paste it verbatim into "The idea in plain words", resolve every TODO, and set the status to complete.

## Doc structure

```markdown
# Handshake · <idea name>

Status: draft, interview in progress | complete · <date> | incomplete · <date> | grilled · <date>

## The idea in plain words
<the read-back that passed, verbatim>

## Why this matters
## Who it's for
## What exists today
<verified facts with sources or file paths, not claims>

## What success looks like
## Decisions already made
<locked; the planner should not reopen these>

## Decisions still open
<only the user can close these; include a recommended default for each>

## Constraints and guardrails
## Out of scope
## Open questions for research
<numbered; what the researcher must find out and why each answer matters>

## Handoff notes
<pointers for the planner: suggested order, dependencies, relevant files>
```

Writing rules:

- **Self-contained.** The reader has none of this conversation. No "as discussed", no unexplained shorthand.
- Write the doc in the language the user used most during the handshake; if they mixed languages heavily, ask which one they want (that counts as one question).
- Never use em dashes (`—`, `–`, `--`); use a comma, a period, or `·`.
- Follow the project's doc conventions when they exist (for example a `## Related` section and an index entry in projects that keep a vault or INDEX.md).

## After the doc

Point at the file and offer the next step: run `/grill-me` on the doc to stress-test it, then hand it to the researcher and planner agents.

**The doc is the living source of truth.** After a grilling session, or any later change to the vision, fold what changed back into this same file and update the status line (`grilled · <date>`). A stale handshake doc is worse than none, because the researcher and planner will trust it.
