# Changelog

Rule 4 of `AGENTS.md`: there are no compatibility shims here, so every hard rename and
every hard delete is written down in this file, in the words somebody upgrading would
search for.

## [Unreleased]

### Added (spec 047 — the cycle's wall budget)

- Three named budgets join `contract.py`: `CYCLE_WALL_BUDGET_MINUTES = 180` (the owner's
  decision of 2026-08-29, carried by PO-27), `CRITIC_TIMEBOX_MINUTES = 40` and
  `CRITIC_CALLS_MAX = 120` — the last two derived, and the comment says so. The clock
  disqualifies a run and never approves one: no box ever ticks because a number said so.
- `ai-eng report vitals --session <id>` reads `.ai/events.jsonl` and attributes the
  minutes between `ts` stamps to the earlier event's `cls`, printing the wall time beside
  the budget. Over it: `INCOMPLETE [OVER_BUDGET]` naming the largest bucket; no readable
  pair of events: `INCOMPLETE [NO_DATA]`, never an empty green.
- The five critic skills (`ai-challenge`, `ai-council`, `ai-review`, `ai-verify`,
  `ai-security`) carry the box in their own text — 40 minutes, 120 calls, the verdict
  returns in the result, and `TIMEBOXED` with what it has when the box closes. A partial
  verdict is a verdict; silence is not.
- `just check-all` runs every step of `just check` in one pass and prints the full list of
  red steps at the end — k defects, one pass. `just check` itself is unchanged.
- `ai-goal` closes a blocked turn with one `BLOCKED:` line naming the unblock and prints
  `report vitals` beside `audit verify` at the handover; `ai-build` never relaunches the
  whole gate for one red.
- `tests/test_cycle_budget.py` is the fixture that pins all of it, red first, over the
  approved digests (spec 047; approvals 0033, 0034, 0035 — the plan moved twice for
  mechanical defects its own `--tick` refused, each correction re-signed).

### Added (spec 046 — visual HTML records)

- The cycle's review surfaces are pages now, rendered in this repository and nowhere
  else. `ai-eng report view --spec NNN` renders a spec and its plan — their prose and
  their fenced `visual` blocks — into one self-contained file under `.ai/views/`;
  `ai-eng report recap --spec NNN --base <ref>` derives a record of what a range
  changed under `.ai/reports/NNN-recap-<slug>.html` from `git diff --name-status` and
  real hunks only. Both print the page as a `file://` link beside the canonical
  digests they rendered. The block grammar, the diff→block mapping and the editorial
  bar are harvested from Builder.io's visual-plan and visual-recap skills (MIT,
  attributed in `policy/visual-pages.md`); the hosted Plan MCP, the `@agent-native/core`
  npm CLI and MDX are not, by the owner's constraint and the audit in
  `.ai/reports/021-skills-integration-roadmap.html`.
- Two skills ship with them: `/ai-visual-plan` turns a plan into the page a human
  approves from, `/ai-visual-recap` turns a finished work unit into the page a reviewer
  reads before the raw diff. The tree carries twenty procedures and the manifest
  declares twenty-two capabilities; the capability schema's digest moved for the two
  new ids, from `80c5de63…` to `ba21fa3d…`.
- The six cycle skills gained a link duty: ai-spec and ai-plan hand over the view link
  beside the Markdown, ai-build and ai-goal put the recap link in the hand-off, ai-ship
  carries it into the pull-request body, and ai-research prints the `file://` URL of
  the report it already wrote. A turn that ends in a page ends with its link.
- `.github/workflows/check.yml` gained a `recap` job: on a pull request it renders the
  page from the real range, uploads it as a run artifact, and comments exactly one
  link — GitHub Pages is off for this repository (a 404 is the measurement), and the
  job fails loudly if Pages is ever enabled under it, because publishing is the
  owner's privacy decision, not a bot's default. The job runs on every event and
  says "not applicable" on a push, the way the claim step does: the workflow's own
  contract refuses a lane conditioned on the event name.
- `pyyaml` joined the dev dependency group, pinned: the gate's task checks prove a
  workflow parses, and a check that cannot import its tool is a check that cannot fail.

### Changed (spec 046 — the clean cut)

- Views are derived, recaps are records, and neither is an approval: the ADR at the
  canonical digests of `spec.md` and `plan.md` is still the sole gate (D-046-01), and
  a page prints those digests so a stale one is identifiable from its own header.
  Page content is authored as `visual` blocks in the Markdown and rendered by a
  command, never written as HTML by prose (D-046-02).
- The fence is a wall: `spec.fence_records` keeps the task parser, the approval digest
  and the intent counter from reading inside a fenced block, which is what makes a
  `**check**:` line safe to put in one. Grill round 1 executed the injection path
  first; the ordering is the precondition, not a warning.
- The doctrine ceiling moved 150 → 180 by the owner's explicit authorization, so the
  four always-on rules and the link duty join the twelve.
- `report` is seven subcommands now — `digest view recap issue surfaces intent
  blocked` — and the verb's `will` banner names both page writers beside the digest
  receipt and the Intent page.
- A correction to an approved spec moves its digest and is re-signed, never accepted
  around (D-046-05): the map found three real broken references in 046's own approved
  bytes, the references were fixed, and ADR 0032 re-approved the specification at
  its corrected digest, superseding ADR 0031. `docs/adr/0023` is the precedent.

### Changed (spec 045 — critics inside the spec)

- `/ai-challenge` is the grill: at most ten `### Q` findings per round, each decided
  by executing its command, returned to the session; the author folds the round into
  the specification's new `## Grill` section and revises the attacked sentences in
  place. The exhaustive every-sentence sweep is retired with it.
