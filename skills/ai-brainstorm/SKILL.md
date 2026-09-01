---
name: ai-brainstorm
description: >-
  Use when the user brings a fuzzy idea that must be pinned down before research or
  planning — "handshake", "get on the same page", "align on this idea", "let me explain my
  vision", or before ANY creative work (a feature, a component, a behavior change). One
  question at a time until the whole idea can be explained in 3rd-grader language, the
  request classified (spike / bounded / architectural), the design approved, and the result
  captured in a self-contained doc that a researcher agent and a planner agent can run with
  without asking anything. Includes an optional spec self-review pass. Not for turning an
  aligned idea into checks and gates — use /ai-plan. Not for external evidence — use
  /ai-research.
license: MIT
---

# ai-brainstorm — interrogate until shared understanding, then design

Two methods, one flow. **Handshake** interrogates the user until the idea is understood so
completely it can be explained in 3rd-grader language, and captures it in a self-contained
doc. **Design gating** (obra/superpowers) classifies how much process the request needs and
puts a hard approval gate before any implementation. The union: understand first, classify
second, approve before building, and leave a doc the next agent can run with.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any
implementation action until you have told your human partner what you intend and they have
approved it. This applies to EVERY task on EVERY path — the ceremony scales with the task;
the approval gate never does.
</HARD-GATE>

## Three paths (classify out loud before the first question)

Say the classification out loud — "this looks bounded, so I'll present a short design here
rather than write a spec" — so your human partner can override it:

- **Spike** — a feasibility question ("can we...", "is it possible...", "quick and dirty
  is fine") whose output is an answer, not code you keep. Present the question and what
  you'll try in 2-3 sentences, get a nod, then find out as cheaply as correctness allows.
  No design doc. Report findings as a recommendation; anything built stays labeled
  throwaway.
- **Bounded** — a well-scoped change to a flow that already exists in this repo: a new
  flag, a small endpoint, a one-file fix. Bounded measures the REPO, not your familiarity.
  Ask the clarifying questions that matter, present a short design IN CHAT (a few
  sentences to a few short paragraphs), and STOP. Implementation starts only after your
  human partner says yes. No spec file.
- **Architectural** — new projects, new subsystems, changes that restructure how
  components fit together or alter interfaces others depend on. Full process: handshake
  questions, 2-3 approaches with trade-offs, sectioned design, written doc, self-review,
  user review, then planning.

When in doubt between two paths, take the heavier one. The ratchet is one-way: hidden
complexity discovered mid-task upgrades the path — stop, say so, and step up. Nothing
downgrades mid-task.

## Anti-pattern: "too simple to need approval"

Every path ends with your human partner approving your intent before implementation. A
todo list, a single-function utility, a config change — the design may be two sentences in
chat, but you MUST present it and get approval. What scales with simplicity is the
artifact, never the approval.

## Red flags

| Thought | Reality |
|---------|---------|
| "This is too simple to need a design" | Simple means a short design, not no design. |
| "I'll call it bounded and skip the doc" | Reaching for a label to skip work IS the doubt — take the heavier path. |
| "The design is obvious — I'll start while they read it" | The gate is the approval, not the design's length. Present, then stop until you hear yes. |
| "I understand this kind of app, so it's bounded" | Bounded measures the repo, not your familiarity. A new project has no existing flow — it is architectural. |
| "The spike works, so I'll keep the code" | A spike's output is an answer. Keeping the code is a new request — classify it. |
| "They approved the spike, so the follow-up is approved too" | Each task gets its own classification and its own approval. |

## The handshake protocol (how you interrogate)

### 0. Check what already exists

- **Scan this conversation.** If the user already explained the idea, do not ask them to
  repeat it. Extract everything said, build the gap list from it, and open with either the
  first targeted question or an early read-back.
- **Look for an existing brainstorm doc** for this idea. If one exists, treat it as
  current truth and interrogate only what is new, changed, or still open. Update that same
  file; never start a parallel doc.
- **Decide the mode: fresh idea or building into something that exists.** If it is unclear
  whether the idea lands inside an existing repo, make that one of your first questions.
  Existing repo → the code is a primary source (this is where /ai-explore earns its keep):
  cross-check what the user says against it and surface contradictions. Fresh idea → leave
  the code alone.

### 1. Listen

Only if the idea is not in the conversation yet: "Tell me the whole idea, messy is fine."
Do not interrupt the dump with questions.

### 2. Open the draft doc on disk immediately

Fill in what you know, mark every gap with `TODO`, update as answers land — not at the
end. A handshake can run 30+ questions and outlive the session: the file is the memory.
Tell the user where the draft lives in your first message.

### 3. Interrogate one gap at a time

- Ask **one question at a time** and wait. Offer your **recommended answer** when you have
  one, so the user can just say "yes" or correct you.
- **Facts vs decisions**: a fact the environment can answer (files, tools, the codebase)
  gets looked up, not asked. Vision and decisions belong to the user.
- **Call out contradictions the moment you spot them.** Quote both statements back.
- **Stress-test with concrete scenarios.** "Walk me through it: a customer does X, then
  what happens?" Where the story stalls is your next question.

Gaps that almost always exist, in rough order of importance:

1. **Why** · what itch does this scratch, why now
2. **Who it's for** · who feels the difference when it exists
3. **What success looks like** · how the user will know it worked
4. **What exists today** · current state, prior attempts, assets in hand
5. **Constraints** · money, time, people, hard rules
6. **Out of scope** · what this is explicitly NOT
7. **Decided vs open** · which choices are locked and which are up in the air

### 4. The bar: the read-back test

You are done understanding only when you can explain the FULL idea in language a 3rd
grader would get: everyday words, short sentences, the mechanism visible. This is not
dumbing it down — if you cannot say it simply, there is a gap and your job is to find it.

**Passing read-back:** "You want to sell little bags of drinking cacao to cafes. The cafe
melts one bag into hot milk and sells it as a special drink. You earn money on every bag,
and the cafe gets a new drink with almost no work."

**Failing read-back:** "You want a B2B wholesale channel for single-serve cacao units,
leveraging existing cafe infrastructure to drive recurring revenue." (Sounds smart,
explains nothing.)

