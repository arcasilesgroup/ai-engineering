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

The repository owner on a drifted machine — the one whose install record says a router
exists and whose `ai-eng doctor` says a repair command fixes it, when it cannot — and,
second, the stranger who installs this wheel on a fresh machine and meets a refusal whose
advice points at a symlink the operating system owns. Report 026 measured both in a live
run (`.ai/reports/026-stranger-install-evidence.html`). Each costs the same thing: the
product's core promise is that a refusal names a followable remedy, and advice that does
not work is this product doing the thing it exists to refuse.

## Context and problem

What is true today, each fact measured on 2026-08-29:

- **A refusal that names no symlink.** `init` refuses a repository whose path crosses a
  symlink with "check that no directory in the path is a symlink" (`init.py`, the
  `_project_preflight` refusal) but does not name *which* component. The sandbox run hit
  it twice on macOS before a `realpath` fixed it, because `/var` is a link to
  `/private/var` — a layout no advice to "check for a symlink" resolves for a non-coder,
  and the failing link is one the OS owns and the person must not "fix". The refusal is
  correct (never write through a link); the advice is unfollowable.
- **A FAIL whose printed fix does not fix it, on a drifted machine.** `doctor` assertion
  24 says "ai-eng init writes them again". It ran, twice today on this machine, and wrote
  nothing: `install_routers` skips any skill whose name collides with a foreign directory
  in the surface's skills root (`wiring.py`, the `theirs` set), and this machine has a
  personal `~/.claude/skills/ai-design` (real directory, not our symlink). The challenge
  run bounded who meets this: a *first* install on such a machine records no
  `ai-design` router and 24 is green — the red is for a machine whose router WAS
  recorded and then stranded by a later collision, exactly the dogfood state measured
  today. The skills-folder skip was already printed (since spec 024); the *router* skip,
  which is what keeps 24 red, was silent, and `--overwrite` cannot name a router at all
  (it selects only the five project files).
- **The CI denial receipt is deliberately ephemeral** — `test_surface_adapter.py:663`
  forbids `upload-artifact` in that step, and `:671-676` pins the whole step by a second
  SHA-256 digest; the stated reason is that a receipt outliving its job is a claim about
  a machine that no longer exists. Report 026's direction (1) ("publish the release
  receipt so each install has the first row") contradicts an enforced contract and needs
  a decision record, not a silent change. This spec takes no decision on it.

## Options considered

1. **Name the offender in both messages, and make the skip visible.** The symlink refusal
   prints the first symlinked component and its target. `install_routers` reports every
   skip it makes — foreign folder or unrecorded file — through one callback, and `init`
   prints a `skipped (foreign)` line. Assertion 24's fix text says what actually resolves
   a stranded router: remove or rename the foreign directory, then rerun `init`. Cheapest,
   fixes the followability without touching either invariant.
2. **Auto-resolve: `init` follows nothing but offers `realpath`; `install_routers` writes
   the router anyway beside the foreign skill.** Loses: writing into a root we do not own,
   next to a skill we did not install, is exactly the collision the skip exists to
   prevent, and silently canonicalising a person's repo path turns a safety refusal into a
   convenience the person never chose.
3. **Defer, file as issues.** Loses on the same ground the framework rejects everywhere
   else: a stranger met these today; the advice is wrong *in the product's own words*, and
   "say it in the changelog" is rule 4, not a backlog item.

## Decision

Option 1. Message-level changes only, no invariant moved: the safety refusals keep
refusing, the skip keeps skipping — they only start naming what happened and what a
person can actually do. The ephemeral-receipt contract is untouched by this spec; report
026's direction (1) stays a proposal that must argue with `test_surface_adapter.py:663`
and its digest pin in its own record if anyone still wants it.

## Challenged once

Strongest case this is wrong: these are cosmetic strings in a CLI that has 26 assertions;
the money is in assertion 23 (capabilities unenforced) and this spends a cycle on prose.
The answer: assertion 23 is a build; this is the product's one observable promise — every
refusal names a followable remedy — broken in the exact places a first-time install and a
drifted dogfood machine meet it, proven today by commands whose printed advice did not
work. A product that cannot direct its own repair is not ready to be trusted to enforce
one.

## Grill

ran: round 1, 2026-08-29 — 40 min

The challenge ran against the spec as first written and against the tree while the build
landed. Ten attacks; the honest split is three real, five refuted with commands. What it
changed:

### Q: does a stranger on a fresh machine actually meet a repairable FAIL? — changed the scope
**A:** No, and the opening claimed too much. The challenger installed into a fresh HOME
carrying a foreign `ai-design/` skill folder: the install printed the collision, landed
19 routers, exited PASS, and `ai-eng doctor` answered 24 **green** — a first install
never records a router it will not write. The broken-advice FAIL is the *drifted*
machine. The fix stands for that machine; the "cost to every stranger" framing was
trimmed. `check`: the challenger's run transcript, `history://Challenger049`.

### Q: is the router skip the only silent one? — changed the example set
**A:** No. `install_routers` also skips when a command file exists that the receipt never
recorded (`wiring.py`, the `mine` set), and `--overwrite` cannot name routers at all.
Both skips now report through one `skip` callback with distinct reasons; the second
prints "a file nobody recorded writing".

### Q: was the collision silent everywhere? — half-refuted, wording kept honest
**A:** The *skills* collision was named before this change (init's `theirs` block, since
spec 024). What was silent was the *router* skip and what doctor's advice said about
repairing it. The spec now says exactly that, not "named nothing".

### Attacks that failed to land
`/private/tmp` is not a symlink (the links are `/tmp → /private/tmp`, `/var →
/private/var` — the example was rewritten to build its own link); the `init.py:868-871`
anchor had moved under the worktree (the spec now cites the symbol, not the line); "the
receipt contract is one test" — no, `test_surface_adapter.py:671-676` pins the step by a
second SHA digest, which strengthens context bullet 3; the "invariants moved" charge names
a 3-tuple return and a callback parameter, and those are exactly what the Decision says
stays put — refusals refuse, skips skip — which the 2361-test suite confirmed.

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

- Assumed: no script outside this test suite parses the two changed strings verbatim. The
  challenger confirmed `grep -rn "followed safely" tests/` and `writes them again` over
  `tests/` both return zero — so nothing reads them today, and the two named tests added
  with this change are what makes that hold going forward.
- Open risk, unsized: the router skip has TWO silent causes, not one — the foreign skill
  folder (`theirs`) and a command file that exists but the receipt does not record writing
  (the `mine` set). Both now report through the same `skip` callback with distinct
  reasons. 7 surfaces declare no command root (`surfaces.toml`), so today only
  claude-code can strand a router; a second declared root grows the blast radius with it.

## Examples somebody can check

- Given a repository path that crosses a symlink (macOS puts every temp dir behind
  `/var → /private/var` and `/tmp → /private/tmp`), When `ai-eng init --project <that path>`
  refuses, Then the message names the offending component and its target. Asserted by
  `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py -k names_the_symlink`
  (it builds a real link and checks the refusal prints its path).
- Given a surface whose skills root holds a foreign `ai-<skill>/` directory that this
  install never wrote, When `install_routers` runs with a skip callback, Then that skill's
  router does not land and the callback is told `foreign skill folder`. Asserted by
  `uv run --with pytest==9.1.1 pytest -q tests/test_stranger_install.py -k foreign_folder_is_named`.
- Given a clean machine where every router lands, When `ai-eng init --global -y` runs,
  Then no `skipped (foreign)` line appears — the negative case the challenge run proved by
  construction (fresh HOME, 19 routers, 24 green).

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
