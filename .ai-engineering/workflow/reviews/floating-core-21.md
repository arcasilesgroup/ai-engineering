# Adversarial review — floating-core#21 Honor Legacy Settings During Updates

## Goal
Update installs every skill for legacy pack settings without changing config bytes, repairs missing payloads, and preserves locally edited or user-owned files.

## Acceptance
- Update installs the complete inventory for absent, empty, partial and other legacy `[canon].packs` values without changing config bytes.
- Update repairs missing shipped payloads while preserving byte-different installed skills and unrelated user-owned skill directories.
- Init-recovery restores its edited skill fixture before asserting zero drift on a clean update.
- The `[canon].packs` test helper recognises every TOML layout; README states precisely which commands keep config bytes.

## changed_files
- README.md
- tests/update-command.spec.ts
- tests/adversarial/init-recovery.test.ts
- tests/carriers-install.spec.ts
- tests/init-command.spec.ts

Commits: bd1f9234 (tests), b64a70cc (implementation). Reviewed at HEAD 34811050.

## verify
- bun test tests/update-command.spec.ts
- bun test ./tests/adversarial/init-recovery.test.ts
- bun test tests/carriers-install.spec.ts
- bun test tests/init-command.spec.ts
- bun run build

## Round 1 evidence
- Verify run in a fresh clone at 34811050 (`bun install --frozen-lockfile`, default TMPDIR): update 31, init-recovery 13, carriers-install 62, init 43 pass / 0 fail; `bun run build` compiled `dist/ai-eng`. Clone removed.
- `src/` has no `packs` reference; `src/commands/update.ts:144` drops `.ai-engineering/config.toml` from the plan. Doctor imports no writer that reaches config.toml.
- Probe (CLI subprocess, isolated `AI_ENG_HOME`) against five valid layouts carrying `[canon].packs = ["triage"]`: `doctor`, `update --yes` and `init --yes` left every file byte-identical. `config --add codex` kept the standard layout parseable, but left the multiline `enabled` array, the `surfaces.enabled` dotted key, the `surfaces = { enabled = … }` inline table and the `[ surfaces ]` header unparseable (orphaned array lines, or a duplicate `[surfaces]` table).
- Tests compare the real config file's bytes and mtime, check every installed skill byte-for-byte against `skills/`, and restore the init-recovery fixture in `finally` before the clean zero-drift update and doctor check. Acceptance items 1–3 are proven.

## F1 · MAJOR · resolved
**Where:** README.md:302-305; src/commands/config.ts:188-204
**Critic (r1):** The new README sentence, which acceptance item 4 requires to be exact, says `ai-eng config` and the init "config" hand-off "rewrite only the `enabled` key under `[surfaces]` (adding that table when it is missing) and leave every other section … as you wrote it". `withSurfacesEnabled` edits text line by line, so the claim is false for valid TOML. With a multiline `enabled = [` array it replaces only the first line and leaves `"claude-code",\n]` behind. With `surfaces.enabled = …`, `surfaces = { enabled = … }` or `[ surfaces ]` it appends a second `[surfaces]` table. In all four cases config.toml no longer parses, so the repo stops being governed and later commands refuse. This repeats L209/L210 (docs disagree with behaviour, R25). → Fail closed in `writeConfigSurfaces`: parse the rewritten text with `Bun.TOML.parse` and check that it differs from the parsed original only in `surfaces.enabled` and that `surfaces.enabled` equals the new list. Otherwise write nothing and tell the person to edit `[surfaces].enabled` by hand. Add `tests/config-command.spec.ts` cases for the four layouts asserting unchanged bytes and the refusal message. If you choose not to change `src/commands/config.ts`, narrow the README claim to the single-line `[surfaces]` / `enabled = [...]` layout and state that other layouts are refused or unsupported.

