---
spec: spec-183
slug: cli-help-visual-grouping
title: spec-183 — CLI command audit + functional color-grouped help
status: approved
effort: large
branch: main
target_dispatch: /ai-autopilot
summary: Prune 3 stale CLI commands, fix 4 docstring bugs, rewrite the stale cli-reference.md (canonical + template mirror), add deprecation notices to 9 low-signal commands, then group ai-eng --help into 4 color-coded functional panels (Lifecycle/Governance/Inspection/Maintenance). All claims live-verified.
---

## Summary

`ai-eng --help` renders one flat, uncategorized panel of 24 top-level
commands, giving an operator no visual signal for which command solves
their problem (the trigger: a side-by-side comparison against `bun
--help`, which groups commands by function with a distinct color per
group). Investigating that redesign surfaced a bigger, prior problem:
a parallel audit across all 24 visible top-level command groups found
confirmed dead/duplicate commands, factually wrong docstrings, and a
canonical reference doc (`.ai-engineering/reference/cli-reference.md`)
that is silent on 11 live top-level commands and documents 6
commands/flags that no longer exist. Coloring a command surface that
is simultaneously stale and inaccurately documented would not achieve
the operator's actual goal — "que el humano pueda identificar mejor
qué usar y cómo" (a human can better identify what to use and how).
This spec prunes and corrects the command surface first (Phase 1),
then applies the color-grouped redesign over the corrected surface
(Phase 2).

Every factual claim below was verified against the live `create_app()`
command tree by a 7-agent parallel evidence sweep before this spec was
finalized; file:line evidence is carried in the References section and
the Decisions. Where the original audit was wrong (the `release`-hide
mechanism, the "pure redirect" framing of two deletions, a THEME key
count, the `--help` interception point), the spec has been corrected
to match reality rather than restate the audit.

## Goals

### Phase 1 — Audit & correctness (gates Phase 2)

1. Hard-delete `spec activate` (hidden alias, `cli_factory.py:594`),
   `maintenance branch-cleanup` (`maintenance.py:141`), and
   `maintenance spec-reset` (`maintenance.py:300`) — each removed-verb
   invocation prints `removed; use <replacement>` and exits 2 (same UX
   contract as spec-132 D-132-02..05). Replacements: `spec start`,
   `cleanup branches`, `cleanup specs`. The deletion also removes/updates
   the direct unit test `tests/unit/test_spec_cmd.py::TestSpecActivate`
   and the two stale src docstring references to `spec activate`
   (`spec_cmd.py:5`, `core/cli/decorators.py:46`). Per D-183-02 the two
   `maintenance` deletions are NOT capability-equivalent redirects
   (see that decision); `CHANGELOG.md` `### Breaking changes` names all
   three commands, their replacements, AND the two dropped behaviors
   (auto base checkout+pull; standalone live-buffer reset).

2. `release` is reclassified as framework-internal: registered with an
   unconditional `hidden=True` in `cli_factory.py:431` (mirroring the
   `dev` and `internal` groups), removing it from `--help` in every
   install while keeping it fully invocable (`hidden` ≠ disabled — a
   maintainer can still run `ai-eng release`). It is also dropped from
   the JSON command list at `cli_factory.py:220`. NO conditional
   source-repo detection is built (see D-183-03 — the mechanism the
   original audit assumed does not exist).

3. Confirmed docstring/help-text bugs are fixed (behavior unchanged,
   text corrected), each verified against live code:
   - `setup {github,sonar,azure-devops}`: three `success("State saved
     to install_state table")` strings (`setup.py:194,299,387`) plus
     three `# … (state.db singleton row)` comments (`setup.py:187,286,
     376`) reference a DB table that does not exist in the files-only
     model — reworded to name the real store.
   - `doctor --check`: the `--check` option help (`core.py:1378`) and
     the `doctor_cmd` docstring (`core.py:1388-1389`) still advertise a
     `state-db` value, but the dispatcher (`core.py:1420-1436`) supports
     only `hot-path` and raises `BadParameter` on `state-db` (spec-148
     removed the underlying check). The dead value is removed from both.
   - `cleanup branches --reset`: the help `"Force re-sync to remote
     state."` (`cleanup.py:233`) is inaccurate — the path is an
     observation-only alias of `--untracked` (`cleanup.py:212-215`). The
     help is corrected to describe the real behavior.
   - `gate pre-push` / `gate risk-check`: `gate_pre_push`'s docstring
     (`gate.py:124`) omits that the body also runs the Article VII
     no-suppression gate (`_run_no_suppression`, exits 1) and a
     `strict=True` inline risk check that blocks on expired AND
     expiring-soon acceptances (`gate.py:126,131-132`). `gate_risk_check`
     under-discloses `--strict` (`gate.py:230` docstring + `gate.py:224`
     option help) which fails on expiring-soon in addition to expired
     (`return bool(expired or (strict and expiring))`, `gate.py:214`).
     Both docstrings are corrected to disclose full enforcement scope.

