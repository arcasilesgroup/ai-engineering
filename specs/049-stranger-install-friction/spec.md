---
id: "049"
slug: stranger-install-friction
status: draft
date: 2026-08-29
ref: ""
supersedes: ""
---

# Stranger install friction

## Who this is for, and what it is worth to them

The stranger who installs this wheel on a fresh machine — the customer report 026 asked
about (`.ai/reports/026-stranger-install-evidence.html`). Running the exact documented
command in a clean HOME and repo today, that person hit two refusals whose printed advice
could not be followed to a fix, and would leave the install with a repairable FAIL that
`doctor` says `ai-eng init` fixes but `ai-eng init` cannot. Each costs the same thing:
the product's core promise is that a refusal names its remedy, and a refusal with an
advice that does not work is this product doing the thing it exists to refuse.

## Context and problem

What is true today, each fact measured on 2026-08-29 in the live sandbox run behind
report 026:

- **A refusal that names no symlink.** `init` refuses a repository whose path crosses a
  symlink with "check that no directory in the path is a symlink" (`init.py:868-871`) but
  does not name *which* component. The sandbox run hit it twice on macOS before a
  `realpath` fixed it, because `/var` is a link to `/private/var` — a layout no advice to
  "check for a symlink" resolves for a non-coder, and the failing link is one the OS owns
  and the person must not "fix". The refusal is correct (never write through a link);
  the advice is unfollowable.
- **A FAIL whose printed fix does not fix it.** `doctor` assertion 24 says "ai-eng init
  writes them again". It ran, twice today, and wrote nothing: `install_routers` skips any
  skill whose name collides with a foreign directory in the surface's skills root
  (`wiring.py:585-592`), and this machine has a personal `~/.claude/skills/ai-design`
  (real directory, not our symlink). The router for `ai-design` will never land, the
  assertion stays red, and both repair passes (`--global -y`, `--overwrite ai-design.md`)
  reported success while skipping it in silence.
- **The CI denial receipt is deliberately ephemeral** — `test_surface_adapter.py:663`
  forbids `upload-artifact` in that step, with the stated reason that a receipt outliving
  its job is a claim about a machine that no longer exists. Report 026's direction (1)
  ("publish the release receipt so each install has the first row") contradicts an
  enforced contract and needs a decision record, not a silent change.

## Options considered

1. **Name the offender in both messages, and make the skip visible.** The symlink refusal
   prints the first symlinked component and its target. The router skip prints a
   `· skipped (foreign)` line for each skipped skill during `init`, and assertion 24's fix
   text says what actually resolves it — remove or rename the foreign directory, then
   rerun `init`. Cheapest, fixes the followability without touching either invariant.
2. **Auto-resolve: `init` follows nothing but offers `realpath`; `install_routers` writes
   the router anyway beside the foreign skill.** Loses: writing into a root we do not own,
   next to a skill we did not install, is exactly the collision the skip exists to
   prevent, and silently canonicalising a person's repo path turns a safety refusal into a
   convenience the person never chose.
3. **Defer, file as issues.** Loses on the same ground the framework rejects everywhere
   else: a stranger met these today; the advice is wrong *in the product's own words*, and
   "say it in the changelog" is rule 4, not a backlog item.

## Decision

Option 1. Three message-level changes, no invariant moved: the safety refusals keep
refusing, the skip keeps skipping — they only start naming what happened and what a
person can actually do. The ephemeral-receipt contract is untouched by this spec; report
026's direction (1) stays a proposal that must argue with `test_surface_adapter.py:663`
in its own record if anyone still wants it.

## Challenged once

Strongest case this is wrong: these are cosmetic strings in a CLI that has 26 assertions;
the money is in assertion 23 (capabilities unenforced) and this spends a cycle on prose.
The answer: assertion 23 is a build; this is the product's one observable promise — every
refusal names a followable remedy — broken in the exact two places a first-time install
meets it, proven today by two failed commands whose printed advice did not work. A
product that cannot direct its own repair is not ready to be trusted to enforce one.

## Grill

TODO: when a grill round lands, replace this prompt with its declaration on its own
line — `ran: round <n>, <ISO date> — <n> min` — then one `### Q` per question with its
`**A:**` answer beside it, and what it changed. A round that attacked and found nothing
says `nothing checkable failed`. While this prompt stands undeclared, the critic step
reads the grill as not run.

## Council

TODO: when the council pass lands, replace this prompt with its declaration on its own
line — `ran: round <n>, <ISO date> — <n> min` — and name the lenses that read:
`lenses: cost, reversibility, undecidable, trust, example`. The shape below is what the
critic step reads — top-level bullets only, each heading carrying bullets or a literal
`none` line, every finding and every refutation carrying a command. The pass may
conclude; it may not approve.

### Gaps no single lens named

### Findings cut for carrying no command

### Findings the cross-read refuted, with the command that refuted them

### The two counts

- Gaps that appeared only after the cross-read: **N**
- Findings deleted, for carrying no command or for being refuted: **N**

## Assumptions and unresolved risks

- Assumed: no consumer script parses the two refusal strings verbatim; the gate's own
  tests are the only reader and they travel with the change. (Nothing in `tests/` greps
  "cannot be followed safely" today — a rename that broke a parser would be red here.)
- Open risk, unsized: 7 surfaces have no declared command root (surfaces.toml note), so
  the foreign-skill skip can only strand a router on the one surface that has roots today,
  claude-code. If a second root is declared, the silent-skip blast radius grows with it.

## Examples somebody can check

- Given a repository path whose component `/private/tmp` is crossed as a symlink, When
  `ai-eng init --project .` refuses, Then the message names the offending component and
  its target, printed by `ai-eng init` and asserted by
  `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py -k names_symlink`.
- Given a surface whose skills root holds a foreign `ai-design/` directory, When
  `ai-eng init --global -y` runs, Then its output carries a `skipped (foreign): ai-design`
  line and `ai-eng doctor` assertion 24's fix text names removing the foreign directory,
  checked by `uv run --with pytest==9.1.1 pytest -q tests/test_wiring_routers.py -k foreign`
  and the live `ai-eng doctor` line.
- Given a clean machine where every router lands, When `ai-eng init --global -y` runs,
  Then no skip line appears — the clean control, same file, `-k no_foreign_no_skip`.

## Decisions

<!-- One `**D-NNN-NN — <the decision>**` per line, each with a `**Rationale:**` under it.
     Prefix a line with `- [X]` to claim the decision earns promotion: it constrains
     specs that do not exist yet, and `ai-eng decide` promotes only marked lines.
     `ai-eng decide` does not write here: it writes a record under docs/adr/. -->


## Accepted risks

<!-- ai-eng accept writes yaml blocks here -->

## Production-ready

Nothing gets a URL until every box is ticked, and each one is ticked by a command.

- [ ] CI/CD — build, lint, test and security analysis on every push; deploy from the default branch
- [ ] Logs — structured JSON, one line per event, with level and service, to stdout
- [ ] Traces — only if this is our code and has more than one hop; no hop, no trace
- [ ] Errors — every uncaught exception leaves as a log with severity 17 and marks its span
- [ ] Health and data age — alive, age of the newest datum, and an independent recomputation
- [ ] External check — something outside the service verifies it and says what it could not check
- [ ] Second path — every published number recomputed by an independent route and compared
- [ ] Security — secrets sealed, no credential in a plain variable, SAST and dependency audit in CI
