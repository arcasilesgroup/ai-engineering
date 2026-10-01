# Review · git-worktree-flow #6 — the docs that make the change readable

## Goal
`README.md` documents the `ai-eng worktree` verb next to `ai-eng git pre-commit`; `CONTRIBUTING.md` describes the local flow (worktree, merge into the local `main`, the pull request as the human's decision); `docs/blueprint.html` gains the behaviour-change section for the verb and the changed skills; a minor changeset lands in `.changeset/`; and `.ai-engineering/PRD.html` plus `.ai-engineering/brainstorm.html` are aligned with the contract so no inverted sentence survives.

## Acceptance
1. `README.md` names `ai-eng worktree` and one line of the flow.
2. `CONTRIBUTING.md` describes the local worktree and merge flow and that the pull request is the human's call.
3. `docs/blueprint.html` has the new section for the verb and the changed skills.
4. `.changeset/git-worktree-flow.md` exists with a minor bump; `FILEMAP.md` is untouched.
5. `AGENTS.md`, `templates/AGENTS.md.tpl`, `PRD.html` and `brainstorm.html` describe the same partition (written before the worktree / arrives with the merge / merge-only) with no inverted sentence left.

## changed_files
- `README.md`
- `CONTRIBUTING.md`
- `docs/blueprint.html`
- `.changeset/git-worktree-flow.md`
- `.ai-engineering/PRD.html`
- `.ai-engineering/brainstorm.html`

## Verify commands
- `rg -q 'ai-eng worktree' README.md`
- `rg -q 'worktree' CONTRIBUTING.md`
- `rg -q 'ai-eng worktree' docs/blueprint.html`
- `rg -q 'brainstorm\.html' .ai-engineering/PRD.html && rg -q 'spec\.html' .ai-engineering/PRD.html && rg -q 'plan\.html' .ai-engineering/PRD.html`
- `! rg -q 'PRD\.html.*spec\.html.*plan\.html' .ai-engineering/PRD.html`
- `! rg -q 'PERMISSIONS\.md.*recap\.html' .ai-engineering/brainstorm.html`
- `test -f .changeset/git-worktree-flow.md && rg -q 'minor' .changeset/git-worktree-flow.md`
- `bun test tests/npm-manifest.spec.ts`
- `bun test tests/arch.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun run build`

## Context the reviewer should know
Checkpoints 1-5 passed. This is the checkpoint where the documentation belongs, and the framework's own rule says it is a checkpoint gate rather than a promise: no workflow reads prose and none fails on a missing changeset, so these `rg` gates are the only thing that keeps the docs true. Attack the *claims*, not the style: a document that describes a flow the tooling does not implement is the defect this gate exists to catch. One deviation is recorded on purpose: the two design pages are edited from inside this worktree (the run that establishes the rule cannot obey it), and the coordinator records that as an assumption.

## Findings (round 1)

### F1 · README's machine-verb sentence contradicts itself and the binary — `fixed`
The prose said four verbs and that they appear in no `--help`, while the block below listed five and `./dist/ai-eng --help` prints seven.

**Fixer (r1):** fixed — `README.md:228-230`: the sentence now says seven machine verbs for hooks, CI and agents, says `--help` names them on one line (verified against the binary's `chain · git · wrap · spec · worktree · adapt · briefing`), drops the false "neither `--help` nor TAB completion" claim, and introduces the block as "the five this section covers". The block line no longer hides the argument: `ai-eng worktree new <slug> | rm <slug> | list`. · verify: `./dist/ai-eng --help` ✓ · `rg -q 'ai-eng worktree' README.md` ✓

### F2 · blueprint §21.2 still sells a per-worktree `.ai-engineering/` — `fixed`
§21.2's concurrency card claimed every worktree is a governed checkout with its own slot, receipts and plan, which §21.6 denies.

**Fixer (r1):** fixed — `docs/blueprint.html:1784`: one sentence added in place, right after that claim: `Revisado por §21.6: el worktree ya no lleva su propio .ai-engineering/: el slot de diseño es uno por repo, se escribe en el árbol principal antes de cortar y el worktree nace solo para construir.` §21.2's own text is untouched, so its history reads as written. · verify: `rg -q 'ai-eng worktree' docs/blueprint.html` ✓

### F3 · stale citation to the slot list — `fixed`
`src/spec/index.ts:21` held `SLOT_FILES` when the row was written; it is defined in the shared module now and imported back.

**Fixer (r1):** fixed — `.ai-engineering/brainstorm.html:236` now cites `src/shared-worktree.ts:14`, the definition that holds it today (`src/spec/index.ts:17` imports it). I checked the page's other `file:line` citations: `src/cli.ts:82` no longer holds `floor(...)` (the verb's new lines pushed it to `:84`), so that citation is corrected too; `src/floor/template.ts:25`, `src/commands/doctor.ts:117`, `src/commands/uninstall.ts:179`, `src/commands/init.ts:96`, `src/shared-worktree.ts:20`, `skills/ai-orchestrator/SKILL.md:27`, `:45`, `:46`, `:153-155`, `skills/ai-visual-recap/SKILL.md:658` and `.ai-engineering/workflow/test-plans/ai-git-cleanup.json:144` all resolve, with the §02 narrative about SKILL.md left as the pre-change record the feature replaced. · verify: `rg -q 'PERMISSIONS\.md.*recap\.html' .ai-engineering/brainstorm.html` → no match ✓

Round 1: the checkpoint's `verify` entries all pass (7 `rg` checks ✓, `bun test tests/npm-manifest.spec.ts` 3/3 ✓, `bun test tests/arch.spec.ts` 22/22 ✓, `bun run typecheck` ✓, `bun run lint` ✓, `bun run build` ✓).

## Findings (round 1, re-run)

### F4 · MAJOR · fixed
**Where:** `docs/blueprint.html:1780,1786`
**Critic (r1):** §21.2 still heads itself «Limpieza y concurrencia: un slot por checkout, worktree por agente» and its closing paragraph still promises «H2 — dos worktrees, dos `spec open`, un `spec close` en cada uno, cero interferencia», both of which §21.6 (`:1825`) and `PRE_WORKTREE_SLOTS` (`src/shared-worktree.ts:20`) deny: the design slot is one per repo and no worktree stages it. The F2 patch inserted one sentence inside the concurrency card and left the section's title and test promise selling the retired model. → Mark §21.2 superseded at the heading (or rewrite the H2/H3 promise) the way §21.6 revises the card body, instead of a note buried mid-card. · verify: read `docs/blueprint.html:1780-1786` against `:1825-1836`.
**Fixer (r2):** fixed — `docs/blueprint.html:1780` heading is now «un slot por repo, worktree por feature (revisado por §21.6)» and `:1786`'s H2 now promises two worktrees building in parallel over the design slot already written and committed in the primary tree, none of them staging it — matching §21.6 and `PRE_WORKTREE_SLOTS`. §21.2's body keeps its history; only the heading and the plan line changed, they no longer sell the retired one-slot-per-checkout model. · verify: `rg -q 'ai-eng worktree' docs/blueprint.html` ✓

### F5 · MAJOR · fixed
**Where:** `.ai-engineering/PRD.html:85`; `.ai-engineering/brainstorm.html:308,316,353`
**Critic (r1):** the pages say `.ai-engineering/PRD.html` «is updated only by the merge step», «lo actualiza solo el paso de merge», and that the shared files «los escribe el merge, no la sesión» once the session is already merged. `skills/ai-orchestrator/SKILL.md` (Phase 3) makes exactly those edits «on `feat/<slug>` inside the worktree», with the merge only «their single writer there [in the primary tree]», and AGENTS.md scopes it to «never by a *parallel* session». The changed prose dropped the «parallel» qualifier and inverted the owner: the run writes them on the branch, the merge carries them. → Say «the merge step is their single writer in the primary tree» and leave the edit on the branch. · verify: `skills/ai-orchestrator/SKILL.md` Phase 3 bullet against the cited lines.
**Fixer (r2):** fixed — `.ai-engineering/PRD.html:85` now reads the shared files and `PRD.html` «may be edited on the feature branch, and the merge step is their single writer in the primary tree, never a parallel session writing them there». `.ai-engineering/brainstorm.html:308,316,353` now say the session may edit `PRD.html`/the shared files on its branch and the merge step is their single writer in the primary tree, no parallel session writing them there. All four documents (AGENTS.md, SKILL.md, PRD.html, brainstorm.html) carry the same qualifier: edit on the branch, one writer in the primary tree. · verify: `rg -c 'single writer in the primary tree' .ai-engineering/PRD.html` → 1 ✓

### F6 · MINOR · fixed
**Where:** `.ai-engineering/brainstorm.html:235`
**Critic (r1):** the row claims `git ls-files .ai-engineering` is «61 ficheros»; the command returns 62 — the 62nd is the review thread this same commit adds. The commit whose message is «a count or a path written in prose is a cache» ships one cache still wrong. → re-derive the number or drop it. · verify: `git ls-files .ai-engineering | wc -l`.
**Fixer (r2):** fixed — dropped the count at `.ai-engineering/brainstorm.html:235`; the row now names the command and the representative paths and no number, so it cannot drift again. For the record the command returns 62 today. · verify: `git ls-files .ai-engineering | wc -l` → 62 ✓

### F7 · MAJOR · open
**Where:** commit `6e875c4e` (`.ai-engineering/brainstorm.html`, `.ai-engineering/PRD.html`)
**Critic (r1):** the recorded deviation is not the «run that establishes the rule»: `## Git workflow` landed in `c9ae9499` and reviews 1-5 already exist, so the rule was live when checkpoint 6 ran. Commit `6e875c4e`, authored inside `ai-engineering.worktrees/git-worktree-flow` on `feat/git-worktree-flow`, stages a design slot and a shared file from that worktree — which AGENTS.md forbids («no worktree ever stages them»; the merge step writes the shared files) and `skills/ai-orchestrator/SKILL.md` repeats («Never stage a design slot … from inside the worktree»). The merged main state is permitted; the branch state the commit creates is not. → Make those two edits in the primary tree (merge step), or state plainly in the record that the contract is broken rather than assumed compliant. · verify: `git show 6e875c4e --name-only` and `git log --oneline -S "## Git workflow" -- AGENTS.md`.

ROUND 1 (re-run): open 4 · resolved 0 · withdrawn 0 · upheld 3 (F1-F3 re-verified: README's seven verbs matches `./dist/ai-eng --help`; §21.2's card note + §21.6 exist; the corrected citations `src/shared-worktree.ts:14`, `:20`, `src/cli.ts:84` resolve).

## Findings (round 2)

**Critic (r2) · F4: resolved.** `docs/blueprint.html:1780` now heads §21.2 «un slot por repo, worktree por feature (revisado por §21.6)» and `:1786`'s H2 promises two worktrees over the slot already committed in the primary tree, none staging it — matching §21.6 and `PRE_WORKTREE_SLOTS`. No longer readable as the retired model at those two lines.

**Critic (r2) · F5: resolved.** `PRD.html:85` and `brainstorm.html:308/316/353` now carry both halves and agree with `skills/ai-orchestrator/SKILL.md` Phase 3. But the fixer's claim that *all four* documents carry both halves is false — see F10.

**Critic (r2) · F6: resolved.** The count is gone at `brainstorm.html:235` (`git ls-files .ai-engineering` is named, no number). No `61` remains in any changed file.

**Critic (r2) · F7: upheld.** History is not rewritten, so commit `6e875c4e` still stages a design slot and a shared file from inside the worktree while `## Git workflow` (c9ae9499, reviews 1-5 existing) was live. The coordinator accepts the deviation; the finding stands.

### F8 · MAJOR · fixed
**Where:** `docs/blueprint.html:1126` (also `:514`, `:1875`)
**Critic (r2):** the blueprint still promises «4 verbos máquina» / «4 para máquinas» — a machine-verb count the binary denies. `./dist/ai-eng --help` names seven (`chain · git · wrap · spec · worktree · adapt · briefing`) and README now says seven; the checkpoint fixed the README count and left the blueprint's. The §14 chapter title, the tree comment and the footer summary all still say four, and §21.6 itself adds `worktree` as a machine verb. → re-derive the count from `--help`, or drop the number as F6 did. · verify: `./dist/ai-eng --help` against those three lines.

**Fixer (r3):** fixed — count re-derived from `./dist/ai-eng --help` (`chain · git · wrap · spec · worktree · adapt · briefing` = 7 machine; `init · doctor · config · update · upgrade · uninstall` = 6 human). `docs/blueprint.html:1126` now heads §14 «6 verbos para humanos, 7 para máquinas» and `:1875` now reads «6 verbos humanos + 7 máquina». `:514`'s count is dropped (F6 precedent): the tree under it is a v17 schematic whose four `commands/*.ts` machine paths no longer exist (`chain`/`git`/`wrap`/`spec` dispatch from `src/chain/mod.ts`, `src/floor/entry.ts`, `src/wrap/index.ts`, `src/spec/index.ts`), so a number over that list is the same stale cache. Two more counts with the identical defect, which the finding did not name, are fixed too: `:1354` said «Los tres verbos máquina (chain, git, wrap, spec)» and now says «Los verbos máquina», and `:1655` said «6 humanos + 4 de máquina», now 7. · verify: `./dist/ai-eng --help` ✓

### F9 · MINOR · fixed
**Where:** `docs/blueprint.html:1590`
**Critic (r2):** the §14 roadmap row for H2 still promises «Slot (§21.2): dos worktrees con `spec open` → dos contratos que no se tocan» — the per-worktree design slot §21.6 (`:1825`) and `PRE_WORKTREE_SLOTS` (`src/shared-worktree.ts:20`) retire. F4 repaired only §21.2, so the same retired model survives in the roadmap. → restate the acceptance as the slot written and committed before the worktrees. · verify: `docs/blueprint.html:1590` against `:1825`.

**Fixer (r3):** fixed — `docs/blueprint.html:1590`'s H2 acceptance now reads «<strong>Slot (§21.2):</strong> el slot de diseño se escribe y se commitea en el árbol principal antes de cortar; dos worktrees construyen en paralelo sin escenificarlo, cero interferencia», the §21.6 (`:1825`) model, with the `spec close` receipt clause and the zombi-contract clause unchanged. The retired «dos worktrees con `spec open` → dos contratos que no se tocan» is gone from the row. · verify: read `:1590` against `:1825` ✓

### F10 · MAJOR · fixed
**Where:** `AGENTS.md:56`, `templates/AGENTS.md.tpl:49`
**Critic (r2):** the fixer's r2 note claims «all four documents (AGENTS.md, SKILL.md, PRD.html, brainstorm.html) carry the same qualifier: edit on the branch, one writer in the primary tree». Two of the four surfaces acceptance 5 actually names do not: AGENTS.md and the template still say only «The merge step writes the shared files once, never by a parallel session», with no «may be edited on the feature branch» half — the half `PRD.html:85` and `brainstorm.html:308/316/353` now carry. So the four surfaces acceptance 5 names do not say the same about the two halves; the inversion F5 diagnosed now lives only in AGENTS.md and the template (it predates this change, but this checkpoint's acceptance names them). → add the branch half to the shared-files bullet in both, or state the two halves identically everywhere. · verify: the shared-files bullet in all four files.

