---
name: ai-brainstorm
description: >-
  Aligns fuzzy ideas before research or planning: interview, classify, and capture the
  approved intent. Trigger: "handshake", "align on this idea", "my vision", or a new
  feature/component/behavior. Do not use as a preflight for Direct/light work with a clear outcome.
  An aligned build goes to
  /ai-orchestrator; external evidence goes to /ai-research.
license: MIT
---

# ai-brainstorm — interrogate until shared understanding, then design

Two methods, one flow. **Handshake** interrogates the user until the idea is understood so
completely it can be explained in 3rd-grader language. **Design gating** (obra/superpowers)
classifies how much process the request needs and puts an approval gate before
implementation on the paths this skill owns. Standard/full feature lanes capture a
self-contained doc; light lanes end with an answer or an in-chat design and write no slot.

<HARD-GATE>
On a path owned by this skill, do NOT invoke an implementation skill, write code, scaffold a
project, or take implementation action until you have told your human partner what you intend
and they have approved it. This gate applies only to this brainstorm flow; Direct/light work
routed elsewhere does not enter it.
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

The path picks the lane you start in: **spike → light, bounded → light, architectural → full**.
Bounded is the one that steps up — the moment it stops being one sitting (it touches an
interface others depend on, or produces receipts somebody else has to read) it takes the
**standard** lane, and ai-orchestrator builds it. Architectural is
always a contract, from the first question. On the light lane nothing is written to a slot at
all: a spike ends at ai-verify with its answer, and a bounded change ends at ai-verify with its
diff.

## Anti-pattern: "too simple to need approval"

Every brainstorm path that proceeds to implementation ends with your human partner approving
your intent first. A small change may need only a few sentences in chat, but you MUST present
that design and get approval. Direct/light work routed elsewhere does not enter this gate.

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

The brainstorm does not run a worktree preflight. The orchestrator owns the
read-only local `ai-eng worktree list` before build work begins; there is no
pre-worktree approval projection. Keep the interview in the current clone or
selected worktree. Never merge an unapproved sibling; never fetch or sync remote
state.

- If lifecycle state is already available, surface a pending plan approval as
  `awaiting-plan-approval` with `plan_approval: pending`, a pending app review as
  `awaiting-app-review` with `app_review: pending`, and `ready-to-merge` with
  `app_review: approved`. Do not reduce these to a generic pending-approval label.
  For pending plan approval, ask the human to **Approve**, **Edit**, or **Stop**
  before implementation continues. For pending app review, ask the human to
  **Approve**, **Request changes**, or **Stop here** before merging. For
  `ready-to-merge`, ask whether to continue the merge before any merge action.
  Unknown lifecycle state is not approval.

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
worst errors) and respect a no. On standard/full lanes, write the doc with what you have.
On light lanes, give the answer or in-chat design without writing a slot. In the doc,
unanswered **decisions** go under "Decisions still open" with your recommended default;
unknown **facts** go under "Open questions for research". Never silently drop a question —
a visible hole is useful, an invisible one is a trap.

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

## User review gate (standard/full feature lanes)

When the page is written, stop. The last line to the user is: the interview is in `.ai-engineering/brainstorm.html`. Say approve, or say what to change. Do not start `ai-orchestrator` in this turn.

If they request changes, make them and re-run the self-review, then ask again.

When they approve, do step 5 of the seam, then stop again. The last line is: next step is `/ai-orchestrator`. That call starts the build. Do not open checkpoints in this turn.

On light lanes, use the spike answer or approved in-chat design and finish at `ai-verify`.
Do not write a design slot or invoke `ai-orchestrator`.

## Doc structure (standard/full feature lanes only)

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

The heading structure above is the CONTENT contract. The file is one self-contained
HTML page at `.ai-engineering/brainstorm.html`, rendered with the artifact design
system — [references/artifact-design.md](references/artifact-design.md) — so it reads as
one family with the research pages and the recap:

- `<header class="hero">` with the `{ai}` favicon, stamp `Brainstorm · <idea>`, h1
  `<idea name>`, `.sub` carrying the read-back that passed, `.meta` with the status
  line (`draft · interview in progress` / `complete · YYYY-MM-DD`).
- Two meta tags in `<head>`, so a later run can tell this interview from an older one:
  `<meta name="ai-feature" content="<slug>">` and, only after approval,
  `<meta name="ai-approved" content="YYYY-MM-DD">`. The slug is the kebab-case name
  of this idea and the identifier `ai-orchestrator` will use for it.
- One `<section>` per markdown heading above, each with `h2 .num` (`01`–`11`), in the
  same order. "Decisions already made" and "Decisions still open" use `note ok` /
  `note warn`; "Open questions for research" is a numbered `ol` (the numbers are what
  ai-orchestrator cites); "Out of scope" uses `note danger`.
