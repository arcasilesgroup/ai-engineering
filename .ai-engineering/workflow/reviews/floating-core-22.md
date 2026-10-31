# Adversarial review — floating-core#22 Check Every Skill and Preserve Settings

## Goal
Doctor verifies every installed skill regardless of legacy settings, while config edits change only the requested setting and preserve unrelated bytes.

## Acceptance
- Doctor verifies the complete skill inventory independently of legacy `[canon].packs` values.
- Config changes only the requested surface setting and preserves comments, legacy pack values and all unrelated bytes.
- Commented TOML table headers are recognised so a valid `[surfaces]` table is updated in place, not duplicated.

## changed_files
- src/commands/config.ts
- src/commands/doctor.ts
- tests/config-command.spec.ts
- tests/doctor-command.spec.ts

Commits: cfa537c9 (tests), d4befb6e (implementation). Reviewed at HEAD 60e0eeb9.

## verify
- bun test tests/config-command.spec.ts
- bun test tests/doctor-command.spec.ts
- bun run build

## Round 1 evidence
- Fresh clone at 60e0eeb9 (`bun install --frozen-lockfile`, default TMPDIR): config 46 pass / 0 fail, doctor 40 pass / 0 fail; `bun run build` compiled `dist/ai-eng`. Clone removed.
- Doctor: `src/` has no `packs` reference; `canonDrift` (`src/embed.ts:294`) walks all of `canonSkills()`. The new doctor cases delete a skill outside a partial pack list and assert the exact `n-1/n · 1 missing` row — behavior, not a proxy. No finding.
- Probes run through `configMain` with `--add cursor` in the clone (scratch spec deleted): `#` inside a quoted name, a comment holding a quote, literal strings, `[] # c`, tabs before a comment and a header with a trailing tab all keep the comment and parse. Failures are F1–F4.

## F1 · MAJOR · fixed
**Where:** src/commands/config.ts:263 (splice at :225)
**Critic (r1):** On a CRLF file, `enabled = ["claude-code"]\r\n` becomes `enabled = ["claude-code", "cursor"]\n`: the line's `\r` is dropped, leaving mixed line endings, while the same line with a trailing comment keeps its `\r` inside the comment. A line terminator is an unrelated byte, and doctor already branches on win32, so CRLF checkouts are realistic. → Split a trailing `\r` off each scanned line and re-append it to the replacement; add CRLF cases with and without a trailing comment that assert exact bytes.
**Fixer (r1):** fixed — the edit no longer splits and rejoins lines: it splices only the bytes of the changed items in the raw text (`withListItems`, src/commands/config.ts:289), so every existing `\r` stays; a new item line copies the ending of the line it follows (`appendItems`, :367) and a new key or table uses the file's own ending (`withSurfacesEnabled`, :236). Regression `a CRLF config with %s keeps its line endings` (tests/config-command.spec.ts:684: one-line, one-line + comment, multi-line; exact bytes on --add and --remove) fails on the old source · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓

## F2 · MAJOR · fixed
**Where:** src/commands/config.ts:218
**Critic (r1):** `[surfaces] # gate\r\nenabled = ["claude-code"]\r\n` is a valid table with a commented header, but `#.*` stops at `\r` and `$` has no `m` flag, so the header is not found, the appended second table fails the parse check, and `--add` exits 2 refusing a valid file. Acceptance 3 says a commented header is recognised and the table updated in place. → Match against the line without its trailing `\r` (or use `[^\n]*`); add a CRLF commented-header case asserting exit 0 and exact bytes.
**Fixer (r1):** fixed — `locateEnabled` (src/commands/config.ts:254) matches each line without its trailing `\r` against `SURFACES_HEADER` (:249) and computes offsets from the raw text. Regression tests/config-command.spec.ts:694 (`[surfaces] # gate\r\n…`, exit 0, exact bytes) fails on the old source with exit 2 · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓

## F3 · MAJOR · fixed
**Where:** src/commands/config.ts:225, :263; tests/config-command.spec.ts:640
**Critic (r1):** For a multi-line list, only the comment after the closing `]` survives. `enabled = [ # hosts\n  "claude-code", # main\n  # cursor later\n] # end` becomes `enabled = ["claude-code", "cursor"] # end`: three user comments are lost on an `--add` that removes nothing, including the comment on the `enabled` line itself, the very case this checkpoint fixed for one-line lists. The test at :640 pins the loss of `# the main one`, contradicting "preserves comments". → Either edit a multi-line array element-wise (insert the new item before `]` with the existing indentation, delete only a removed item's line), or refuse with exit 2 and a byte-identical file when the value span holds a comment not on its closing line; rewrite test :640 to assert the chosen behavior with exact bytes.
**Fixer (r1):** fixed — the list is edited item by item (`withListItems`, src/commands/config.ts:289): additions go after the last item in its style (own line: same indentation, quote, trailing comma and line ending, one per line; inline: `, "id"`), and a removal deletes only that item's line when it has one, else the item and one adjacent comma (`withoutItem`, :386). An empty multi-line list, nested arrays and multi-line strings return null and are refused at exit 2 byte-identical. The parse-and-compare guard (:112) stays and now also checks the order: kept items in place, new ones after. Test :649 now asserts the comment is kept with exact bytes; new regressions :661 (critic's layout, add then remove, exact bytes) and :672 (no-trailing-comma style) fail on the old source · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓

## F4 · MINOR · fixed
**Where:** src/commands/config.ts:225; tests/config-command.spec.ts:574
**Critic (r1):** The replacement line is rebuilt as `enabled = …`, so the key's indentation and the spacing around `=` are normalised: `\tenabled\t=\t[…]` → `enabled = […]`, `  enabled = …` → `enabled = …`. The test at :574 only uses `toContain`, so it cannot see this. → Keep the original prefix through the whitespace after `=` and assert exact bytes in :574.
**Fixer (r1):** fixed — the key line is never rebuilt: only the bytes inside `[…]` change, so indentation and spacing around `=` are left alone. :574 now asserts exact bytes; regression :584 (`\tenabled\t=\t[…]`, --add then --remove) fails on the old source · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓

VERDICT: FAIL — open F1, F2, F3 (MAJOR); F4 (MINOR)