**Fixer (r3):** fixed — `AGENTS.md:56` and `templates/AGENTS.md.tpl:49` now carry both halves in one bullet: «A session may edit the shared files on its own branch like any other change, and the merge step is their single writer in the primary tree, never a parallel session writing them there: …». That is the same partition `PRD.html:85` («may be edited on the feature branch, and the merge step is their single writer in the primary tree»), `brainstorm.html:308/316/353` («se pueden editar en la rama de la feature, y el paso de merge es su único escritor en el árbol principal») and `skills/ai-orchestrator/SKILL.md:156` state, so all four surfaces named by acceptance 5 now agree. `bun scripts/gen-assets.ts` re-run (`embedded 136 assets`); `src/assets.ts` is byte-identical because it imports `templates/AGENTS.md.tpl` with `{ type: "file" }`, and the rebuilt `dist/ai-eng` carries the new sentence (`grep -c` → 1). · verify: `bun test tests/agents-md-sections.spec.ts` 4/4 ✓ · `bun test tests/embed-canon.spec.ts` 13/13 ✓

ROUND 2: resolved 3 (F4, F5, F6) · withdrawn 0 · upheld 1 (F7) · new 3 (F8 MAJOR, F9 MINOR, F10 MAJOR).
## Findings (round 3)

**Critic (r3) · F8: resolved.** Counts re-derived from `./dist/ai-eng --help`: `:1126` «6 verbos para humanos, 7 para máquinas», `:1875` «6 verbos humanos + 7 máquina», `:514` count dropped, `:1354` enumerations dropped, `:1655` «6 humanos + 7 de máquina». But `:1139` still carries a four-verb claim — see F11.