Every 5 to 7 questions, and whenever the TODO list looks empty, attempt the read-back and
ask "Did I miss anything or get anything wrong?" Any correction → back to interrogating. A
wrong read-back surfaces misunderstandings faster than ten more questions.

### 5. Early exit

If the user says "enough" or "just write it": offer one last read-back (cheap, catches the
worst errors), respect a no, and write the doc with what you have. Unanswered **decisions**
go under "Decisions still open" with your recommended default; unknown **facts** go under
"Open questions for research". Never silently drop a question — a visible hole is useful,
an invisible one is a trap.

## Design (architectural path, after the read-back passes)

1. **Propose 2-3 approaches** with trade-offs, recommendation first. YAGNI ruthlessly.
2. **Present the design in sections** scaled to their complexity, asking after each
   whether it looks right. Cover: architecture, components, data flow, error handling,
   testing.
3. **Design for isolation**: every unit answers what it does, how you use it, what it
   depends on — without reading its internals.
4. **Working in existing codebases**: explore the current structure first, follow existing
   patterns, include targeted improvements the work depends on, propose no unrelated
   refactoring.

## Spec self-review (before user review)

Look at the written doc with fresh eyes:

1. **Placeholder scan** — any TODO, TBD, vague requirement? Fix.
2. **Internal consistency** — contradicting sections? Fix.
3. **Scope check** — one implementation plan's worth, or does it need decomposition?
4. **Ambiguity check** — could any requirement be read two ways? Pick one, make it
   explicit.

For a deeper pass, dispatch a reviewer with
[references/spec-document-reviewer-prompt.md](references/spec-document-reviewer-prompt.md)
(a fresh subagent with no stake in the doc). Only flag issues that would cause real
problems during planning; approve unless there are serious gaps.

## User review gate

Ask the user to review the written doc before planning. If they request changes, make them
and re-run the self-review. Only proceed once the user approves.

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

Writing rules: **self-contained** (the reader has none of this conversation); written in
the language the user used most; never use em dashes (`—`, `–`, `--`) — use a comma, a
period, or `·`.

## What this is not

- "The spike worked, keep building" — a spike's terminal state is a reported
  recommendation. Keeping the code is a new request: classify it.
- "I understand this kind of app" — familiarity is not a flow that exists in the repo.

## Done when

- The read-back passed clean (or the early-exit doc honestly lists what is still open).
- The path was classified out loud and the approval gate was honored.
- The doc is self-contained and lives where the next agent will find it.
- For architectural: the doc passed self-review and the user approved it.

## The ai-engineering seam

1. Output path: `.ai-engineering/brainstorm.md` — a slot, not an archive. It dies at STOP 1
   (contract approval): whatever survived into spec/plan was the signal, the rest was
   noise.
2. The gaps feed ai-plan as files, not chat: "Decisions still open" and "Open questions"
   become ai-plan's question queue.
3. Grounding duty (§11.6): never cite a file or API you have not opened this session —
   /ai-explore and /ai-read-docs are the lenses.
4. The approval gate here IS blueprint STOP 0; the plan approval downstream is STOP 1. One
   idea, two stops, both human.
5. Handoff: after approval, /ai-plan turns the doc into checks and gates
   (`.ai-engineering/spec.html` + `plan.html`). This skill never writes those files.

## Routing

In scope: fuzzy ideas needing alignment, pre-build design, feasibility spikes, vision
capture. Not for: evidence from outside the repo (/ai-research), turning an aligned idea
into executable checks (/ai-plan), running the build loop (/ai-goal), diagnosing failures
(/ai-debug).

Source: handshake by obra (https://obra.sh, MIT; obra/superpowers attributed by URL) +
brainstorming from obra/superpowers
(https://github.com/obra/superpowers/tree/main/skills/brainstorming, MIT) — merged; the
spec-document reviewer prompt is from the same source (MIT).