- Sticky `<nav>` with one `<a>` per section, `<main id="main">`, `<footer>` with the
  `{ai}` mark and the status.
- Draft is a living page: update the sections in place as answers land, never rewrite
  from scratch.

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
- On standard/full lanes, the doc is self-contained and lives where the next agent will find it.
- On light lanes, no slot is written; the answer or diff ends at `ai-verify`.
- For architectural: the doc passed self-review and the user approved it.

## The ai-engineering seam

Only standard/full feature lanes use the slot-writing steps below. Handoff follows the lane.
Spike and light/bounded paths write no design slots and do not invoke `ai-orchestrator`;
they finish at `ai-verify`. The grounding duty in step 3 applies on every lane.

1. Output path: `.ai-engineering/brainstorm.html`. Approval does not delete it.
   `ai-orchestrator` reads it for the whole build. Git integration closes the
   feature; `brainstorm.html` and an optional `recap.html` remain local evidence.
   The recap is optional and never a prerequisite to integrate. Write it with the file
   tools, or with a redirect: `rm`, `mv` and `tee` into `.ai-engineering/` are denied,
   because a verb that can act on several paths is judged as a whole command.
   Render it with the artifact design system —
   [references/artifact-design.md](references/artifact-design.md):
   copy that document's whole CSS block in verbatim — tokens, layout rules and
   components, not tokens alone — same family as the research pages and the recap.
   Before
   `</body>`, copy that file's scroll-spy script verbatim (it is already in
   `templates/brainstorm.html.tpl`): it marks the nav link for the section in view.
   The markdown
   structure in §Doc structure maps to sections of that page; the file is HTML only,
   no `.md` twin.
2. Keep the gaps in the approved documents, not chat: "Decisions still open" and "Open questions"
   stay available to the next skill. On the standard lane, they become the orchestrator's
   question queue.
3. Grounding duty (§11.6): never cite a file or API you have not opened this session —
   /ai-explore and /ai-read-docs are the lenses.
4. On standard/full lanes, the approval gate here IS blueprint STOP 0. After approval, a new checkpoint plan
   proceeds to implementation without another approval stop; resumed legacy pending plans
   retain their checkpoint review. The final app review remains a human stop.
5. After approval, set `ai-approved` to today's date and the status line to `complete · YYYY-MM-DD`. Copy only the conclusions into `.ai-engineering/PRD.html`: Problem (why it matters), Goal (what success looks like), Users & roles, the Feature plus its Rules (decisions already made), and Out of scope. Leave the interview in `brainstorm.html`. If the PRD already has other features, update the matching one and leave the others. Commit only these two files using explicit paths:
   ```bash
   git add -- .ai-engineering/brainstorm.html .ai-engineering/PRD.html
   git commit -m "docs: approve brainstorm" --only -- .ai-engineering/brainstorm.html .ai-engineering/PRD.html
   ```
   This skill never writes spec.html or plan.html.
6. Handoff, said out loud after approval, follows the lane:
   | Lane | Next step |
   | --- | --- |
   | Architectural | `/ai-architect` |
   | Standard | `/ai-orchestrator` |
   This turn does not run the next skill.

## Routing

In scope: fuzzy ideas needing alignment, pre-build design, feasibility spikes, vision
capture. Not for: clear Direct/light tasks such as bug fixes or one-session changes (follow
their relevant skill or Direct rhythm without ai-brainstorm), evidence from outside the repo
(/ai-research), turning an aligned idea into a build (/ai-orchestrator), or diagnosing failures
(/ai-debug).

## Lifecycle

Lane: light, standard, full
Writes: standard/full only: .ai-engineering/brainstorm.html, .ai-engineering/PRD.html; light: none
Read by: ai-orchestrator on standard/full, the agent that opens the next session
Dies: when a brainstorm for a different feature replaces it, or the feature is integrated
Next: ai-research when questions are still open; architectural → ai-architect → ai-orchestrator; standard → ai-orchestrator; Direct/light/spike → follow the relevant skill or Direct rhythm without the full brainstorm path (brainstorm light paths end at ai-verify)
Stop: interview
Stop words: approve, ok, go, adelante
Stop confirms: the brainstorm
Stop runs: Standard writes the PRD conclusions and hands off to /ai-orchestrator; Architectural writes the PRD conclusions and hands off first to /ai-architect, whose Lifecycle continues to /ai-orchestrator; Direct/light/spike do not invoke the full brainstorm path, and brainstorm light paths end at ai-verify

Source: handshake by obra (https://obra.sh, MIT; obra/superpowers attributed by URL) +
brainstorming from obra/superpowers
(https://github.com/obra/superpowers/tree/main/skills/brainstorming, MIT) — merged; the
spec-document reviewer prompt is from the same source (MIT).