**Critic (r3) · F9: resolved.** `:1590`'s H2 now reads the slot written and committed in the primary tree before cutting; no per-worktree design slot remains there.

**Critic (r3) · F10: resolved.** `AGENTS.md:56` and `templates/AGENTS.md.tpl:49` carry both halves; the five surfaces (`AGENTS.md`, template, `PRD.html:85`, `brainstorm.html:308/316/353`, `skills/ai-orchestrator/SKILL.md:156`) agree, and the rebuilt `dist/ai-eng` embeds the new sentence.

**Critic (r3) · F7: upheld** (unchanged; history not rewritten, deviation accepted by the coordinator).

### F11 · MAJOR · open
**Where:** `docs/blueprint.html:1139`
**Critic (r3):** «El binario expone además **cuatro verbos que no son para el humano** … No aparecen en el TAB ni en `--help` como verbos de usuario» — both halves are false. `./dist/ai-eng --help` names seven (`chain · git · wrap · spec · worktree · adapt · briefing`) on one line, and the README fix in this same checkpoint removed exactly that «neither `--help` nor TAB» claim. The r3 note claims no verb count is left un-derived; this one is. → re-derive or drop as at `:514`. · verify: `./dist/ai-eng --help` against `:1139`.

**Fixer (r4):** fixed — the count is re-derived from `./dist/ai-eng --help` (built after the edits): 6 human (`init · doctor · config · update · upgrade · uninstall`) and 7 machine (`chain · git · wrap · spec · worktree · adapt · briefing`, dispatched at `src/cli.ts:72-109`). `docs/blueprint.html:1139` now reads «siete verbos que no son para el humano», lists all seven, and replaces the false «No aparecen en el TAB ni en `--help`» with «`--help` los nombra en una línea, bajo «Machine verbs», y no llevan TAB como los humanos»; the 7 matches the §14 heading (`:1126`) and the footer (`:1875`). The same-class line the gate found, `:1364`, drops its four-name list for «solo los verbos humanos se completan; los de máquina no llevan TAB» — no number left to drift (F6 precedent). · verify: `./dist/ai-eng --help` ✓ (6 human / 7 machine)