4. `.ai-engineering/reference/cli-reference.md` is rewritten from a
   systematic pass over the live `create_app()` command tree, and the
   byte-parity template mirror
   `src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md`
   is regenerated in lockstep (the mirror still documents the deleted
   commands at `:110-118` — both must be corrected or consumer installs
   ship the stale doc). The rewrite adds the 11 undocumented live
   top-level surfaces (`verify`, `status`, `commit`, `pr`, `host`,
   `cleanup`, `decision`, `ownership`, `risk`, `spec`, `plan`) and
   removes/fixes the 6 phantom/wrong entries (`audit index`, `audit
   query`, `audit otel-export`, `config ide list`, `config provider
   list`, the wrong bare-`config` description → `config surface` /
   `config reconfigure`). Verified by a new lightweight test
   (`tests/unit/docs/test_cli_reference_parity.py`) asserting every
   non-hidden top-level command name registered in `create_app()`
   appears at least once in `cli-reference.md` — a coarse but
   CI-enforced parity floor, not just manual review.

5. A one-line, non-blocking stderr deprecation notice (suppressed in
   `--json` mode) is added to the 9 confirmed-live low-signal
   commands: `commit` (`cli_factory.py:433`), `status` (`:432`),
   `verify` (bare/default path only — NOT the `--release` subflag,
   `:419`), `ownership import` (`:551`), `issue sync` (`:615`), `spec
   show` (`:597`), `pr` (`:434`), `maintenance pr` (`:501`),
   `maintenance reset-events` (`:506`). Each notice names the low-usage
   signal found and, where one exists, the suggested alternative.

6. Full existing test suite stays green. New/updated tests cover: each
   deletion's `removed; use X` contract, removal of
   `TestSpecActivate`, each new deprecation notice (stderr-only,
   JSON-suppressed), and each corrected docstring/help string.

### Phase 2 — Functional color grouping (depends on Phase 1)

7. `ai-eng` (bare invocation) AND `ai-eng --help` both render 4
   titled, distinctly-bordered/colored panels — **Lifecycle**,
   **Governance**, **Inspection**, **Maintenance** — built by ONE
   shared custom renderer driven by a single `{command: category}`
   map. The two entry paths differ (D-183-06): the bare path is hooked
   at `cli_factory.py:236` inside `_app_callback`; the explicit
   `--help` path (Click's eager `--help`, which fires before the
   callback body) is hooked via the existing `SmartTyperGroup`
   (`cls=SmartTyperGroup`, `cli_factory.py:401,412`). Both converge on
   the same render function.

8. Subcommand `--help` screens (e.g. `ai-eng risk --help`) are
   unchanged — Typer's native rendering, no cascading color.

9. `NO_COLOR`, `TERM=dumb`, non-TTY, and `--json` output paths are
   provably unaffected (existing + new golden tests).

10. The palette reuses 3 of the existing 9 semantic tokens (`cli_ui.py`
    `THEME`, keys: `brand`, `brand.dim`, `success`, `warning`, `error`,
    `info`, `muted`, `path`, `key`) — brand teal (`BRAND_TEAL =
    "#00D4AA"`) for Lifecycle, `info` blue for Inspection, `muted` grey
    for Maintenance — plus one NEW violet token for Governance (no
    violet/purple token exists in THEME today). No color is the sole
    carrier of meaning; the panel title (text) is the primary signal in
    every case.

## Non-Goals

