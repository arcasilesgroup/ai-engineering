# Intake: reaching shared understanding before the record exists

Read this file before the first intake question. It carries the detail of `ai-spec`
step 0: what to ask, in what order, what to write down while asking, and the one test
that ends the interview. The step in the skill is the contract; this file is how to
keep it.

## What ends step 0

Three things, each visible, none optional:

1. The goal, its constraints and its acceptance are named. The opening request or
   `specs/new-goal-template.md` supplies them; a question goes to the owner only for a
   part that is missing.
2. Everything the tree, a search, or a command can answer has been answered that way,
   not asked. The owner supplies vision and decisions; facts about the repository are
   looked up and cited at `file:line` instead of costing a question.
3. The owner has confirmed a plain-words read-back. Until that yes exists, nothing is
   scaffolded: `ai-eng spec new` is the last move of intake, never the first. Under an
   unattended goal there is no owner to confirm; carry on, and move the read-back into
   the scaffold's `## Assumptions and unresolved risks` as "unconfirmed", beside the
   draft's other contents, when the scaffold is created.

## The live draft

From the owner's first answer, keep a draft file on disk and update it after every
answer, not at the end. It holds what is known, and one `TODO` line per open gap. The
draft lives at `.ai/intake-<slug>.md`, under `.ai/`, which is disposable by design. If the session dies
mid-interview, the next one reads the remaining `TODO` lines and continues; nobody
re-asks an answered question. Never write an answer the owner did not give. When the
scaffold is created it writes a blank template over nothing — it does not read your
draft — so the author moves the draft's contents into the spec's sections, then
deletes the draft. One home per file class, and the draft is the crash-recovery copy,
not the record.

## Asking

- One question at a time, the biggest open gap first. Each carries your recommended
  answer, so the owner can confirm it or say what is wrong.
- A fact you could look up is not a question. Ask decisions and vision; look up the rest.
- When two answers contradict each other or the tree, quote both and ask which is true
  before writing either down. Two versions of the truth in one draft is how a record
  starts lying.
- Stress-test with a story: "walk me through it, a person does X, then what?" Where
  the story stalls is the next question.
- Order the gaps roughly: why this and why now; who feels the difference; what makes it
  a success; what already exists; the hard limits; what is explicitly not being built;
  which choices are locked and which are open.

## The read-back test

The interview ends when you can say the whole thing back in two plain sentences the
owner recognises as their own idea. Everyday words, one thought each, the mechanism
visible: who does what, and what happens next. If you cannot say it that way, you have
a gap, not a style problem.

**Passes:** "You want a box of bread offcuts at the market. People buy a box cheaper
than a loaf, feed it to the lake ducks, and you stop throwing good bread away."

**Fails:** "A B2C last-mile channel for surplus bakery SKUs, leveraging weekend foot
traffic to monetise existing waste streams." Every noun is a term the owner never
used, and none of it says who does what.

A correction, however small, is a gap: fold it, re-ask the touched area, read back
again. If the owner says "whatever you think", that is delegation, not confirmation;
put two concrete options and ask them to choose.

## Early exit

When the owner wants to stop before convergence: offer one last read-back, respect a
no, and write the draft with what you have. Every unanswered decision goes into the
spec's `## Assumptions and unresolved risks` with your recommended default beside it,
so the plan is never blocked on a question nobody asked. Every unknown fact goes to
the research questions. A visible hole is useful; a silently dropped question is a
trap. Say in the spec's assumptions that intake ended early.

## What this is not

Not the grill. The grill attacks a written spec with commands after it exists; this
interview builds the understanding the spec records. Not a transcript either: the draft
carries conclusions, not the conversation that reached them.
