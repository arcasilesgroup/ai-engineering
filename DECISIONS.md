# DECISIONS.md — ADR-lite: ≤6 lines per decision [Problem → Decision → Reason]

## D-001 · ai-engineering governs this repo (2026-09-01)
**Problem:** agents need common ground: guards, git floor, executable contract.
**Decision:** planted {ai} Engineering 2.0.0 (init), global skill canon, local receipts.
**Reason:** proof > promise — a decision that always comes out the same is code, not a prompt.

## D-002 · §14 mockups are the CLI visual contract (2026-09-01)
**Problem:** the human verbs (init/doctor/update/upgrade/config/uninstall) drifted from the blueprint: raw stdout breaks the clack frame mid-flow (user: "feo feo feo").
**Decision:** blueprint §14 mockups are the acceptance standard; src/ui.ts is the single frame layer over clack 1.7.0 (no new deps); machine verbs keep byte-stable stdout. Research: .ai-engineering/brainstorm.md @ git b3d70782.
**Reason:** the manual already decided the UX line by line; the gap was implementation depth, not design.

## D-003 · the floor's real location is protected, and the payload keeps fixture data (2026-09-10)
**Problem:** audit: the `.git/hooks/` shims had drifted and were absent from the lock (so `update` treated them as the user's forever), `git-hooks/` was a dead v1 layout, `.claude/reviews/` entered git through an `update` sweep carrying machine paths, `.chain-bundle` was materialized into every canon and mirror, a session could disarm the floor by writing `.git/hooks/*` (relative-path tokens evaded self-protect entirely), and the binary dropped ai-verify's fixture `.ts/.tsx`, leaving its own eval pack citing files that never shipped.
**Decision:** reinstall the shims from the shipped templates and re-record them; delete `git-hooks/`; untrack and gitignore `.claude/reviews/`; `canonSkills()` in src/embed.ts is the single predicate for canon membership (bundle excluded, fixtures included); fixture data travels as generated `.txt` copies under `scripts/.embed/`; self-protect protects `<repo>/.git/hooks` and canonicalizes relative path tokens before judging; `update --yes` actually receives `--yes`.
**Reason:** a guard the governed session can edit, or a canon that counts a build artifact as a skill, is theater — and an eval pack that cites files the binary never carried was already broken for every binary install.

## D-004 · the over-engineering audit applied (2026-09-10)
**Problem:** a repo-wide ponytail audit found a hand-rolled TOML parser the runtime ships, 13 exports nothing referenced, a dead frontmatter linter, install's symlink mode, 3 of the 4 denial protocols unreachable, the adapter-alias layer with no producer, `spec run`'s built-in CHECK extractor, a `VerdictCache` class with one consumer, unread `surfaces.json` fields, hooks wired for events the chain table has no rows for, and tests that asserted their own fixtures.
**Decision:** all applied. `Bun.TOML` replaces `src/toml.ts` (parse+stringify parity verified against this repo's own config, lock and overrides, and inside a compiled binary); `ai-eng config` rewrites the single `enabled =` line in place, so the template's comments survive the command; `scripts/proof-cli-ux.sh` is wired into CI instead of deleted; the ai-verify eval pack stays — its review step is a fresh session, not a CI job.
**Reason:** the payload is what a foreign repo executes, so every unreachable branch there is weight every audit has to carry again — and a test that reads back a fixture it wrote proves nothing.

## D-005 · one build entry point, and it sweeps Bun's scratch (2026-09-10)
**Problem:** `bun build --compile` leaves its 61 884 464-byte scratch executable (`.{hash}-{n}.bun-build`) in the cwd on every *successful* compile — not only on an interrupt (measured on Bun 1.4.2, four consecutive builds, all four left one) — and `.gitignore` hides it, so builds accumulated ~59 MB per run invisibly.
**Decision:** `scripts/build.ts` is the single build path (`bun run build`; release.yml's duplicate `|| bun build …` fallback is gone): it sweeps `.bun-build` in the cwd and `dist/`, before and after the compile, prints what it removed, and forwards `--target` to Bun.
**Reason:** a build artefact the build tool never deletes is 59 MB nobody sees; sweeping in the one place every build goes through costs a few lines and cannot be forgotten — and one build path means a failed build fails the job instead of silently retrying itself.
