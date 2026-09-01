# Plan: <task>

Depth: tree <N>   Mode: orchestrated
Budget note: <what a competent single pass would take; context, not arithmetic>

## Contract

Decided BEFORE fan-out. Everything a leaf could get wrong about its neighbors:

- Interfaces: <function signatures, file formats, API shapes>
- Data ownership: <which leaf owns which files; no two leaves share a file>
- Naming and conventions: <casing, folder layout, error handling style>

Coordination files are owned too: the driver owns this file and every branch
gates file; each leaf owns its deliverable files plus its own gates file.
Nothing else writes to them, which is what keeps the status log append-safe
while several leaves are in flight.

## Tree

Every leaf carries three dispatch fields. Keep `Owns` and `Needs` mechanical,
so the driver can compute the ready set instead of reasoning about it.

- `Owns:` the files this leaf may write. Two leaves may never list the same
  file; if they need to, the split is wrong.
- `Needs:` leaf ids that must be **verified** before this leaf starts, comma
  separated, or `--` for none. Ids only, never prose. This covers reads as
  well as writes: disjoint ownership keeps leaves from overwriting each other,
  but it does not stop a leaf's check from importing a file a sibling is
  halfway through editing. If a leaf's CHECK touches another leaf's files,
  even transitively, that leaf belongs in `Needs`.
- `Tier:` one word, the model that runs it (`haiku` / `sonnet` / `opus`).
  Ask model-router once while planning; see references/orchestration.md for
  the two constraints this skill adds.

```
- 1 <task>
  - 1.1 <branch> .......... gates/node-1.1.md
    - 1.1.1 <leaf> ........ gates/leaf-1.1.1.md
      Owns: src/foo/parse.ts, src/foo/types.ts
      Needs: --
      Tier: sonnet
    - 1.1.2 <leaf> ........ gates/leaf-1.1.2.md
      Owns: src/foo/render.ts
      Needs: 1.1.1
      Tier: haiku
  - 1.2 <branch> .......... gates/node-1.2.md
    - 1.2.1 <leaf> ........ gates/leaf-1.2.1.md
      Owns: src/bar/client.ts
      Needs: --
      Tier: opus
    - 1.2.2 <leaf> ........ gates/leaf-1.2.2.md
      Owns: tests/bar.test.ts
      Needs: 1.2.1
      Tier: haiku
```

## Dispatch schedule

Derived from the `Needs` fields above, written out once so the first fan-out
is obvious. It is a reading aid, not a barrier: a leaf is dispatched the
moment its own `Needs` are verified, not when its listed group finishes.

- Ready at once (`Needs: --`): 1.1.1, 1.2.1
- Unblocked by 1.1.1: 1.1.2
- Unblocked by 1.2.1: 1.2.2
- Branch gates: node-1.1 after 1.1.1 + 1.1.2; node-1.2 after 1.2.1 + 1.2.2
- Root gates: after every branch

If this list has one long chain and nothing parallel, the split is following
your writing order rather than the task's joints. Re-cut it.

## Status log

Append-only. One line per event: leaf dispatched, leaf verified, leaf sent
back, gate abandoned. Never rewrite lines above; appending keeps the file
cheap to re-read and diff, and keeps concurrent dispatch from clobbering it.

- <timestamp or step> plan written, contract fixed
