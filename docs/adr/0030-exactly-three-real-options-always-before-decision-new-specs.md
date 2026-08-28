---
schema: "urn:ai-engineering:madr:1"
schema_version: "1"
type: "adr"
id: "0030"
title: "Exactly three real options, always, before Decision; new specs only, history frozen; critics revise them in place; a decision earns a MADR only when it constrains future specs."
date: "2026-08-28"
spec: "045"
status: "proposed"
supersedes: ""
---

# 0030. Exactly three real options, always, before Decision; new specs only, history frozen; critics revise them in place; a decision earns a MADR only when it constrains future specs.

## Context and problem statement

`ai-spec` and its template demanded "at least two real options". Two is the minimum
that makes a comparison, and every real decision in this tree that mattered carried
three — the third being the honest baseline (defer, do nothing, keep as is) that two
option lists quietly omit. The owner's directive for spec 045 named it as a rule:
always three, so the shape of the comparison stops being one more thing each author
re-decides.

## Considered options

1. **Exactly three real options, always, before `## Decision`** — bound by the
   template, pinned by the skill text and its contract literals; new specs only,
   the nine historical exceptions stay frozen.
2. **Keep "at least two"**: the floor holds, the theatre of padding a two-option
   list to three never happens because authors who have two stop there.
3. **Move the section after the critics**: alternatives weighed with grill and
   council input in front of them.

## Decision outcome

Chosen option: **1**, with option 3 refused: a decision with no alternatives in
front of it is not auditable, and the critics' effect lands by revising the options
in place — `## Grill` and `## Council` record what moved. Option 2 loses because the
third option (the honest baseline) is the one two-item lists omit, and its absence is
exactly the weak-option theatre rule 10 kills in writing.

## Consequences

Better: every new spec carries the deferral answer explicitly or names why it loses;
the rule is one scaffold decision, enforced by the template and pinned in prose.
Worse: a spec with genuinely two options must find an honest third — the template
says the baseline is allowed to be it, and then it must be killed in writing; and
the corpus is now two regimes (36 conforming, nine frozen exceptions on the
readiness list).
