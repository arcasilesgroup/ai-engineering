---
name: migrate
description: Use for cross-framework or cross-version migrations — Express → Fastify, Vue 2 → Vue 3, breaking dependency updates, language major bumps. Generates a phased migration plan (compat layer → swap → deprecate) with --dry-run support. Trigger for "migrate from X to Y", "upgrade major version", "swap library", "this needs a deprecation path".
effort: high
tier: core
capabilities: [tool_use, structured_output]
---

# /ai-migrate

Cross-framework / cross-version migration planner and executor. Reads a
spec describing the source and target, walks the codebase to enumerate
every call site, and generates a phased plan with explicit rollback at
each step.

> Pairs with `/ai-specify`. The migration spec must exist before
> `/ai-migrate` plans the work; rationale, scope, and non-goals come
> from the spec, not from the skill.

## When to use

- "Migrate Express → Fastify" / "Vue 2 → Vue 3"
- Major version bump with breaking changes (e.g. React 17 → 19,
  Python 3.10 → 3.13)
- Swap a library (e.g. `requests` → `httpx`, `enzyme` → `testing-library`)
- Database engine swap (Mongo → Postgres) — coordinate with `/ai-data`
- Deprecating a public API surface

## Phase model (always 3+)

### Phase A — Compatibility layer

1. Introduce a thin abstraction (port) that both source and target can
   implement.
2. All new code goes through the port; existing code untouched.
3. Coverage gate: 100% on the port.

### Phase B — Swap

1. Migrate call sites in batches, smallest first.
2. Each batch is a separate commit + PR — bisectable.
3. Tests run against both implementations during the swap.
4. Feature flags allow runtime fallback if the new path regresses.

### Phase C — Deprecate

1. Remove the source implementation.
2. Remove the compat layer if it has no other consumers.
3. Update docs, CHANGELOG, migration guide.
4. Bump major version per semver.

## Process

1. **Read migration spec** — refuse if `state != approved`.
2. **Enumerate call sites** — grep / AST walk for every reference to
   the source API. Persist to `.ai-engineering/specs/spec-NNN/migration-plan.md`.
3. **Bucket call sites** by complexity (low / medium / high) and
   coverage (covered / partial / uncovered).
4. **Plan phases** — A / B / C with explicit task ids, each pairing
   RED + GREEN per `/ai-test`.
5. **`--dry-run` mode** — render the plan without modifying files.
6. **Execute phase A first**; require user approval to proceed to B.
7. **Phase B per-batch commits** — each batch must keep tests green.
8. **Phase C only after** all call sites swapped + soak window passed.
9. **Emit telemetry** — `migrate.phase_started`, `migrate.batch_completed`,
   `migrate.deprecated`.

## Rollback

Every batch must have a documented rollback (revert + feature flag flip).
If a batch regresses production, rollback is the default response while
debugging.

## Hard rules

- NEVER skip the compat layer phase — direct swaps are unbisectable.
- NEVER batch call sites larger than what fits in one reviewable PR.
- NEVER deprecate (Phase C) without a soak window of ≥ 2 weeks in
  staging or production behind a feature flag.
- A migration spec is mandatory; this skill refuses to plan otherwise.
- Every batch carries a documented rollback.

## Common mistakes

- Big-bang swap with no compat layer — bisect impossible when it breaks
- Mixing migration with feature work in the same batch
- Forgetting the migration guide in `/ai-docs` — downstream consumers
  break silently
- Treating Phase C as "done", missing CHANGELOG and docs sync
- Skipping the dry-run on first plan — users surprised by scope
- Deprecating before the soak window catches a regression
