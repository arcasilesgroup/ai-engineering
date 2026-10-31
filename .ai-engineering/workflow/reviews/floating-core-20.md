# Adversarial review — floating-core#20 Install Every Skill During Init

## Goal
A fresh init installs every skill and resource by default, writes no legacy pack selection, and never executes installed skill content.

## Acceptance
- A fresh init shows no pack prompt, writes no `[canon].packs`, installs every skill and resource, and executes none.
- Materialization refuses symlinked asset paths and leaves external targets untouched.
- Every orchestrator ceremony asset resolves in the repo and in the default installed inventory.
- Installable skill frontmatter is at most 5,000 tokens (bytes/4); `templates/AGENTS.md.tpl` is at most 1,200.

## changed_files
- src/commands/init.ts
- README.md
- templates/config.toml.tpl
- CHANGELOG.md
- tests/init-command.spec.ts
- tests/carriers-install.spec.ts
- tests/ceremony-contract.spec.ts
- tests/embed-canon.spec.ts
- tests/token-budget.spec.ts

Commits: 986c7981 (tests), aaa8972e (implementation). Reviewed at HEAD e7be9c7f.

## verify
- bun test tests/init-command.spec.ts tests/carriers-install.spec.ts tests/ceremony-contract.spec.ts tests/embed-canon.spec.ts tests/token-budget.spec.ts
- bun run build

## Round 1 evidence
- Verify run in a fresh clone at e7be9c7f (`bun install --frozen-lockfile`): 128 pass / 0 fail across the five files; `bun run build` exit 0; the clone's tree stayed clean after the build. Clone removed.
- `git grep -i pack` over `src/` at aaa8972e finds no pack-selection code; the only hit is a licence comment in `src/guards/spoken-secret.ts`. The only inventory filter is `materializeSkills(destRoot, preserve)` (src/embed.ts:311-317). Init feeds it `changedCanonSkills` only when `canon.drift > 0` (src/commands/init.ts:167), so it keeps locally edited files and does not select skills.
- No execution path is left unrecorded: `src/` has no `Bun.$`, `Worker`, or dynamic import of installed paths. The recorder spies on `node:child_process` and `Bun.spawn*`. It is proven live because it observes init's own `git init` (tests/init-command.spec.ts:704).
- Symlink refusal is covered for a skill file, the canon root, an agent file (embed-canon), and an intermediate skill folder (carriers-install F-test at line ~1395).
- Ceremony contract now materializes through `installCanon(VERSION)` into an isolated `AI_ENG_HOME`, with the environment restored afterwards. `machineBase()` follows `AI_ENG_HOME`, so the mirrors stay inside the temporary root.
- Token budget: the payload-based count equals the source count, at most 5,000; the AGENTS.md.tpl limit of 1,200 is the existing test at tests/token-budget.spec.ts:76.

## F1 · MINOR · open
**Where:** tests/init-command.spec.ts:258
**Critic (r1):** `canonPacks` only proves "no `[canon].packs`" for one exact shape. The section regex stops at the first line end because `$` runs in multiline mode, so it captures only the first line after `[canon]`. The value regex also needs exactly `packs = [ ... ]` on one line. If init wrote `[canon]` with a comment or another key first, or `packs=[...]`, or a multi-line array, the helper would return `null` and all three "writes no `[canon].packs`" assertions would still pass (R1/R2: an assertion too weak to fail). → Assert directly on the written config: no line matches `^\s*\[canon\]` and no line matches `^\s*packs\s*=`. Or parse the TOML and assert `canon?.packs === undefined`.

## F2 · MINOR · open
**Where:** README.md:299-300
**Critic (r1):** The README says "init and update ignore their values and never rewrite your config." The re-init hand-off in src/commands/init.ts:231 offers "config", which calls `configMain` and rewrites `[surfaces]` in config.toml; it keeps the `[canon]` bytes. Also, no init-level test runs a re-init on a repo whose config has a legacy `[canon].packs`. The claim rests on init `--yes` handing off to update (update-command.spec.ts:367-415) (R25: the documentation overstates the scope). → Reword to "init and update ignore their values and never rewrite or remove them". Then add one init-command case: a governed repo with `[canon].packs = ["triage"]`, `initMain({ yes: true })`, assert unchanged config bytes, and `assertCanon(home)`.

VERDICT: PASS
MINOR    tests/init-command.spec.ts:258 — F1 canonPacks parse too narrow to fail on other `[canon].packs` shapes → assert no `[canon]`/`packs =` line, or parse TOML
MINOR    README.md:299 — F2 "never rewrite your config" overstates; init→config rewrites `[surfaces]`, and there is no init-level legacy-packs test → narrow wording, add an init re-init case