---
name: explain
description: Use to get an engineer-grade explanation of code, architecture, a decision, or a skill — three depth tiers (brief, standard, deep) with ASCII diagrams for non-trivial structures and execution traces in deep mode. Trigger for "explain this", "walk me through", "why does this work", "trace this call".
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-explain

Engineer-grade explanations. Three depth tiers calibrated to how much
context the user already has. Outputs ASCII diagrams when the structure
isn't trivially obvious from text and walks execution traces in deep
mode.

## When to use

- "Explain this function / module / package"
- "Why does this work" / "what does this do"
- "Walk me through the call path"
- Onboarding after `/ai-guide tour` — drilling into a specific area
- Pre-review prep — understand the diff before judging it

## Depth tiers

### `brief` — 5 lines, one paragraph

For experienced engineers who need a refresher. Cover: purpose,
inputs, outputs, side effects, key invariant. No diagrams.

### `standard` (default) — 15-30 lines

For mid-level / new-to-this-area engineers. Adds: design rationale,
where it sits in the architecture, ASCII diagram for non-trivial
relationships, common gotchas. Default tier when the user does not
specify.

### `deep` — execution trace + diagrams + invariants

For deep-dive sessions, debugging hard problems, or pre-rewrite
analysis. Walks an actual execution trace through the system, names
every type / port / adapter touched, calls out where invariants are
checked, and surfaces edge cases the code does not handle.

## ASCII diagram convention

For a port + two adapters:

```
[Application] --> PolicyPort
                     |
       +-------------+-------------+
       v                           v
   [opa-adapter]            [stub-adapter]
   prod / regulated         dev / tests
```

Use only ASCII (no unicode box chars). Width ≤ 72 columns.

## Process

1. **Resolve target** — file, function, package, ADR id, or skill name.
2. **Resolve tier** — explicit (`brief|standard|deep`) or default to
   `standard`.
3. **Read source** — actual code first, then docs / ADR. Never
   paraphrase from memory.
4. **Render** at the chosen tier with diagrams when structure helps.
5. **Cite line ranges** — `path:Lstart-Lend` so the user can jump.
6. **Suggest follow-up skills** — `/ai-debug` if the user is chasing a
   bug, `/ai-test` if coverage gaps surface.

## Hard rules

- NEVER explain from memory — read the actual code.
- NEVER fabricate diagrams; if structure is trivial, skip the diagram.
- `deep` mode must trace one concrete execution path, not a generic
  "how it works".
- Cite line ranges for every claim; "I think it does X" is not allowed.
- ASCII only — no unicode box-drawing characters.

## Common mistakes

- Defaulting to `deep` when the user wanted a quick refresher
- Walls of prose where a diagram would be clearer
- Generic "this is a service that…" instead of tracing actual code
- Missing line citations — user has to hunt for the source
- Treating ADR explanations as marketing rather than tradeoff analysis
