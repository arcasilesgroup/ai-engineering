# Documentation writer — the framework's documentation discipline (spec 039 / B-039-1)

Loaded only when a document is being written (spec, plan, corpus, skill, ADR, page) —
never always-loaded (context economy, spec 033). It is the single source of the discipline;
a spec, plan, corpus or skill is read against it when authored and when reviewed. Two
halves: **writing for the agent** (writing-for-agents) and **writing in controlled
language** (ASD-STE100).

## Writing for the agent — the levers

1. **Context pointer** — a reference held in context that names out-of-context material and
   encodes the condition for reaching it. Its *wording*, not its target, decides when the
   agent reaches the material. A must-have target behind a weakly worded pointer is a
   variance bug: sharpen the wording first; inline the material only if sharpening fails.
2. **The two loads** — *context load* (always-loaded material, costs every turn) and
   *cognitive load* (what the human must remember exists; the price of human agency, not a
   cost to minimise). Material reached only through a pointer escapes context load at the
   price of the pointer's own line.
3. **Information hierarchy** — in-file step (what the agent does, in order) · in-file
   reference (consulted on demand) · disclosed reference behind a pointer. *Progressive
   disclosure*: what only some branches need goes behind a pointer; what every branch needs
   stays inline. *Co-location*: a concept's definition, rules and caveats under one heading.
4. **Completion criterion** — every step ends on a condition that is *checkable and
   exhaustive*. A vague bound ("understanding reached") invites premature completion:
   sharpen the bound first; hide later steps only across a real context boundary.
5. **Leading word** — a compact concept already living in the model's pretraining (lesson,
   fog of war, red) that the agent thinks with while running the document. Repeated as a
   token, never as a sentence; recruits priors for free. Hunt refactors: "fast,
   deterministic, low-overhead" → *tight*.
6. **Positive over negation** — prohibiting drags the forbidden behaviour into context and
   makes it *more* available. State the target behaviour ("write one-line comments"); a
   prohibition earns its place only as a hard guardrail, always paired with the positive.
7. **Pruning** — one source of truth per meaning (duplication costs maintenance and inflates
   prominence); the *environment* is a source of truth too (a document that restates
   `--help` is a cache, earning its load only when the lookup is expensive); every line
   must stay relevant (the default fate is sediment); hunt *no-ops* sentence by sentence —
   an instruction the model already obeys by default pays load to say nothing.

## Writing in controlled language — ASD-STE100

1. **One idea per sentence** — short, declarative sentences; a single statement each.
2. **One word, one meaning** — the approved vocabulary never changes meaning by context;
   do not invent synonyms.
3. **The verb leads** — the action lives in the verb, never hidden in a noun ("decide",
   not "make a decision").
4. **No ambiguity** — no pronouns with doubtful referents, no ellipsis; what is stated can
   be checked.

## The closing rule

A document that hands the agent a vague completion bound, or that restates what the
environment already says, is refused by the corpus route that names this reference. The
discipline is the single source; a later measured need may add a light prose check, never a
hard parser over user repositories.