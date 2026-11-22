# Review brand-design-system checkpoint 2

Goal: installCanon writes every templates/*.html.tpl into the machine home templates directory on every OS through the one guarded helper, records them as ai-eng's, sweeps a template the binary stops shipping, keeps a file of the user's, and uninstall removes them, so the skills' ../../templates/ links resolve outside this repository.

Acceptance:
- After installCanon, the home templates directory holds exactly the shipped *.html.tpl files, byte for byte, and the ownership record names each one.
- A recorded template the binary no longer ships is swept; an unrecorded file of the user's in the same folder keeps its bytes.
- A link or non-folder at the home templates path is refused with a named warning, and skills, agents and the ownership record are still written.
- Uninstall removes the installed templates and leaves the user's own file.

changed_files:
- src/embed.ts
- src/surfaces/canon-install.ts
- src/commands/uninstall.ts
- FILEMAP.md
- docs/global-carriers.md
- .changeset/brand-design-system.md
- tests/embed-canon.spec.ts
- tests/carriers-install.spec.ts

verify:
- mkdir -p /private/tmp/t-runs && TMPDIR=/private/tmp/t-runs bun test tests/carriers-install.spec.ts tests/embed-canon.spec.ts tests/uninstall-command.spec.ts tests/update-command.spec.ts tests/generated-payload.test.ts
- bun test tests/arch.spec.ts
- bun run typecheck
- bun run lint

## F1 · BLOCKER · open
**Where:** src/embed.ts:399
**Critic (r1):** `canonDrift` still measures only `canonSkills()`. `init`, `update` and `doctor` all treat drift 0 / missing 0 / stale 0 as a healthy canon and skip `installCanon` (`src/commands/init.ts:160`, `src/commands/update.ts:91` and `:140`, `src/commands/doctor.ts:89`). This branch does not change `skills/` against main, so an already-installed machine stays "intact" and `~/.ai-engineering/templates/` is never created. A deleted or edited page template is invisible the same way: update will not rewrite it, which breaks R28 (install, update and uninstall converge a path ai-eng ships) and repeats the failure this function's own comment describes — a canon reading intact while files are missing. The new tests call `installCanon` directly, so they stay green. → Count every `templates/*.html.tpl` from `pageTemplates()` in the same missing / drift / verified loop as skills, and add a test where skills already match, one shipped template is absent or edited, `canonDrift` is unhealthy, and `update` / `init` actually writes the shipped bytes.

## F2 · BLOCKER · open
**Where:** src/commands/uninstall.ts:337
**Critic (r1):** `recordedMachinePaths` (`src/embed.ts:243`) unions every current `machinePayload()` key with the ownership record, and uninstall deletes that set. A shipped name such as `templates/research.html.tpl` is removed even when the record does not name it and the bytes are not ai-eng's. R28 says a file ai-eng never wrote, whose bytes differ, is the user's and uninstall must leave it; the comment this change put on `removeMachinePayload` (`src/commands/uninstall.ts:326`) and `docs/global-carriers.md:79` say the same. U18 only plants `mine.html`, so a colliding unrecorded page is untested. Skill folders are a different rule (the folder is ai-eng's whole) and must stay on the payload union. → For `templates/` keys, delete only a path the ownership record names, or a regular file whose bytes equal the shipped template. An unrecorded file with different bytes stays. Prove it: after install, drop `templates/research.html.tpl` from the record, write different bytes, uninstall, and assert those bytes survive; a byte-identical unrecorded copy is still removed.

## F3 · MAJOR · open
**Where:** src/embed.ts:262
**Critic (r1):** `recordCanonOwnership` stamps every `machinePayload()` path with the embedded hash, including every page template, whether or not `materializeTemplates` wrote it. A link or a non-folder at `templates/` is refused (`src/surfaces/canon-install.ts:85`) and then still recorded. That changes the ownership class of a file this run did not write (R39, L242). After the user replaces the link with a real directory, uninstall or a later binary that stops shipping that name will treat their page as ai-eng's and delete it. U16 checks that skills, one agent and the record file exist; it never asserts the refused templates are absent from `files`. → Add a `templates/` key only when `safeProjectPath` reaches a regular file whose hash equals the embedded file. Do not keep an older `templates/` key that is present only through a link or a non-directory. Prove it with the U16 symlink and file fixtures: the record contains no `templates/` key, and the target bytes are unchanged.
