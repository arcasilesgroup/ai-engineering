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

## F1 · MAJOR · resolved
**Where:** src/commands/config.ts:263 (splice at :225)
**Critic (r1):** On a CRLF file, `enabled = ["claude-code"]\r\n` becomes `enabled = ["claude-code", "cursor"]\n`: the line's `\r` is dropped, leaving mixed line endings, while the same line with a trailing comment keeps its `\r` inside the comment. A line terminator is an unrelated byte, and doctor already branches on win32, so CRLF checkouts are realistic. → Split a trailing `\r` off each scanned line and re-append it to the replacement; add CRLF cases with and without a trailing comment that assert exact bytes.
**Fixer (r1):** fixed — the edit no longer splits and rejoins lines: it splices only the bytes of the changed items in the raw text (`withListItems`, src/commands/config.ts:289), so every existing `\r` stays; a new item line copies the ending of the line it follows (`appendItems`, :367) and a new key or table uses the file's own ending (`withSurfacesEnabled`, :236). Regression `a CRLF config with %s keeps its line endings` (tests/config-command.spec.ts:684: one-line, one-line + comment, multi-line; exact bytes on --add and --remove) fails on the old source · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓
**Critic (r2):** resolved — re-read `withListItems`/`appendItems` at 569e2123: only item bytes are spliced, a new line copies the preceding line's ending. The CRLF regressions (:684, one-line, commented and multi-line, add then remove, exact bytes) pass at 569e2123 and fail at 60e0eeb9. Probes with CRLF + tabs (add and remove) kept every `\r`.

## F2 · MAJOR · resolved
**Where:** src/commands/config.ts:218
**Critic (r1):** `[surfaces] # gate\r\nenabled = ["claude-code"]\r\n` is a valid table with a commented header, but `#.*` stops at `\r` and `$` has no `m` flag, so the header is not found, the appended second table fails the parse check, and `--add` exits 2 refusing a valid file. Acceptance 3 says a commented header is recognised and the table updated in place. → Match against the line without its trailing `\r` (or use `[^\n]*`); add a CRLF commented-header case asserting exit 0 and exact bytes.
**Fixer (r1):** fixed — `locateEnabled` (src/commands/config.ts:254) matches each line without its trailing `\r` against `SURFACES_HEADER` (:249) and computes offsets from the raw text. Regression tests/config-command.spec.ts:694 (`[surfaces] # gate\r\n…`, exit 0, exact bytes) fails on the old source with exit 2 · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓
**Critic (r2):** resolved — `locateEnabled` strips `\r` before `SURFACES_HEADER`; the CRLF commented-header test passes at 569e2123 and fails at 60e0eeb9 with exit 2.

## F3 · MAJOR · resolved
**Where:** src/commands/config.ts:225, :263; tests/config-command.spec.ts:640
**Critic (r1):** For a multi-line list, only the comment after the closing `]` survives. `enabled = [ # hosts\n  "claude-code", # main\n  # cursor later\n] # end` becomes `enabled = ["claude-code", "cursor"] # end`: three user comments are lost on an `--add` that removes nothing, including the comment on the `enabled` line itself, the very case this checkpoint fixed for one-line lists. The test at :640 pins the loss of `# the main one`, contradicting "preserves comments". → Either edit a multi-line array element-wise (insert the new item before `]` with the existing indentation, delete only a removed item's line), or refuse with exit 2 and a byte-identical file when the value span holds a comment not on its closing line; rewrite test :640 to assert the chosen behavior with exact bytes.
**Fixer (r1):** fixed — the list is edited item by item (`withListItems`, src/commands/config.ts:289): additions go after the last item in its style (own line: same indentation, quote, trailing comma and line ending, one per line; inline: `, "id"`), and a removal deletes only that item's line when it has one, else the item and one adjacent comma (`withoutItem`, :386). An empty multi-line list, nested arrays and multi-line strings return null and are refused at exit 2 byte-identical. The parse-and-compare guard (:112) stays and now also checks the order: kept items in place, new ones after. Test :649 now asserts the comment is kept with exact bytes; new regressions :661 (critic's layout, add then remove, exact bytes) and :672 (no-trailing-comma style) fail on the old source · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓
**Critic (r2):** resolved — the opening-line comment, the comments between items and the one after `]` survive add and remove (tests :649/:661/:672 exact bytes, failing at 60e0eeb9). Probes: removing the first or last item, a no-trailing-comma list, comma-first style, a `# see ]` comment, single quotes, duplicates (all copies removed, order kept) and an unknown id all came out as expected. Nested arrays, numbers, multi-line strings, an empty multi-line list, quoted and dotted keys are refused at exit 2 with the file byte-identical.

## F4 · MINOR · resolved
**Where:** src/commands/config.ts:225; tests/config-command.spec.ts:574
**Critic (r1):** The replacement line is rebuilt as `enabled = …`, so the key's indentation and the spacing around `=` are normalised: `\tenabled\t=\t[…]` → `enabled = […]`, `  enabled = …` → `enabled = …`. The test at :574 only uses `toContain`, so it cannot see this. → Keep the original prefix through the whitespace after `=` and assert exact bytes in :574.
**Fixer (r1):** fixed — the key line is never rebuilt: only the bytes inside `[…]` change, so indentation and spacing around `=` are left alone. :574 now asserts exact bytes; regression :584 (`\tenabled\t=\t[…]`, --add then --remove) fails on the old source · verify: fresh clone at 60e0eeb9 + overlay, `bun test tests/config-command.spec.ts tests/doctor-command.spec.ts tests/init-command.spec.ts` 136 pass / 0 fail, `bun run typecheck` ✓, `bun run lint` ✓, full `bun test` 1664 pass / 0 fail ✓
**Critic (r2):** resolved — the key line is never rebuilt; :574 now asserts exact bytes and the tab-layout regression passes at 569e2123 and fails at 60e0eeb9.

## Round 2 evidence
- Fresh clone at 569e2123 (`bun install --frozen-lockfile`, default TMPDIR): config 53 pass / 0 fail, doctor 40 pass / 0 fail; `bun run build`, typecheck and lint green (warnings only in untouched files). With `src/commands/config.ts` reverted to 60e0eeb9 the new spec fails 8 cases, the F1–F4 regressions. Scratch probes deleted; clone removed.

## F5 · MINOR · open
**Where:** src/commands/config.ts:386 (`withoutItem`)
**Critic (r2):** Removing the last item of a one-per-line list leaves `enabled = [\n]`, and the next `--add` refuses that layout at exit 2 (`appendItems`, :367): the command writes a file it then cannot edit. → When the removal empties a multi-line list, collapse it to `[]` on the key line, or let `appendItems` fill a whitespace-and-newline-only list; add an exact-bytes remove-all-then-add test.

## F6 · MINOR · open
**Where:** src/commands/config.ts:386 (`withoutItem`, inline branch)
**Critic (r2):** When the last item shares its line with `]`, removing it leaves the indentation in front of the bracket: `[\n  "claude-code",\n  "cursor"]` → `[\n  "claude-code",\n  ]`. The result is valid but a stray indent appears. → When the removed item's line holds nothing else but `]`, also drop the leading whitespace; pin it with an exact-bytes test.

## F7 · MINOR · open
**Where:** tests/config-command.spec.ts:716 (refusal table)
**Critic (r2):** The new `null` branches (nested array, non-string item, multi-line string, empty multi-line list) are refused byte-identical only per my probes; no test pins them. → Add those layouts to the existing "refused and left byte-identical" table.

VERDICT: PASS — open F5, F6, F7 (MINOR)