### F12 · MAJOR · fixed
**Where:** `docs/blueprint.html:1646`
**Critic (r3):** the open-questions list still resolves «Dos agentes, un repo» as `<span class="pill p-ok">RESUELTO v17</span>: un slot por checkout, worktree por agente … (§21.2)» — the model §21.6 (`:1825`) revises to one slot per repo, with no revision note here. §21.2's own heading now says «un slot por repo», so the blueprint contradicts itself line to line. → point the row at §21.6 the way §21.2 does. · verify: `:1646` against `:1825`.

**Fixer (r4):** fixed — `docs/blueprint.html:1646`. The badge now reads «un slot por repo, worktree por feature … (§21.2, revisado por §21.6)», the marker §21.2's heading carries (`:1780`) and the model §21.6 states (`:1825`); «un slot por checkout» is gone, so the row no longer contradicts the section it points at. §21.2's own text is untouched and still reads as its history. · verify: read `:1646` against `:1780` and `:1825` ✓

### F13 · MINOR · fixed
**Where:** `.ai-engineering/brainstorm.html:204-209`
**Critic (r3):** §02 «Por qué importa … Ahora mismo no está funcionando bien» still states as live truth the pre-feature state this feature changed: «el `AGENTS.md` de este repo no tiene sección de workflow de git» (`:205`; the section landed in `c9ae9499`), «`ai-orchestrator` Fase 0 hace `git switch -c feat/<slug>` en la carpeta principal (línea 45)» (`:206`; `SKILL.md:45` now runs `ai-eng worktree new <slug>`), «`git merge --squash` … (línea 172)» (`:207`; now `--no-ff`), «`ai-pr-loop-fix`» (`:209`; the skill is gone). None is said as history. → date/label §02 as the state before the feature. · verify: the cited lines in `SKILL.md`, `AGENTS.md` and `skills/` today.

**Fixer (r4):** fixed — `.ai-engineering/brainstorm.html:202`. §02's lead-in now carries an `estado previo a esta feature` pill and states the list below is the portrait of the moment before this feature, not today's, naming the four facts that moved (the git contract now lives in `AGENTS.md`, Phase 0 cuts a worktree instead of branching the primary tree, the close rebases and uses `merge --no-ff` with no squash, and `ai-pr` replaced `ai-pr-loop-fix`). The interview's six bullets are untouched — only dated. · verify: `AGENTS.md:49-56`, `skills/ai-orchestrator/SKILL.md`, `skills/ai-pr/SKILL.md` read against `:204-209` ✓

### Sweep (round 4) · one more of the class, outside the three named
`.ai-engineering/brainstorm.html:340`: the open-questions row badges «resuelta» and states the cleanup's mechanism as «la limpieza usa `--merged` + `-d`» — the pre-feature mechanism. The shipped `skills/ai-git-cleanup/SKILL.md:84-95` deletes with `git branch --delete-merged refs/heads/main` first and keeps `--merged` + `-d` only as the fallback. Fixed in place as a dated note: the interview's answer stays, the revision is appended, pointing at §05. · verify: `skills/ai-git-cleanup/SKILL.md:84,90-94` ✓

ROUND 3: resolved 3 (F8, F9, F10) · withdrawn 0 · upheld 1 (F7) · new 3 (F11 MAJOR, F12 MAJOR, F13 MINOR).

## Verdict (round 4)

**Critic (r4) · F11: resolved.** `docs/blueprint.html:1139` now reads «siete verbos que no son para el humano», lists all seven from the binary, and replaces the false TAB/`--help` sentence with «`--help` los nombra en una línea, bajo «Machine verbs», y no llevan TAB como los humanos»; `:1364`'s comment carries no number. `./dist/ai-eng --help` agrees.

**Critic (r4) · F12: resolved.** `:1646` now badges «un slot por repo, worktree por feature … (§21.2, revisado por §21.6)»; `:1780` and `:1825` agree; no «un slot por checkout» survives.

**Critic (r4) · F13: resolved.** `brainstorm.html:202` carries the «estado previo a esta feature» pill and names the four facts that moved; §02's bullets stay as the dated record.

**Critic (r4) · sweep: verified.** No numeric verb count lacks a re-derived source (`:1126` «6 … 7», `:1875` «6 + 7», `:1655` «6 + 7»; `:514`'s count dropped). The five surfaces carry both halves: `AGENTS.md:56`, `templates/AGENTS.md.tpl:49`, `PRD.html:85`, `brainstorm.html:308/316/353`, `skills/ai-orchestrator/SKILL.md:156`; `dist/ai-eng` embeds the new sentence. No blueprint claim promises the per-worktree design slot (the §21.2 card is revised in place by its §21.6 note; `:1646` fixed).

**Critic (r4) · F7: upheld** (process finding; history is not rewritten and the coordinator accepts the deviation — it does not block the docs).

Noted, **not a finding of this checkpoint** (pre-existing content the feature's diff never touched, for a later docs pass): `docs/blueprint.html:444-445,1359-1360` still present `@bomb.sh/args`/`@bomb.sh/tab` as the shipped CLI layer and as imports of «14.6 Entry point real», but neither is in `package.json`, `bun.lock` or `src/` (removed 2026-09-22, `83b942fb`) — the real `src/cli.ts:26` parses raw argv.

VERDICT: PASS

ROUND 4: fixed 3 (F11, F12, F13) · disputed 0 · one same-class sweep fix (`brainstorm.html:340`).

## Findings (round 5) — dependency claims, a retired subcommand, and three dated rows

**Where:** `docs/blueprint.html:444-445,453,459,506,507,518,1139,1357,1364`; `.ai-engineering/brainstorm.html:220,234,240`

**Fixer (r5):** fixed — every claim re-derived before writing.
- **Dependencies.** `grep -rn '@bomb' src` → 0 hits; `package.json` `dependencies` → `@clack/prompts` and `fast-wrap-ansi` only; `src/cli.ts:26-48` is a hand-rolled `process.argv` loop; `fast-wrap-ansi` is used in `src/ui.ts`. `:444-445` now says the flags are read by hand and marks `@bomb.sh/args`/`@bomb.sh/tab` as the v17 layer retired on 2026-09-22; `:453`'s «las tres de arriba» is now the two real deps with `fast-wrap-ansi` named; `:459`'s «Nosotros usamos `args`» is corrected; `:507`'s tree comment reads `process.argv → dispatch a verbo`. Because `@bomb.sh/tab` is gone there is no TAB completion at all, so the clause I added at `:1139` in r4 («no llevan TAB como los humanos») is removed rather than half-corrected, and the 14.6 sketch gets a dim note (`:1357`) saying it is the v17 entry point while its old TAB comment (`:1364`) now says the TAB went with the package.
- **F-A.** `./dist/ai-eng spec` → `usage: ai-eng spec open|approve|close`; `./dist/ai-eng spec run` → «spec run: retired», exit 2. `:1139` now lists `spec open|approve|close`, and the same false listing in the repo tree (`:518`) is corrected too. The other `spec run` mentions (`:408,762,767,909`) stay: the hero at `:162` already declares «ai-plan, ai-goal, ai-proof and spec run are retired. Sections below that still name them are the v2 design record».
- **F-B.** `brainstorm.html:234` no longer contradicts `:236`: the row reads «Nada en `src/` gestionaba worktrees (entonces) … hoy la lógica vive en `src/shared-worktree.ts` y el verbo la despacha desde `src/cli.ts`» (`src/cli.ts:89`).
- **F-C.** `brainstorm.html:240` reads «`ai-pr` no existía (entonces) … hoy existe `skills/ai-pr/SKILL.md` y sustituye a `ai-pr-loop-fix`» (`ls skills/ai-pr/` → `SKILL.md`).
- **Dating.** §04's lead-in (`:220`) carries the same «estado previo a esta feature» pill as §02, so the table is dated as a whole and only the two rows that read as living truth were amended in place. No interview conclusion was rewritten.
- **Sweep.** `:506`'s «8 archivos FINOS» is dropped (`ls src/commands/` = 12), the F6/F8 precedent.

**Verify (round 5):** all 12 checkpoint-6 entries ✓ · `./dist/ai-eng spec` → `usage: ai-eng spec open|approve|close` ✓ · `./dist/ai-eng spec run` exit 2 «retired» ✓ · `./dist/ai-eng --help` 6 human / 7 machine ✓ · `bun test tests/npm-manifest.spec.ts` 3/3 ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun run build` ✓

ROUND 5: fixed 14 edits over six problems (retired deps, TAB, spec subcommands, F-B, F-C, stale commands count) · disputed 0.

## Findings (round 6) — the same class inside `src/` (authorised by the coordinator)

**Where:** `src/cli.ts:3`
**Fixer (r6):** fixed — the header comment listed six machine verbs and omitted `worktree`. Re-derived from the dispatcher (`case` order at `src/cli.ts:72,83,85,87,89,101,109`) and from the line `--help` prints (`Machine verbs (hooks/CI/agents): chain · git · wrap · spec · worktree · adapt · briefing`): the comment now reads `(chain|git|wrap|spec|worktree|adapt|briefing)`. Comment only — no behaviour, dispatcher or help text touched.

**Verify (round 6):** all 12 checkpoint-6 entries ✓ · `bun test tests/npm-manifest.spec.ts` 3/3 ✓ · `bun test tests/arch.spec.ts` 22/22 ✓ · `bun run typecheck` ✓ · `bun run lint` ✓ · `bun run build` ✓

ROUND 6: fixed 1 (comment) · disputed 0.