1. No change to subcommand-level `--help` styling — confirmed scope is
   the top-level listing only (matches observed `bun info --help`
   behavior: subcommand screens get Typer's own default flag/option
   coloring, not the parent's category hue).
2. No blanket hard-delete of the 9 "Bucket 4" commands in goal 5 —
   deprecation notice only, pending real external-usage signal. No
   backwards-compat *shim* is created either; the notice is new,
   additive, honest text, not a redirect.
3. No new CLI framework — stays on Typer; the Phase 2 renderer is an
   additive interception at the existing bare/`--help` root paths, not
   a replacement of Typer's formatter.
4. No fix for `doctor_hot_path.py`'s overrun advisory-to-blocking
   sunset date (verified ~6 weeks overdue during the audit, unrelated
   to command-surface pruning) — raised in Open Questions as its own
   follow-up.
5. No resolution of the 3 parallel "open a PR" implementations
   (`ai-eng pr`, the `/ai-pr` skill's own inline `gh`/`az`
   composition, `ai-eng maintenance pr`) beyond the deprecation notices
   in goal 5 — full consolidation is a follow-up spec.
6. No major semver bump — treated as a MINOR version bump, consistent
   with spec-132's precedent for pre-1.0 hard renames/removals.
7. No 5th visible category — `dev`, `internal`, and (per D-183-03)
   `release`, plus the 8 hidden removed-verb tombstones, stay in the
   hidden set, not a new "Framework maintainers only" panel; they are
   excluded from the Phase-2 taxonomy and its golden test (R-183-03).
8. No re-plumbing of the source-repo detector. The real `_is_source_repo`
   file-existence helper (`validator/_shared.py:201-203`) stays where it
   is (validator-only); this spec does NOT wire it into CLI visibility.

## Decisions

### D-183-01 — One spec, two gated phases, not two specs

**Choice**: This single spec covers both the audit/correctness pass and
the visual redesign, with Phase 1 gating Phase 2.
**Rationale**: Operator explicit instruction after reviewing the first
rendered mockup: "un solo spec: expandir spec-183 para incluir la
auditoría completa antes de tocar colores." Coloring a category map that
Phase 1 is about to change (deleting subcommands, hiding `release`)
would mean building the panel mapping twice. Confirmed still correct by
the evidence sweep: the taxonomy in D-183-08 depends on `release`'s
final visibility (D-183-03) and on the deletions in D-183-02.

### D-183-02 — Hard-delete 3 commands; two are NOT pure redirects (verified)

**Choice**: `spec activate`, `maintenance branch-cleanup`, `maintenance
spec-reset` are removed entirely, zero deprecation window, per the same
"removed; use `<new>`", exit 2 contract as spec-132 D-132-02..05.
Replacements: `spec start`, `cleanup branches`, `cleanup specs`. The
evidence sweep corrected the original "zero callers / pure redirect"
framing — deletion proceeds anyway, and `CHANGELOG.md` documents the two
behavior drops.
**Rationale**: All three cleared the deletion bar (self-declared-expired
shim or "legacy singleton"/"compatibility buffer" self-description; a
shipping replacement command). The audit's stronger claims were
falsified and are corrected here so the plan is honest:
- `spec activate` is NOT caller-free: it retains a dedicated unit test
  (`tests/unit/test_spec_cmd.py::TestSpecActivate`) and two src docstring
  references (`spec_cmd.py:5`, `core/cli/decorators.py:46`) — all removed
  as part of the deletion. It has no skill/doc/workflow caller. Its body
  is a pure alias to `spec_start`, so the redirect IS capability-equal.
- `maintenance branch-cleanup` is NOT caller-free (a CLI test, an
  internal repo-status suggest-next string at `maintenance.py:281`, and
  the shipped `cli-reference.md:110-113`). Its replacement `cleanup
  branches` deletes merged/squashed/stale/untracked branches but does
  NOT replicate the auto base checkout + `pull --ff-only`
  (`branch_cleanup.py:297-306`) — an undisclosed working-tree side
  effect that `cleanup branches` deliberately lacks. Per operator
  decision (2026-07-13), dropping that auto base-sync is a net risk
  reduction (it is the "footgun" side effect), NOT a capability we
  preserve; CHANGELOG documents the drop.
- `maintenance spec-reset` is NOT caller-free (`maintenance all` invokes
  the underlying `run_spec_reset` at `maintenance.py:577`; unit +
  integration tests; `cli-reference.md:117-118`). Deleting the standalone
  COMMAND keeps the `run_spec_reset` impl (still used by `maintenance
  all`, which is out of scope for deletion). Its redirect `cleanup specs`
  only consolidates already-SHIPPED sidecars and does NOT clear the live
  `spec.md`/`plan.md` buffer or drop the work-plane pointer — that
  live-buffer reset now lives in `mark_shipped` and in `maintenance all`.
  Per operator decision, the standalone buffer-reset command is dropped;
  CHANGELOG names `maintenance all` as the full-parity path and `cleanup
  specs` as the common-case redirect.

CONSTITUTION.md Hard Rule 3 (no backwards-compat shims) applies: hard
delete, CHANGELOG documents the breakage AND the two dropped behaviors.

### D-183-03 — `release` hidden unconditionally (mirror dev/internal), NOT via a source-repo gate

**Choice**: Register `release` with a literal unconditional
`hidden=True` in `cli_factory.py:431`, exactly as the `dev` and
`internal` groups are hidden. Do NOT build any conditional source-repo
detection.
**Rationale**: The original audit's premise — "reuse the existing
`pyproject.toml [tool.aiengineering.source_repo]` mechanism already used
for `dev`" — was REFUTED by the evidence sweep and is discarded:
- No `[tool.aiengineering.source_repo]` key exists anywhere in the repo.
  The only reference to it is a stale, aspirational docstring in
  `cli_commands/dev.py:5-7` describing wiring that was never built.
- `dev` is NOT conditionally hidden. It carries a hardcoded
  `hidden=True` on both the Typer group and the `add_typer` call
  (`cli_factory.py:623,626`) — it is hidden in the source repo too, not
  just in consumer installs.
- The only real source-repo detector is a FILE-EXISTENCE check
  (`_is_source_repo` → `(target/"src"/"ai_engineering"/"templates").is_dir()`,
  `validator/_shared.py:201-203`), used only by the validator and NOT
  wired into CLI visibility.
Since `hidden=True` in Typer suppresses a command from `--help` while
leaving it fully invocable, an unconditional `hidden=True` satisfies the
goal ("hidden from `--help` in consumer installs") with a one-line change
and zero new abstraction (KISS/YAGNI/DRY). Operator-approved
(2026-07-13). The marginal loss — `release` no longer appears in the
source repo's own `--help` — is acceptable: maintainers who publish
releases already know the command exists and can still run it. Building
a conditional `_is_source_repo` wire-up into `cli_factory` for that
marginal benefit was explicitly rejected.

### D-183-04 — Bucket-4 commands get a deprecation notice, not deletion, this release

**Choice**: `commit`, `status`, `verify` (bare path only), `ownership
import`, `issue sync`, `spec show`, `pr`, `maintenance pr`, `maintenance
reset-events` print a one-line, non-blocking stderr notice on invocation
(not at `--help` time), naming the low-usage signal and, where
applicable, the suggested alternative. All 9 targets were verified to
exist as live commands/subcommands by the evidence sweep.
**Rationale**: Operator decision after reviewing the full parallel audit.
This repo's internal evidence (tests, skills, docs) cannot rule out
external consumer usage of a public PyPI package's CLI — the audit's own
stated caveat. A visible, honest deprecation warning is the responsible
middle ground between silently keeping known-questionable commands
indefinitely and hard-deleting on internal-only evidence, and it gives
real signal (issue reports, if anyone depends on them) before a future
spec revisits deletion.

### D-183-05 — `cli-reference.md` gets a full rewrite (canonical + template mirror), not incremental patches

**Choice**: Regenerate BOTH the canonical
`.ai-engineering/reference/cli-reference.md` and its byte-parity template
mirror `src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md`
from a systematic pass over the live `create_app()` registration tree,
rather than patching the confirmed errors in isolation.
**Rationale**: The evidence sweep confirmed the doc covers only ~13 of 24
live top-level commands (~54%), is silent on 11 (`verify`, `status`,
`commit`, `pr`, `host`, `cleanup`, `decision`, `ownership`, `risk`,
`spec`, `plan`), and is actively wrong in 6 places (phantom `audit
index`/`query`/`otel-export`; phantom `config ide list`/`provider list`;
incorrect bare-`config` description). Patching only the sampled errors
risks leaving the same error class in whatever the audit did not read
closely. The template mirror is a separately-installed twin (memory:
template mirror parity has no CI guard) that still documents the deleted
commands — regenerating only the canonical would ship the stale doc to
consumers. This directly serves the operator's original goal — a human
should be able to trust this file to know "qué usar y cómo."

### D-183-06 — Top-level `--help` gets a custom renderer hooked at TWO paths (Approach A, corrected)

**Choice**: Hand-build 4 Rich panels from one `{command: category}` map,
rendered by a single shared function, hooked at BOTH root entry paths:
the bare invocation via `_app_callback` (`cli_factory.py:236`, the
existing `typer.echo(ctx.get_help())` site), and the explicit `ai-eng
--help` via the existing `SmartTyperGroup` (`cls=SmartTyperGroup`,
`cli_factory.py:401,412`). Subcommand `--help` stays untouched.
**Rationale**: Operator-approved after reviewing 3 approaches and a
rendered mockup (`ai-eng-help-mockup.svg`). The evidence sweep confirmed
Typer's `STYLE_COMMANDS_PANEL_BORDER` (`= "dim"`) and
`STYLE_COMMANDS_TABLE_FIRST_COLUMN` (`= "bold cyan"`) are module-level
globals in `typer.rich_utils` read directly by `_print_commands_panel`
(`rich_utils.py:487,527`), so native `rich_help_panel=` grouping cannot
carry a distinct per-panel color without transient global mutation
(rejected: fragile across Typer upgrades) or a full custom Click/Rich
formatter (rejected: would restyle every subcommand's help, breaking
Non-Goal 1). It ALSO corrected the original single-hook assumption:
`_app_callback` only fires on the BARE `ai-eng` invocation — Click's
eager `--help` prints during group parameter parsing, before the
callback body runs. Covering `ai-eng --help` therefore requires the
`SmartTyperGroup` hook in addition to the bare-path hook. Both call the
same render function, so there is one source of truth for the panels.

### D-183-07 — Category palette reuses 3 of 9 existing semantic tokens + 1 new token

**Choice**: Lifecycle = existing `BRAND_TEAL` (`#00D4AA`, `cli_ui.py:29`);
Inspection = existing `info` blue token; Maintenance = existing `muted`
grey token; Governance = one NEW violet token (e.g. `#A78BFA`), added to
`cli_ui.py`'s `THEME` dict alongside the existing 9 keys.
**Rationale**: "Dominant colors with sharp accents outperform timid,
evenly-distributed palettes" (design direction) — reusing 3 of the
existing tokens keeps this cohesive with the CLI's restrained brand
identity instead of an arbitrary rainbow. The evidence sweep corrected
the key count: `THEME` (`cli_ui.py:31-41`) has 9 keys (`brand`,
`brand.dim`, `success`, `warning`, `error`, `info`, `muted`, `path`,
`key`), not 8, and confirmed no violet/purple token exists today (so
Governance's token is genuinely additive). The panel title (text) is
always the primary grouping signal; color is reinforcement only, never
the sole indicator (accessibility gate S1).

### D-183-08 — 4-category taxonomy over the 24 visible commands; hidden set excluded

**Choice**: **Lifecycle** (`install`, `update`, `doctor`, `check`,
`verify`, `gate`, `config`, `setup`, `commit`, `pr`, `version`);
**Governance** (`spec`, `plan`, `decision`, `risk`, `issue`,
`ownership`, `audit`); **Inspection** (`status`, `host`, `skill`);
**Maintenance** (`maintenance`, `cleanup`). Hidden set (NOT a visible
panel, excluded from the taxonomy and its golden test): `dev`,
`internal`, `release` (now hidden per D-183-03), and the 8 removed-verb
tombstones (`validate`, `work-item`, `stack`, `ide`, `provider`, `vcs`,
`workflow`, `sync`).
**Rationale**: Operator-confirmed mapping (2026-07-06). The evidence
sweep confirmed there are exactly 24 visible top-level commands and that
these 4 buckets partition 23 of them cleanly; the 24th, `release`, is
moved into the hidden set by D-183-03 (the original taxonomy wrongly
filed `release` as hidden while it was still visible — that
contradiction is now resolved by actually hiding it). The 8 removed-verb
tombstones (`cli_factory.py:644-645`, `_REMOVED_VERBS` map `:358-367`)
are registered `hidden=True` stubs that belong in no functional bucket;
the golden test (R-183-03) must exclude both the hidden groups and the
tombstones, iterating only visible non-tombstone commands. This extends
the Lifecycle/Inspection/Maintenance split from the (draft,
spec-132/133-consumed) `cli-ux-overhaul-brief.md` with a 4th "Governance"
bucket that draft lacked.

## Risks

### R-183-01 — Deleting 3 commands breaks external consumer automation with zero warning

**Risk**: Per Hard Rule 3, no compat shim ships — any downstream repo
scripting `ai-eng maintenance branch-cleanup` or `ai-eng maintenance
spec-reset` in CI breaks on the next `pip install --upgrade`. The
evidence sweep additionally showed the two `maintenance` replacements do
LESS than the deleted commands, so a consumer relying on the auto
base-sync or the standalone live-buffer reset loses that behavior, not
just the command name.
**Mitigation**: (a) `CHANGELOG.md` `### Breaking changes` is the
contract, naming the exact replacement inline AND explicitly listing the
two dropped behaviors (auto base checkout+pull; standalone live-buffer
reset → use `maintenance all`). (b) The removed-verb invocation prints
`removed; use <new>` with the replacement on the same line — no docs
lookup required. (c) A MINOR version bump signals the change, consistent
with this repo's own precedent for pre-1.0 hard renames (spec-132 →
v0.7.0).

### R-183-02 — Deprecation notices add stderr noise to automation parsing `ai-eng` output

**Risk**: A CI script piping e.g. `ai-eng status` output may see
unexpected stderr lines.
**Mitigation**: (a) Notice is stderr-only, never stdout — matches this
CLI's existing message/data separation (`cli_ui.py`: "All messaging goes
to stderr; data goes to stdout"). (b) Suppressed in `--json` mode,
mirroring the existing `is_json_mode()` gating pattern already used for
the update-available notice. (c) One line, shown once per invocation,
not repeated per sub-step.

### R-183-03 — Custom help renderer drifts from the real command tree over time

**Risk**: The `{command: category}` map is hand-maintained; a future
command added without a matching map entry either breaks the renderer or
silently renders miscategorized. The evidence sweep confirmed the live
tree already contains categories the naive "every registered command"
rule would trip on: `release` (visible→now hidden) and 8 hidden
removed-verb tombstones.
**Mitigation**: (a) Fail-open by design — any VISIBLE non-tombstone
command missing from the map renders in a catch-all, dim "Other" panel
instead of crashing or silently disappearing, so a forgotten mapping is
visible noise, not a silent gap. (b) A golden-snapshot test asserts every
VISIBLE non-tombstone command registered in `create_app()` appears in
exactly one category — explicitly excluding `hidden=True` groups
(`dev`, `internal`, `release`) and the `_REMOVED_VERBS` tombstones — so
CI fails loud the moment the map and the live visible surface diverge
without false-flagging the hidden set.

### R-183-04 — `cli-reference.md` drifts stale again after this rewrite

**Risk**: A hand-written doc, however accurate today, is exactly the
failure mode this spec is fixing — nothing structurally prevents the next
added/renamed/removed command from silently going undocumented again. The
sweep also showed the doc has a separately-installed template twin with no
CI parity guard, doubling the drift surface.
**Mitigation**: Goal 4 ships a coarse top-level-name-presence parity test
now (mirroring R-183-03's live-tree assertion). A fully generated and
verified reference doc, and a template-mirror parity guard, are out of
hard scope — captured in Open Questions with a concrete recommendation.

## References

- doc: .ai-engineering/reference/cli-reference.md (Phase 1 rewrite target; ~13/24 coverage, 6 phantom entries)
- doc: src/ai_engineering/templates/.ai-engineering/reference/cli-reference.md:110-118 (template mirror — still documents deleted commands; regenerate in lockstep, D-183-05)
- doc: src/ai_engineering/cli_factory.py:181-272 (`_app_callback`; bare-path help render at :236; SmartTyperGroup at :401,412; command tree :415-616; JSON list :220)
- doc: src/ai_engineering/cli_ui.py:29-41 (`BRAND_TEAL` :29; `THEME` 9 keys :31-41; palette extension site)
- doc: src/ai_engineering/cli_commands/maintenance.py:141,300,577 (`branch-cleanup` / `spec-reset` deletion targets; `maintenance all` internal `run_spec_reset` caller)
- doc: src/ai_engineering/maintenance/branch_cleanup.py:297-306 (auto base checkout + `pull --ff-only` side effect that `cleanup branches` lacks)
- doc: src/ai_engineering/maintenance/spec_reset.py:237,296-308 ("compatibility buffer"/"legacy singleton" self-description; live-buffer clear + pointer drop)
- doc: src/ai_engineering/cli_commands/cleanup.py:212-215,233 (`--reset` observation-only alias; help-text fix target; `branches`/`specs` replacements)
- doc: src/ai_engineering/cli_commands/spec_cmd.py:5,190-191 (`spec activate` deletion target + stale docstring ref; `spec show` deprecation target :597)
- doc: tests/unit/test_spec_cmd.py::TestSpecActivate (unit test to remove with the `spec activate` deletion)
- doc: src/ai_engineering/core/cli/decorators.py:46 (second stale `spec activate` docstring reference)
- doc: src/ai_engineering/cli_commands/release.py:33 (D-183-03 hide target; help is "Create a governed release…", NOT "sole authority")
- doc: src/ai_engineering/cli_commands/dev.py:5-7 (stale aspirational `[tool.aiengineering.source_repo]` docstring — mechanism never built)
- doc: src/ai_engineering/validator/_shared.py:201-203 (`_is_source_repo` real detector — file-existence, validator-only, NOT wired into CLI; Non-Goal 8)
- doc: src/ai_engineering/cli_commands/setup.py:187,194,286,299,376,387 (docstring/comment fix targets — stale install_state/state.db strings)
- doc: src/ai_engineering/cli_commands/core.py:1376-1436 (`doctor --check` state-db help/docstring fix; dispatcher supports only hot-path)
- doc: src/ai_engineering/cli_commands/gate.py:124,214,222-231 (`pre-push` / `risk-check` docstring fix; Article VII + strict expiring-soon scope)
- doc: src/ai_engineering/cli_commands/doctor_hot_path.py:7,14-16,181 (Open Question 1 — advisory→blocking sunset 2026-05-31, ~6wk overdue)
- doc: src/ai_engineering/cli_commands/pr.py + .claude/skills/ai-pr/SKILL.md + maintenance.py:86-120 (Open Question 2 — 3 parallel PR implementations)
- doc: .venv/lib/python3.12/site-packages/typer/rich_utils.py:55,64,487,527 (STYLE_* module globals — D-183-06 feasibility)
- doc: .ai-engineering/specs/archive/spec-132-cli-ux-overhaul/spec.md (precedent: hard-rename UX contract, Renderer architecture)
- doc: .ai-engineering/specs/drafts/cli-ux-overhaul-brief.md (superseded draft; origin of the 3-way taxonomy this spec extends)
- doc: CHANGELOG.md (breaking-change + behavior-drop entries target)

## Open Questions

1. `doctor_hot_path.py`'s self-declared advisory-to-blocking sunset date
   (2026-05-31, `doctor_hot_path.py:7,14-16`) is confirmed ~6 weeks
   overdue and was never actioned in code (`run_hot_path_check` never
   raises `typer.Exit`), tests (`test_doctor_hot_path.py:119-120` still
   asserts exit 0 on violation), or docs/CHANGELOG. Out of scope here (a
   gate-policy enforcement question, not a command-surface question) —
   recommend a dedicated follow-up spec/issue.
2. The 3 parallel "open a PR" implementations are confirmed distinct:
   `ai-eng pr` and `ai-eng maintenance pr` both route through the Python
   VCS provider abstraction (`get_provider().create_pr`), while the
   `/ai-pr` skill shells out to `gh`/`az` directly; `maintenance pr` has
   a distinct payload (a maintenance report). This spec only adds
   deprecation notices to 2 of 3. Recommend a follow-up spec to decide
   consolidation — with the `/ai-pr` skill (the canonical delivery-chain
   step) as the likely survivor and a replacement path for the
   maintenance-report payload.
3. R-183-04: Goal 4 ships a coarse top-level-name-presence test plus a
   lockstep template-mirror regeneration now; recommend a follow-up spec
   deepening it to (a) subcommand- and flag-level parity and (b) a
   CI-enforced canonical↔template mirror parity guard, so this class of
   drift cannot recur silently at any depth or in either copy.