- `/ai-council` runs one pass: five named lenses plus the anonymous cross-read in a
  single fork; the chairman's separate round and its page are folded into the
  author's verdict, and the result lands in the specification's `## Council`
  section. No `council.md` and no `council.html` are created for new specs.
- The `ai-eng spec new` template carries `## Grill` and `## Council` after
  `## Challenged once` and demands exactly three real options under `## Options
  considered`; `ai-spec` gained step 11, the fold-in-place rule.
- `just council` is the critic step over both shapes: historical `specs/*/council.md`
  files keep their counts, and a declared critic section in a `spec.md` is refused
  for carrying the template's prompt, an empty heading without `none`, a malformed
  `ran: round <n>, <date> — <n> min` line, or a `### Q` without its `**A:**`. A
  section that declares no round still reads "has not run", as before.
- The no-authority test scopes to `## Council` bodies for the new shape; the
  file-wide rule over historical councils is unchanged.
- `specs/*/approval.md` is no longer created: the approval record returns to
  `docs/adr/` as a digest-approval MADR, the series resumed by ADR 0028 after the
  gap since 0026. The fifteen historical dossiers stay exactly where they are.
- A behaviour change for consumer repositories that pinned the wheel: the two
  critic skills now end with sections inside the specification instead of files
  beside it, and their `## What it produces` lines name those sections.

### Removed (spec 044 — ponytail audit residual cuts)

- The orphan layer is deleted: twelve src modules with zero production callers —
  `constellation`, `decision_fw`, `decision_boundary`, `intake`, `trim`, `versions`,
  `lane_merge`, `loopgate`, `skillify`, `verify_cold`, `evidencing`, `answer_key` —
  with the fourteen test suites that were their only callers. `git revert` reinstates
  any of them; the design records live in specs 030-042.
- The orphan register goes with them: `policy/module-status.toml`,
  `wiring.module_status()` and `tests/test_orphan_register.py`. With no caller-less
  module left the register had nothing to register. The stale rows for `sbom`, `scan`,
  `skillmap` and `coverage` are removed with the file; those four modules are KEPT —
  the gate itself calls them (`just sbom`, `just security`, `just map`, the evals lane)
  and the register rows saying otherwise were wrong.
- Root `answer-key.yaml` (a sample with a zeroed digest, read by nothing) and
  `policy/answer-key-v1.schema.json` (its schema) are deleted with the module.
- Zero-caller dead weight: `spec.self_contained`/`_LEAKS` (with
  `tests/test_spec_containment.py`), `model_router.bail_out` (with its test),
  `audit.replay` (the wrapper; `audit replay` the verb always used `_replay` directly),
  the root sample file.
- One-caller relics folded: `cli.UNEXPECTED` → `EXEC_FACTS_FAIL` inline;
  `solution_intent.NOT_HASHED` → the digest filter itself; `spec._document_relations`
  is a named seam wrapper, not a bare alias.
