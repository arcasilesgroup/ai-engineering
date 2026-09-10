---
"ai-engineering": patch
---

fix(chain): overrides.toml now loads — the only guard-off switch had never worked

`readOverrides` looked up the literal TOML key `guard.off`, but `[[guard.off]]`
parses as `{ guard: { off: [...] } }`: a dotted key nests, and the literal never
exists. Every file returned an empty list, so §09.1's sole mechanism for turning a
guard off was inert — a written exception with a reason and an end date changed
nothing, and the guard kept denying.

Doctor now also dates what it reads: an override renders as `expires in 3d`, an
entry with no `until` is named as never-expiring, and an entry whose date has
passed is reported with the removal it needs, so dead config stops hiding behind
`none active`.

`doctor` now answers the question existence cannot: for every surface that runs the
guard in-process, the planted `ai-eng-chain.ts` is compared byte for byte against
the chain this binary ships. A stale or hand-patched bundle reports `is NOT the
chain this binary ships → ai-eng update` instead of passing as present.

`ai-eng <typo>` no longer answers with a bare `unknown verb`: the nearest verb is
named, or the help line that follows it (§14.5b).