**Fixer (r1):** fixed — `writeConfigSurfaces` (src/commands/config.ts:88) now judges the candidate by meaning: `isOnlySurfacesChange` (config.ts:111) parses original and result with `Bun.TOML.parse` and allows the write only when the result equals the original with `surfaces.enabled` set to the new list; otherwise it writes nothing, prints a refusal naming `.ai-engineering/config.toml` plus "Edit it by hand: under [surfaces], set enabled = […]", and `configMain` exits 2. Carrier removal moved after the successful write (config.ts:159), so a refused `--remove`/picker untick deletes nothing. The line edit now accepts `[ surfaces ]` (config.ts:218) and replaces a multi-line `enabled` array whole (`arrayEndLine`, config.ts:224/238); dotted and inline layouts are refused byte-identical. Re-init "config" calls `configMain`, so it shares the guard. README.md:305-307 states the refusal. Tests: tests/config-command.spec.ts:593-639 (multi-line and `[ surfaces ]` update; dotted and inline refuse byte-identical; refused `--remove` keeps the carrier) — all 5 fail on 34811050 · verify: bun test tests/config-command.spec.ts tests/init-command.spec.ts tests/update-command.spec.ts ✓ 110/0; bun run typecheck ✓; bun run lint ✓; bun test ✓ 1642/0

**Critic (r2):** resolved. I checked it myself in a fresh clone at 28ad73b9. Verify passed: config-command 36, update 31, init-recovery 13, carriers-install 62, init 43, 0 fail; build, typecheck and lint passed. I ran `config --add cursor` and `config --remove claude-code` against twelve more valid layouts: CRLF, a quoted `"enabled"` key, a trailing comment, brackets inside comments, a nested array before `enabled`, a `[surfaces]` line inside a multi-line string, `[surfaces.extra]` before `[surfaces]`, `[canon]` first, a multi-line literal string holding `]`, `[[surfaces.extra]]`, no final newline, and indented keys. Every run either produced parseable TOML with only `surfaces.enabled` changed and every other key kept, or refused with exit 2, the file unchanged and no new `.cursor` carrier. `configMain` removes carriers only after `writeConfigSurfaces` returns true, and the picker path now uses the same deferred `removing` list. The README matches this behaviour.

## F2 · MINOR · resolved
**Where:** README.md:300-305 (writer at src/commands/adapt.ts:108)
**Critic (r1):** The README sets out which commands keep config bytes and which rewrite part of the file, but leaves out `ai-eng adapt apply`. That command rewrites `.ai-engineering/config.toml` wholesale from an approved proposal, `[canon]` included. A reader may take the two named rewriters as the complete list. → Add one clause: `ai-eng adapt apply` replaces config.toml with the proposal you approved.

**Fixer (r1):** fixed — README.md:308-309 adds: `ai-eng adapt apply` replaces the whole of `.ai-engineering/config.toml`, `[canon]` included, with the text in the approved proposal when that proposal carries the file (matches src/commands/adapt.ts:94-108: only ALLOWED paths present in the payload are written whole) · verify: bun test ✓ 1642/0

**Critic (r2):** resolved. README.md:308-309 matches src/commands/adapt.ts:94-108: only the allowed paths present in the approved payload are written, each replaced whole.

## Round 1 verdict
VERDICT: FAIL
MAJOR    README.md:302 — README says `ai-eng config` rewrites only `[surfaces].enabled`, but `withSurfacesEnabled` (src/commands/config.ts:188) leaves multiline, dotted, inline and spaced-header layouts unparseable → fail closed on any rewrite that changes more than `surfaces.enabled` and test the four layouts, or narrow the README claim
MINOR    README.md:300 — `ai-eng adapt apply` also rewrites config.toml but is not named → add it to the README sentence
ROUND 1: resolved 0 · withdrawn 0 · upheld 0 · new 2

## Round 2 verdict
VERDICT: PASS
ROUND 2: resolved 2 · withdrawn 0 · upheld 0 · new 0