- Test-shaped flexibility: `cost.calibrate` loses its `threshold_usd` and `interactive`
  overrides — the gate reads `policy()` and fails closed over threshold, always;
  `cost._Policy` becomes a validating function. `spec_transaction.publish` keeps its
  return; the Windows publication arm is untouched (spec 010's platform contract).

### Changed (spec 044)

- `intent.pinned_policy(path, digest, *, bounded)` is the one digest-pinned policy
  loader; `acceptance`, `capability`, `evidence`, `madr` and `outcome` now delegate to
  it and keep their own refusal vocabularies. `evidence._read_policy` and
  `outcome._read_policy` are deleted.
- `acceptance._parse_legacy` delegates to `text.flat_yaml(strict=True)`; the strict
  refusals (containers, repeated keys) live in the shared parser, so the record reader
  and the acceptance reader cannot drift.
- `paths.git_lines(root, *flags, timeout=60)` is the shared `git ls-files` reader;
  `doctor.tracked_files` (timeout=10), `contract.tracked` and `madr._worktree_files`
  use it. `madr` passes its listings through its own `_git` so the GIT_* sanitizer
  still holds. `evidence` keeps its bytes-level reader deliberately (receipt digest).
- `wiring.cli_answers(*arguments, cwd=None)` is the one CLI probe; `doctor._run_cli`
  delegates to it.
- `uninstall._hex` uses `re.fullmatch` instead of a character loop.
- The `sys.path.insert` + `# noqa: E402` idiom is removed from every pytest module
  (pyproject `pythonpath` covers it; `tests/evals` joins the path). Kept modules whose
  register rows died: `sbom`, `scan`, `skillmap`, `coverage` — kept, reason recorded
  here, because the gate reaches them.

### Removed (spec 043 — ponytail audit cuts)

- `skeletons.seed_intent` and its `_seed_incomplete`/`_path_identity`/`_same_identity`/
  `_remove_owned` helpers, the `INTENT_*` result constants and `import secrets` are
  hard-deleted with their two test suites (`test_skeleton_seed_is_write_once`,
  `test_skeleton_seed_cleans_failed_publication`). Nothing in the product called it —
  no verb writes `.ai/intent.md`; the framework asks you to write it (`/ai-spec`). A
  checkout that seeded an Intent through this function writes the file itself or pins
  the old wheel; there is no shim.
- `ui.ask` is hard-deleted with its parametrized suite; nothing imported it, and
  `init.ask` owns its own prompt.
- `surface.Standing.as_dict`/`Report.as_dict` are deleted; no caller rendered a surface
  report through them.
- `[guards] design_budget` and `[observability] encoding` in the skeleton
  `.ai/config.toml` are gone: no line of code read either key, so deleting one could not
  break anything that existed.
- `hooks/_otlp.redact(event, mode)` / `as_logs(events, mode)` lost the `mode`
  parameter (`redact = "strict"` config keys were already unread) and `post(signal, …)`
  lost the `signal` parameter (the exporter has exactly one lane, logs). Callers passing
  either now raise `TypeError`; pin the wheel version before upgrading any external
  caller.
- The duplicated primitives collapsed to shared homes this pass:
  `paths.read_bounded` (was three copies in evidence, outcome and capability — the
  capability one read in chunks rather than one bounded read, so it was the closest
  match, not a byte-twin; audit.py's chain reader keeps its own loop because its
  identity check adds size+mtime+ctime pinning the others do not have),
  `intent.canonical_json` (was four private copies), `intent._Schema` now carries
  `anyOf`/`format`/`minimum` so `capability._Schema` and `evidence._SchemaValidator`
  keep only their policy keywords (`madr._Schema` still re-declares anyOf/format in
  place; collapsing it is left for its owner), and `loop_guard` uses `_emit.printable`
  instead of its own sanitizer — which also changes `_emit.model()`'s non-printable
  characters from `?` to `\xNN` escapes, with the length cap now applied after escaping. Behavior is unchanged where tests observe it; three audit
  proposals that would have changed defended behavior (per-revision `git ls-tree`
  history walks, caching the outcome-policy mapping, inlining the chain matcher table)
  were declined because the contract tests refused them.

### Breaking changes

- `contract.CEILING` is hard-deleted, and with it the length branch in
  `contract.audit_one`, the test `test_a_skill_over_the_line_cap_is_a_procedure_that_should_be_a_script`,
  the `"the skill cap"` row in the guards mutation lane and the `skill_ceiling` field that
  `just stats` printed as a denominator. A `SKILL.md` is no longer capped at 80 lines and is
  no longer capped at any number: `contract.SKILL_FOG_CEILING` bounds how hard a skill reads
  and nothing bounds how long it is. Measured before deleting it, across sixteen skills the
  largest file was 80 lines and the largest prose count 52, so the cap was spent on
  frontmatter, blank lines and fenced blocks and was binding on exactly one file. Anything
  importing `contract.CEILING` now raises `AttributeError` and there is no shim.
- A council may now conclude. `/ai-council` writes a verdict and a recommendation where it
  previously had no field in which either could be written, and `docs/adr/0022` supersedes
  `docs/adr/0019` on that boundary. What is refused instead is granted authority —
  `approved`, `approve`, `approval`, `PASS`, `FAIL`, `granted` and an accepted risk — in
  four shapes: a line that is the word, the word as a field, the word after a colon, and
  the word anywhere in the tail of a `Verdict:` or `Recommendation:` line. Three of those
  four caught nothing before. It is not refused in an ordinary sentence elsewhere, and it
  is not refused inside backticks, a fenced block or quotation marks: the wide rule was
  tried and reds this repository's own council file. `EP-195` is not closed by any of this.
- `hooks/change_scope_guard.py` and `hooks/claim_scope_guard.py` are hard-deleted, with no
  replacement and no shim. `change_scope_guard` asked whether any `specs/**/plan.md` was in
  the branch's changed set — existence, never approval, as its own docstring conceded — so
  `touch specs/x/plan.md` satisfied it, and the event log reads 3 blocks against 670
  bypasses. A control bypassed two hundred times for every time it fires is not a control;
  it is a machine for teaching a person to click through the next one, which is the failure
  the whole `@guard` split exists to avoid. `claim_scope_guard` was worse than useless: it
  sat in neither `SECURITY` nor `FLOW`, so `_wrap.deny` printed
  `ai-eng exception --skip ... --guard claim_scope_guard` while `take_bypass` only ever
  consults `FLOW` — a remedy that could not be honoured, printed on a denial that fires on
  an *unreadable* `.ai/claim.json` and therefore locks every edit in the repository
  including the edit that would fix the file. What changes for you: **the fourth file on a
  branch with no plan is no longer denied, and a write outside a held claim is no longer
  denied at the keyboard.** The claim is still recorded and still re-checked from the remote
  at the merge gate, which is where a second machine's claim was always going to be
  authoritative. `hooks/no_verify_guard.py`, `hooks/self_protect.py`,
  `hooks/injection_guard.py` and `hooks/loop_guard.py` are untouched. `ai-eng exception`
  now accepts only `--guard loop_guard`, because that is the only guard left that a person
  may bypass at all.

- The two research reports are hard-renamed and there is no shim:
  `.ai/reports/evolution-proposal/index.html` is now
  `.ai/reports/001-evolution-proposal.html`, and
  `.ai/reports/process-optimization-research/index.html` is now
  `.ai/reports/002-process-optimization-research.html`. Anything naming the old paths — a
  script, a bookmark, an evidence command — stops resolving. What changes for you:
  **`.ai/.gitignore` now keeps reports by the shape of their name rather than by listing
  them**, so a report matching `reports/[0-9][0-9][0-9]-*.html` is committed and reviewed
  like any other change and everything else in that directory stays this machine's. Under
  the old five lines every report after the second was ignored by default: three were, and
  two of those could only be ordered by a file date that a `git checkout` rewrites. `ai-eng
  doctor`'s assertion 17 reads the same shape rather than a hand-written list — the rule is
  written twice on purpose, and CI has already caught one side moving without the other.

- `ai-eng decide` no longer writes into the specification, and `--madr` and `--why` are
  hard-deleted with no shim. The verb had two halves and one destination was chosen with a
  flag: a yaml block appended under the specification's `## Decisions` heading, or a record
  under `docs/adr/`. The first half is gone. Measured before removing it: 70 of those blocks
  exist, every one in specifications 001 to 009, none since 010 eleven specifications ago,
  and nothing in `src/`, `hooks/` or `tests/` ever read one — a writer with no reader is a
  place to put something and forget it. What changes for you: **`ai-eng decide "<title>"`
  now writes a record under `docs/adr/` instead of a block inside the spec, `--madr` is an
  unrecognised argument because there is no longer a choice to make, and `--why` is gone
  with the destination it described.** `--list`, `--accept` and `--supersede` are untouched.
  The 70 existing blocks stay where they are; nothing rewrites a delivered specification.
  One behaviour improved in the same commit: with no specification to record against, the
  verb now says so instead of reporting that git history cannot prove MADR transitions —
  it resolves the target before validating the graph, and resolving writes nothing.

- What an approval of a `plan.md` is a signature on has changed, and there is no shim. The
  digest is now taken over the file with one column masked — the gap between a task's number
  and its bold title, where `ai-eng spec show <id> --task <n> --tick` writes a box and its
  seal. A `spec.md` is untouched and is still signed over its raw bytes, because its eight
  production-ready boxes are a person's claim that `readiness.py` reads. What changes for
  you: **`sha256 plan.md` and the digest `ai-eng` compares against your approval are no
  longer the same number once any task carries a box**, and a plan with no box is unaffected.
  Measured on this repository the day it landed: over 16 plans and 22 specifications the two
  were identical, `specs/010/plan.md` canonicalised to the number `docs/adr/0009` signs, and
  a box on all 141 tasks with every one ticked left it at that same number — so no approval
  on record changed value and nothing was re-signed. Ticking a box no longer voids an
  approval; editing a word, or a task's check command, moves the digest exactly as before.

- The commit anchor is hard-deleted, with no replacement and no shim: the
  `Ai-Eng-Anchor:` footer that `git-hooks/commit-msg` wrote, the `--anchor` and `--anchors`
  arguments of `ai-eng audit`, the three history verdicts that compared the git log against
  the chain, `audit.anchor_line`, and the `anchor_commits` key `ai-eng init` used to seed.
  The generated CI workflow now runs `ai-eng audit verify` without an argument — a wheel
  whose generated CI passes a switch the wheel refuses is an argument error in every
  destination repository. What changes for you: **`ai-eng audit verify --anchors` is an
  unknown-argument error, commits no longer carry or ask for a footer, and the line saying a
  commit is not anchored stops.** In this repository's life the three verdicts produced no
  finding and one false alarm on every commit, and the cure the alarm named needed a person
  at a physical keyboard and was never run. `audit verify`, `audit replay` and
  `audit account` keep every other property, including refusing a link that arrived edited
  before it was sealed. `ai-eng doctor` keeps 25 assertions; assertion 11 loses only the
  question about signing a footer, so a machine whose chain is not established now reads
  `ok` there rather than `undecidable`. Recorded in
  `specs/022-the-anchor-nobody-could-answer-for` and approved at digests by `docs/adr/0017`.

- `contract.REPO_CEILING`, `contract.repo_lines` and `contract.NOT_THE_PRODUCT` are
  hard-deleted, with no replacement and no shim, and `tests/seal_ceiling.py` and the `just
  seal` recipe go with them. The ceiling was a total-line bound on the repository that a test
  obliged to stay within 400 lines of the tree it claimed to bound, so it moved in fifty of
  the last fifty commits — four of which do nothing else — and the one row in
  `docs/blocked.toml`, the only time this machine ever stopped and asked a person, is a
  fixed-point collision over that integer between two sessions. Nothing in its history shows
  it catching a defect. What changes for you: **`just seal` no longer exists, a commit no
  longer needs an arithmetic step, and anything importing those three names from `contract`
  breaks at import.** `contract.tracked` and `contract.count` are untouched.
  `contract.TEST_RATIO_MAX` is the size bound that remains, and its own comment says it
  covers the shape the ceiling could not see: a suite growing while the product does not.
  Recorded as EP-299, withdrawn in place in `docs/requirements.toml`, and in
  `specs/021-three-controls-that-could-not-say-no`.

- `"maxItems": 15` is removed from `policy/capability-manifest.schema.json`. It could not
  fire: measured against a sixteenth capability in five shapes, anything that would trip it
  died earlier in the exact-equality check against `allowed_ids`, and the one situation where
  it did fire was after somebody had correctly widened both lists — when it answered "the
  manifest is invalid" without naming which rule. What changes for you: **nothing, unless you
  were relying on the catalogue being refused above fifteen entries, which it never was for
  that reason.** `allowed_ids` and `minItems` are untouched and still refuse an undeclared or
  empty catalogue. This closes EP-308, which `docs/audit-2026-08-16.md` already listed among
  the proofs it withdrew.

- `redact` is gone from `[observability]` in `.ai/config.toml`, and the exporter always
  redacts. It accepted `"strict"` and `"none"`, and `"none"` sent every field outside the
  two allow-lists to the collector verbatim — free text, guard reasons, whatever a payload
  happened to carry. A configuration value that disables a privacy control is a control
  whoever runs the exporter can switch off, and nothing downstream could tell a machine
  that had redacted from one that had been told not to. What changes for you: **if your pin
  says `redact = "none"`, that line now does nothing and your exports are redacted.** The
  key is simply ignored rather than rejected, so nothing breaks on upgrade; delete it when
  convenient. Recorded as D-014-08 in `specs/014-security-baseline-no-false-pass`.

- `policy/surfaces.toml` has no `proven` column. It was a field somebody typed, and
  OpenCode's row said `true` with no denial ever executed there — so `ai-eng doctor`'s
  coverage line printed "a denial has executed here" on the strength of it. The word is now
  read from that surface's enforcement receipt under `.ai/receipts/surface`, and the table
  has no way to assert it. What changes for you: **every surface that can deny reads
  `UNPROVEN` until a denial is receipted on it**, including ones that deny perfectly
  well today. The two instruction-only surfaces still read `ADVISES`, which is what
  they always were. Nothing lost a
  capability; the claim lost its evidence. A repository carrying a hand-written
  `surfaces.toml` with that field keeps working — the field is ignored, and it is ignored
  rather than honoured on purpose.

- The repository owner delegated approval of this wave's records, in the session that
  closed P0, in these words: "Cierra el P0 automáticamente rellenando tú lo que haga falta.
  Arregla eso también porque debe ser siempre automático." Recorded here because MADRs
  0005, 0006 and 0007 name this entry as the reference for their approval, and an approval
  reference that points at nothing a reader can open is not a reference. The role recorded
  in those three records is `repository owner`; no model supplied it, and the schema refuses
  a role that names an agent or a reviewer for exactly that reason.

- The guard that used to be `hooks/design_gate.py` is now `hooks/change_scope_guard.py`.
  Nothing answers to the old path: if you referred to it in a settings file, a script or a
  document, that line now points at a file that is not there, and a hook whose file is
  missing does not run. The old name said "design" for a check that has never looked at a
  design — it counts how many files a change touches and stops one that has outgrown its
  plan. The name it had sent people looking for a design document that does not exist. The
  operator-facing setting is still spelled `design_budget`, so that one line does not move
  under you; it will be renamed in its own release, and this file will say so.

- `ai-eng plan` is now `ai-eng exception`, and `src/ai_engineering/plan.py` is gone,
  replaced by `src/ai_engineering/exception.py`. The verb never planned anything. It asks a
  person at a keyboard to grant one fifteen-minute bypass of a flow guard, which is an
  exception to the rules and not a plan for anything. It was also the word printed at
  somebody every time a guard denied them, which meant the product's own error messages
  advertised a verb that did something else.

- `ai-eng digest` is now `ai-eng report digest`, and `src/ai_engineering/digest.py` is gone,
  replaced by `src/ai_engineering/report.py`. `ai-eng report issue` joins it. The old verb
  did one thing and had a name that promised a category, and the second thing it was going
  to have to do had nowhere to live.

- `ai-eng decide --adr` is now `ai-eng decide --madr`. It writes the same file in the same
  place. The record it writes is a Structured MADR — a specific documented format with
  required fields — and calling the flag `--adr` invited the loose kind, which is prose
  with a heading. There is no alias: the old spelling is refused, so a script that passes
  it stops rather than silently deciding nothing.

- An accepted risk is no longer a block of text inside a spec. It is published as one file
  at `specs/NNN-slug/acceptance-r-NNN-NN/record.json`, created by a rename that fails if
  something is already there, and never rewritten afterwards. `spec.md` is not opened for
  writing at all any more. The blocks written by earlier versions are still read, exactly as
  they were written, and are never altered in place: renewing one publishes a new record and
  leaves the old text alone. What changed for you: accepting a risk no longer edits a file
  you are also editing, and two acceptances racing each other can no longer overwrite one
  another, because the second rename loses instead of winning.

- `ai-eng doctor` reports the eight production-ready boxes and how old the proof of each
  one is. It reads a declaration you commit at `.ai/readiness.json` and one receipt per box
  under `.ai/receipts`, and a box with no receipt, a stale receipt or a receipt that does not
  match what you declared reads `INCOMPLETE` — unproven, which is not the same as passed and
  is never shown as green. The receipts are this machine's and stay ignored; the declaration
  is reviewed, and `ai-eng doctor` fails a repository that has receipts and has not committed
  one. Nothing here is gated on it yet; doctor tells you, and does not decide whether
  anything gets a URL.

- If this repository was set up by an earlier release, its `.ai/.gitignore` ignores
  everything under `.ai/` except three names, and the readiness declaration is not one of
  them — so a declaration written there is dropped by `git add -A` without a word. Add
  `!readiness.json` to `.ai/.gitignore` and commit it. There is no command that does this
  for you: that file is written once when a project is set up and deliberately never
  rewritten, because rewriting it is how a tuned ignore file gets reset under somebody.
  `ai-eng doctor` names the line to add when it finds receipts without a declaration.

- Three things that used to carry on now stop. The installer refuses to write git's
  configuration when the command line tool it is about to point git at cannot be run — a
  wired repository whose hooks resolve to nothing is worse than an unwired one, because it
  looks configured. `ai-eng uninstall` ends `INCOMPLETE` and lists what it could not place,
  instead of exiting 0 with guards still wired. And the release workflow refuses to publish
  a tag whose commit `origin/main` does not contain, so a tag pushed from any branch can no
  longer ship code the default branch never held. This is the direction the whole framework
  fails in: a guard that cannot decide fails closed, and only telemetry fails open.

- `ai-eng doctor` and the installer now run their own command line tool with `PYTHONSAFEPATH`
  set. Without it, Python puts the current directory at the front of its import path, so a
  repository that happens to contain a folder named `ai_engineering` had *its* copy executed
  by the check that was supposed to be diagnosing it — and could print whatever answer it
  liked. If you keep a package by that name in a repository, the diagnosis now reads the
  installed product instead of yours.

### Changes

- **The pin's model tiers retuned against a live benchmark (dogfooding).** `medium` moves
  from `qwen3.8-flash` to `glm5.3-flash` and `low` from `qwen3.6` to `qwen3.8-flash`,
  measured on 2026-08-27 against `api.nan.builders/v1` (latency, tok/s, tool calling,
  vision, and a ~300K-token needle probe on all six chat models). Build/verify/ship now
  burn the tier with the 500M-token monthly allowance, and research/spec gain vision and
  262K context. `qwen3.6` leaves the tier table (still in the catalog, fastest measured at
  ~129 tok/s); roles outside the three tiers — audio on `mimo-v2.5`, extraction on
  `gemma4`, RAG on `qwen3-embedding` + `rerank` — are documented as pin comments that no
  code reads. Nothing changes for installers: the pin is per-repository, the wheel ships
  no model names, and the framework still never hardcodes one.
- **Model emission, router consumption and the orphan decision (spec 042).** The `[models]`
  section of the pin is no longer a promise with no reader: every `ai-eng` command event now
  records `tier_model` (the model string the pin says the verb routes to, on both the plain
  and `--json` emit paths) and every event carries a `model` field from `AI_ENG_MODEL`
  (or `undetermined` when a surface does not report one; old events read as `missing`). The
  `report digest` answers "how many models, what distribution" with the four states named,
  never merged. The cycle skills name the tier each stage asks for (top for security/review/
  plan/audit, low for research/spec, medium for the rest), pinned against the router. Every
  caller-less module now has exactly one checked status in `policy/module-status.toml`
  (consumer / orchestrator-future / deferred-with-reason), read by `wiring.module_status()`
  and verified by an AST import-graph test that detects new orphans rather than a fixed list.
  And `loop_guard` keeps failing closed but escalates the repeated verdict from the third
  identical denial in a window, naming the call and the person channel instead of re-stating
  the same sentence — its escalation text is capped at the window and control characters in
  signatures and model values are sanitised at the record edge. The router's schema and pin
  now resolve through `paths`, fixing a latent crash when the module was imported from an
  installed wheel. The inherited `madr` red is re-attributed correctly: `MADR_HOME_INVALID`
  from the `specs/*/approval.md` dossiers, not `MADR_SCHEMA_INVALID` from ADR 0025.
- A new skill, `/ai-goal`, runs the whole governed cycle in one pass and stops only to
  hand over: research → spec → challenge → council → build → review → verify → security →
  audit → ship, with the invocation as the standing approval. Two bars, both green and
  neither negotiated: the gate (`ai-eng audit verify`, shown, nothing silenced) and the
  goal (acceptance criteria written into the spec, judged met-or-not by a critic with no
  memory of the builder's reasoning). The loop is bounded — two attempts per task and
  failing recipe, a fixed cap and a no-progress guard, then a page a person can act on —
- Spec 028 records the writer model of `/ai-goal` as a governed decision: today one
  writer — the invoked agent — implements only a spec/plan approved at its exact digest,
  and the four-term formula `1 task = 1 branch = 1 worktree = 1 writer` is the gated
  future P3 target of spec 013, not the current model. The record sits in
  `specs/028-writer-model-recorded/` (spec, plan, challenge, council, blocked page); the
  proposed ADR 0028 that would seal it is gated on `madr.validate`, which this tree has
  red since ADR 0025 of spec 026, and `specs/028-writer-model-recorded/blocked.md` names the approved repair that
  unblocks it. The `ai-goal` corpus gains the refusal «record the writer model as a
  decision» → `/ai-spec`, and the `skill-routing` baseline moves 349→350 with the reason
  written beside it in `policy/pilot-register.toml`.
- A note is now appended to, never rewritten — `contract._appendix_problems` refuses an
  `ai-note` that would edit its history instead of adding a dated finding. Decisions get a
  named framework: `decision_fw` applies RICE, Effort/Value or Kano deterministically, and
  a bare "ranked by impact" with no method is refused. Verdicts get a lens:
  `constellation` reads ≥2 same-class signals in one context as systemic and a lone
  signal as isolated — and it never erases a guard's own fail. The `skill-routing`
  baseline moves 359 → 363 with the reason beside it. Recorded in
  `specs/034-appendix-notes-decision-frameworks-and-constellation`.
- Context is now a budget the framework enforces. `trim_output` keeps head and tail with
  the elided middle marked and **never drops a failure line**; `skillify` turns a costly
  one-off transcript into a contract-clean SKILL.md skeleton (the generalisable steps,
  never the chat); the dispatcher craft rule refuses a body that grew past the tier bound
  because of branches it should have split into `examples/`/`references/`; and
  `verify_against_installed` drops or downgrades a version claim that contradicts the
  installed distribution — never trusted from memory. The `skill-routing` baseline moves
  355 → 359 with the reason beside it. Recorded in `specs/033-context-economy-and-skill-
  authoring`.
- Every shipped skill now answers the four craft questions or the gate refuses it. A
  `SKILL.md` must carry an anti-rationalization table (at least one excuse the agent
  could make to skip the work, answered factually), a `## What it produces` naming the
  exact artifact (a path, a file, a record — not "verify"), Incorrect/Correct pairs for
  every rule it gives, and a body within the load tier (≤500 lines, scripts moved to a
  `scripts/` folder that is executed, never read into context). Recorded in
  `specs/032-standard-skill-craft-contract`.
- Verification output is now a gated DAG, and a loop knows when to stop. `lane_merge`
  orders and gates verification lanes: each node's `verify` command must pass before
  its output feeds the next node (a failed verify leaves the downstream input
  `INCOMPLETE`), and findings are deduped by `(file, line)` with lane conflicts surfaced
  rather than hidden. `loopgate` ends a loop only on **two identical green runs**
  (digest-equal), and a diverged or failed pass restarts the requirement. Specs gain
  `self_contained` — a spec carrying "as we discussed" or "per our conversation" is
  refused — and a deterministic `§N` section resolver. Recorded in `specs/031-
  verification-dag-loop-termination-and-spec-containment`.
- Verification is now cold, and coverage is declared as data. `verify_cold` reads only
  the spec/answer key and the delivered files — never the constructor's conversation,
  never the plan's rationale — with **no write tools**, and "an uncertain check is a
  fail"; every guard whose scan surface can change declares its roots in a
  `policy/coverage/*.toml` per guard (a coverage rule that escapes the declared roots is
  `INCOMPLETE`); and revalidation runs at **finding granularity**, re-executing each
  finding's command independently. Recorded in `specs/030-cold-read-verification-and-
  revalidation`.
  and simplicity (KISS, YAGNI, DRY, SOLID, BDD, TDD, Clean Code, Clean Architecture) is
  the standing bar. It is the gauntlet-loop half of what `ai-cycle` deliberately is not:
  `/ai-cycle` stops at the brief, `/ai-goal` stops at the green gate. The routing
  evaluation's `skill-routing` baseline moves 332 → 347 in `policy/pilot-register.toml`,
  and the commit that moves it is its approval, per the register's own rule.
- The governed cycle's order is now checked data. `policy/skill-sequence.toml` is the one
  copy of which stage follows which — first half `ai-research` → `ai-spec` →
  `ai-challenge` → `ai-council`, a human gate, then `ai-build` → `ai-review` →
  `ai-verify` → `ai-security` → `ai-eng audit verify` → `ai-ship` — with a per-stage
  `fork` marker checked against each SKILL.md's `context: fork` + `background: false`
  frontmatter, and the stage-level parallel refusal recorded as data instead of prose.
  `wiring.next_stage` renders a "Sigue en el ciclo: …" line into the generated `/ai-*`
  routers (the last stage of the first half reads "Sigue: la aprobación humana del
  brief", and a skill outside the cycle carries no line), and `ai-cycle` stops restating
  the numbered list and points at the map. `tests/test_skill_sequence.py` fails the gate
  on a stage that exists nowhere, phases running backwards, a fork flag the frontmatter
  does not carry, an empty gate or a duplicate stage. What changes for you: **a `/ai-*`
  router may now print what follows, regenerating routers changes their bytes once, and
  adding a stage to the cycle means recording it in the map.** Recorded in
  `specs/025-skill-sequence-map`.
- Evidence is now executed, and the answer is decided before a gate runs. The `evals`
  lane plants an independently-graded defect pack (answer key outside the fixture tree)
  and scores each review skill per-skill with recall **and** precision; the `ai-spec`
  flow emits an immutable **answer key** — each observable requirement a binary check
  with `judged_by`, and an unknown observable reports `BLOCKED: U<n>` instead of an
  invented score; verification gains `--recheck`, which ignores claims and re-executes
  the named command against the named digests; and costly lanes get a bounded-sample
  calibration with a `doctor` pre-run. Recorded in `specs/029-evidence-executed-and-
  answer-keys`.
- Rule 1 of `AGENTS.md` now reads "No code before an approved spec and plan", and the
  delivered doctrine matches it: the `AGENTS.md` skeleton `init` writes, the `EP-324`
  ledger subject and the `test_record` docstring that quotes it. The rule had always
  meant both documents — the approval records name a digest for `spec.md` and `plan.md`
  alike — but the short form "approved plan" let the spec pass on a reading of the plan
  alone. The two historical records that quote the older wording (`docs/adr/0016`,
  `specs/024`) are left as written, because an approval record describes the rule as it
  was when it approved that work.
- The shipped skills are now a contract the gate checks. `contract.audit_one` applies
  four rules to every skill pair: portable commands only (an `ai-eng` verb, or a tool
  whose printed output the gate keeps — `just <recipe>`, bare `semgrep`/`gitleaks`/
  `trivy` and `git grep` are replaced), an existence check beside every cross-file
  reference, a forced-output clause in each "Done when", and a source beside every
  statistic — and the sixteen skill pairs are repaired until the audit is green.
  `/ai-research` and `/ai-goal` declare their external tools optional, present-or-
  degraded; the `skill-routing` baseline moves 347 → 349 with the reason beside it in
  `policy/pilot-register.toml`.

## 1.0.0 — 2026-08-10

### Breaking changes

- Events buffered in `.ai/events.jsonl` carry a `stamp`: an HMAC over the event, made with
  a key written 0600 to `~/.ai-engineering/buffer.key`, outside every clone. The flush at
  the end of a session checks it, and a line that does not carry this machine's stamp —
  edited, truncated, or no longer JSON — is sealed into the chain as an `error` reading
  `outcome: edited`, with whatever the line claimed kept beside it under `claimed`, and
  `ai-eng audit verify` names that link and exits 1. It used to be hashed in as genuine, so
  an agent that had just been blocked could rewrite its own denial into an allow and the
  chain still reported intact. The bound, stated plainly: the key is a file readable by
  anything running as you, so this detects a buffer edited by something that did not read
  it and raises the bar against nothing that did — the git anchors are what defend the
  chain against a writer already inside your account. A buffer written before this change
  seals as edited on the first flush after upgrading, and so does every unflushed line if
  that key file is deleted: end your sessions before you upgrade.

- `ai-eng doctor` assertion 9 reports "could not evaluate" instead of a failure when the
  adversarial suite's real-model half has never run on this machine, and still fails when
  it ran and the result is more than seven days old. Never run and gone stale are different
  answers and it gave the second for both — and nothing on a runner or a fresh machine can
  write that field, because that half needs an API key and somebody's spend, which is a
  risk this repository accepted and dated. So `ai-eng doctor --ci` could not pass anywhere,
  which is what the first CI run on this branch reported. Not evaluated is still never
  green: it is printed, counted separately, and says what it could not ask.

- Every verb now writes UTF-8 with replacement rather than whatever encoding the shell
  handed it. On Windows a bare `print()` gets a cp1252 stream, and the tick in `ai-eng spec
  new`'s success line is not in cp1252, so that verb ended in a `UnicodeEncodeError`
  traceback with the spec already written — work done, crash reported. The styled screens
  were never affected, which is why this survived every local run.

- The `.github/workflows/check.yml` that `ai-eng init` writes gets `just` with
  `uv tool install rust-just` instead of the `extractions/setup-just` action. A repository
  that restricts which actions may run — GitHub's "allow select actions" — never starts a
  workflow naming one outside its list, and the failure has no job and no log to read. The
  uv this file already sets up is enough. Nothing changes for a repository that allows all
  actions; re-run `ai-eng init --project` to take the new file, or delete the one line.

- The dated backup `ai-eng init` writes before it overwrites one of your files now lands in
  `.ai/backups/` instead of beside the original. At the repository root nothing ignored
  those files, no verb removed them and `git add -A` committed them; the managed
  `.ai/.gitignore` ignores everything under `.ai/` and a `.gitignore` cannot reach out of
  its own directory, so the file moved rather than the ignore widening. `uninstall` touches
  nothing under `.ai/`, so the recovery path still outlives the framework. Backups written
  before this change stay where they are and are still yours to delete.

- `ai-eng doctor --fix` no longer runs `ai-eng update`. Assertion 12 still names that
  command when the wheel and the pin disagree, and still prints it, but `--fix` runs its
  cures with nobody in front of them and `update` asks for a typed `y` before it migrates:
  at a terminal the repair stopped in the middle and waited for a keystroke, and with no
  keyboard `update`'s own refusal exited 1, took the rest of the repair with it and skipped
  the second diagnosis. Whether the pin moves is a person's decision, which is what that
  question is for. Run `ai-eng update` yourself; `--fix` now counts assertion 12 under
  "needs a person" instead of under "fixable now".

- A JSON file this tool has to read and cannot parse now stops the verb with the file
  named and exit 2, where it used to be read as an empty document. Two things were losing
  data behind that: `wiring.record` read the install receipt, appended and wrote, so one
  interrupted write emptied the record of every file this tool had installed; and the
  settings writers read, merged and wrote back, so a `~/.claude/settings.json` carrying a
  `//` comment — which VS Code and Cursor write as a matter of course — was replaced by our
  hooks block alone. A file that is simply absent still reads as empty. If a verb now
  refuses, the named file is unparseable and nothing was written.

- `ai-eng uninstall` removes the skills store at `~/.ai-engineering/skills`, prints one
  line per row in the receipt including the reason for anything it keeps, and retracts what
  it removed from the receipt. It used to list every row, ask "Remove them?", and run a loop
  with branches for two of the five kinds — so the store and every repository row survived
  with no line printed, and the record still claimed all of them afterwards. It exits 1 when
  it could not change a file, instead of 0.

- `ai-eng uninstall --project` no longer touches repositories other than the one you are
  standing in. It compared recorded paths by string prefix, so `~/repos/app` reached
  `~/repos/app-backup`. Repositories in the receipt that are not this one are named with the
  command to run inside each.

- `ai-eng update` rewrites the guard entries the receipt records as chosen, not every
  surface it can detect, and records what it writes. Declining a surface at `ai-eng init`
  and running `update` later used to wire it — Cursor with `failClosed: true` — with no
  receipt row, so `uninstall` could not find it afterwards. On a machine with no recorded
  guard entry, `update` now writes none and names `ai-eng init --global`.

- `ai-eng init --project` no longer rewrites `.ai/config.toml` or `.ai/.gitignore`. It
  writes them when they are absent, says on its own line which one it left alone, and
  names `ai-eng update` as the only verb that changes the pin. It used to rewrite both on
  every run — taking a dated backup and printing a line — which reset the pinned version,
  the guard windows and the observability endpoint on every re-run, and made `ai-eng
  update`'s three consent gates reachable around. If you were re-running `init` to refresh
  the pin, run `ai-eng update`: it refuses on a dirty tree, refuses without a keyboard, and
  asks for a typed `y`.

- `ai-eng init` no longer prints `.github/workflows/check.yml` at you to paste. It writes
  the file, which means it is offered for overwrite like the other four when one is already
  there, and it lands in the receipt, so `ai-eng uninstall` removes the one we wrote and
  leaves the one you wrote. There is no flag to get the old paste-it-yourself behaviour
  back.

- `ai-eng accept` now requires `--by` and `--justification`. It used to write
  `TODO: a person, by name` and `TODO: why this is acceptable, in one sentence` into the
  record when they were omitted, and assertion 16 compared only the expiry date — so an
  accepted risk with no owner and no reason passed every gate this product has. An
  omitted `--follow-up` is now an empty field rather than a third marker. There is no
  shim and no deprecation period: the command exits 2 and names the four flags it needs.

- What makes a hook entry ours is now the dispatcher's own filename, `chain.py`, and no
  longer the hyphenated project name. The old mark could only reach an entry through the
  interpreter's path, which spells this package with an underscore under a wheel, so it
  worked under `uv tool` and `pipx` and was false everywhere at once under `pip` into a
  venv named anything else. If you installed that way, `ai-eng init` has been writing a
  duplicate guard entry on every run and `ai-eng uninstall` has been leaving your guards
  wired; run `ai-eng init --global --no-project` once after upgrading and both stop. There
  is no dual-marker fallback: entries written before 1.0.0 are recognised by the new
  signature because the dispatcher's path was always in them.

- `ai-eng spec new --ref` no longer prefills the spec. The flag still records the work
  item in the frontmatter and `/ai-ship` still closes it, but the heading is the slug and
  the problem statement is the author's to write. Nothing fetches the work item any more.
