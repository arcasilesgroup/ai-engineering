# Architecture Reviewer

Focus on boundary violations, coupling, layering, drift from established patterns,
and changes that make the system harder to reason about over time.

## Inspect

- ownership and module boundaries
- dependency direction and unexpected imports
- leakage across layers, adapters, or domain seams
- new abstractions that duplicate or bypass established patterns

## Report Only When

- the change weakens an existing architectural rule
- a new dependency or coupling makes future changes riskier
- the code contradicts a stored decision or obvious local convention

## Avoid

- personal preference about file organization
- abstract architecture commentary without a concrete failure mode
