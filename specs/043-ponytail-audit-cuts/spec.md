---
id: "043"
slug: ponytail-audit-cuts
status: draft
date: 2026-08-27
ref: ""
supersedes: ""
---

# Ponytail audit cuts

## Who this is for, and what it is worth to them

The maintainer of ai-engineering and every stranger who installs the wheel. Today the
tree re-forks the same primitive up to six times over — four bounded readers, five git
wrappers, four ISO-date validators, byte-identical canonical-JSON helpers, three
JSON-Schema subclasses, six frontmatter parsers — and carries a handful of wrappers and
readers no production path reaches. Every future change pays to read, test and keep
those copies green. After this spec each primitive lives once in a shared home and the
unreached wrappers are gone.

Scope retractions recorded here rather than in a register nobody owns: answer_key and
decision_boundary (spec-042's orphan-register rows); `constellation` is also deferred
there and was never in this spec's scope.

## Context and problem

A whole-repo over-engineering audit (2026-08-27) produced a ranked cut list (the audit
transcript is this spec's parent conversation; its artifact line is net -2080). Its
dead-code claims were independently grep-verified:
zero production callers for `answer_key.py`, `decision_boundary.py`,
`skeletons.seed_intent`, `imagery.findings`, `surface.receipt_binds_version`, `ui.ask`,
`executor.Sandbox.connect/.secret`. A second class of finding is alive but multiplied:
the same primitive hand-rolled N times across modules because there is no shared home
below `intent.py` — 4 identical O_NOFOLLOW bounded readers, 5 near-identical git
subprocess wrappers, 4 ISO-date validators, byte-identical `_canonical_json` in 4
modules, 3 JSON-Schema subclasses adding the same keywords, 6 frontmatter parsers.

Research (report 020) then enclosed several audit targets in governance: answer_key and
decision_boundary sit behind spec-042's orphan register and its fixture,
imagery.findings/surface.receipt_binds_version/executor's gated paths are named
evidence of PROVEN ledger rows. Those are kept; what follows cuts only what no
governance artifact claims.

The harm of leaving it unchanged: each duplicated primitive drifts (loop_guard and
_emit already sanitize differently); each dead module still costs its test suite on
every CI run; reviewers review the same code twice because it exists twice.

## Options considered

1. **Apply the surviving cuts in one commit family (chosen).** Dedup primitives first
   into shared homes (`paths.read_bounded`, one `git()` wrapper, text ISO pair, intent
   `_canonical_json`/`_Schema`), then delete production-dead wrappers, then shrink the
   engines (spec publication-report map, madr history via `git ls-tree -z`, cost
   arithmetic). Gives: maximal reduction, single coherent review. Costs: larger diff
   than an incremental trim; risk if a "dead" claim was wrong (mitigated by grep proof +
   dynamic-import sweep + per-cut commits so bisect stays useful).
2. **Apply only mechanically-safe cuts; defer contested ones.** Skip spec-010-tensioned
   items, skip anything not personally verified, cut only test-consumed-only code where
   callers can be migrated in-tree. Gives: minimal risk of governance breach. Costs:
   leaves the biggest cut (~810-line Windows transaction backend) in place, keeps the
   duplication load at nearly full strength, and defers decisions that are actually
   mechanical (which error type maps to which message) rather than risky.

Option 2 loses: it preserves most of the weight while pretending to act.

## Decision

**D-043-01**: Apply option 1, ordered as: (a) dedup primitives into shared homes;
(b) delete production-dead wrappers whose grep proof holds after dynamic-import sweep;
(c) engine shrinks preserving exact public behavior; (d) hook-layer unsanctioned
duplicate cuts only. The two sanctioned hook duplications that stay, named: (1)
self_protect's derivation of blocked-write paths from policy/surfaces.toml — hooks must
not import the package (AGENTS.md tree contract), so the re-derivation is the
constraint; (2) paths.load executing hooks by path rather than importing them — same
constraint on the hot path (~110 ms import cost is stated in pyproject.toml:22-28).

Research report 020 swept every dynamic-resolver site in the tree (cli verb
import_module, chain TABLE, paths by-path load, evals pack scan): none reaches any cut
target. Four audit findings are WITHDRAWN as governance-enclosed, not dead:

- answer_key.py / decision_boundary.py — enclosed by spec-042's orphan register
  (policy/module-status.toml deferred rows) and its hardcoded fixture
  (tests/test_orphan_register.py); deletion reverses a registered decision without
  authority. Kept. This aligns D-043-01 with the earlier draft's own exclusion rather
  than contradicting it — an earlier draft's success example asserting ImportError was
  wrong and is corrected here.
- imagery.findings/_svg_findings — the PROVEN row EP-254's named evidence command
  (`pytest tests/test_imagery.py`) executes this symbol 17 times, and stripped()'s
  shipped contract references it inside the same module. Kept.
- surface.receipt_binds_version — the named location of PROVEN row EP-016's claim.
  Kept.
- executor.Sandbox.connect/.secret + capability.Action.connect/use_secret — the
  exercised half of PROVEN row EP-176 ("secrets stay gated") backing declared
  network/secret modes in policy/capabilities.toml. `.secret` is directly exercised by
  EP-176's named evidence (`pytest tests/test_executor.py -k secret`); `connect` is not
  named in any evidence command but sits behind the same gated path and its own test
  (tests/test_executor.py:192) — kept, and flagged: an owner should either wire connect
  into a named evidence command or accept removing it under the same authority.

Excluded otherwise: spec_transaction Windows backend stays for THIS spec (prudence:
platform arm of spec-010's publication design decision — a superseding spec with an
owner is the vehicle that removes it, see Challenged once);
module-status deferred-register doctrine tension stays human-owned. The full register
also defers `constellation`, which no audit finding targeted — recorded here so the
register and this spec cannot be read as disagreeing.

Retraction provenance: the research underpinning the withdrawals lives in
`.ai/reports/020-dead-module-removal-research.md`, which is gitignored (the `.ai/`
tree is disposable by design). The retracted claims are therefore restated here,
inside the version-controlled record, so the spec does not depend on a file git
does not keep.

## Challenged once

Strongest realistic failure case: "one of the 'dead' modules has a consumer that ships
in the next release branch and its deletion breaks that work". Answer: this repo's own
doctrine (AGENTS.md rule 4) forbids compatibility shims and hard-rename culture covers
this; a deleted module returns via `git revert` in minutes; the alternative — keeping
code alive on speculation — contradicts the audited doctrine. Case fails to justify
deviation.

Second challenge case: "spec_transaction Windows backend removal was flagged by audit
as biggest cut, but you keep it — inconsistency between doctrine and action". Answer,
revised after the council finding: spec-010's own Accepted risks section reads
"None. Every risk remains open until removed or explicitly accepted" — there is NO
dated risk record sheltering the Windows backend, and the first draft of this spec
claimed one existed. That claim was wrong and is withdrawn here. What spec-010 does
contain is a design decision (option 3 chosen partly because it preserves foreign bytes
on Linux/macOS/Windows) naming ReplaceFileW as a platform contract of the record's
publication model (specs/010:456-490). The backend therefore stays for this spec's run
not as governance obedience but as prudence: deleting a platform arm of a shipped
design decision deserves its own superseding spec with an owner behind it, not a rider
on an audit sweep. Dropped from CONSTITUTION quote: the paraphrase "unaccepting needs
the same authority" — CONSTITUTION.md contains no such sentence; only "Only an
authorized person may accept a dated, evidenced risk" (:76) is real.


## Assumptions and unresolved risks

Assumptions:
- Grep evidence that named modules have zero production callers holds against the
  dynamic-import/lazy-import possibility (no evidence found of either pattern reaching
  these modules).
- The green-before-cut test suite is the observable contract baseline; any cut that
  turns a passing test red, or deletes a passing test's subject without migrating the
  test with it (the tests are part of the cut commit), flags the cut as incorrect —
  not the tree. Known migrated-in-with-the-cut tests: tests/test_ui.py's ui.ask cases
  die with ui.ask in the same commit.


Unresolved risks:
- answer_key / decision_boundary: the register (a governance artifact) and ponytail
  doctrine disagree; this spec sides with the register, and report 020 documents why.
  Owner may reopen later by superseding spec-042's register rows.
- spec_transaction Windows backend stays despite ~810 redundant lines: a machine this
  project develops on POSIX only still has to run it until its owner revisits specs/010.
## Examples somebody can check

**The success path.** Given the repository after the cut commits land, When
`just check` runs, Then the gate is green against the reduced tree: the same test
count minus the deleted modules' own tests, `0 failed` in the tail. No pre-cut pass
count is asserted here; the baseline is whatever the tree read green before the first
cut commit, verified by the build log of each commit.

**The governance-enclosure path.** Given `answer_key.py` kept per D-043-01, When
`uv run python -c "from ai_engineering import answer_key"` runs, Then it imports cleanly —
verified by running the command and reading exit `0` with no traceback, the enclosure
proven rather than assumed.

**The denial path.** Given any cut whose module had a hidden consumer, When
`ai-eng doctor` runs after the cut, Then it fails closed — verified by running
`ai-eng doctor` and reading the missing symbol's name beside an `exit status 1`.

**The dedup criterion.** Given the four commit stages landed, When
`grep -rc "def _canonical_json" src/ai_engineering/*.py | grep -v ":0"` runs,
Then it prints exactly one line (the shared home in intent.py); and when
`grep -rn "def _git\b" src/ai_engineering/*.py` runs, Then every remaining hit is the
single shared wrapper. Each primitive's "lives once" test is a grep with an expected
count written beside it.

**The undecidable path.** Given any ambiguity about whether a module is reachable, When
the evidence cannot decide reachability, Then the module stays, and its name is recorded
under Excluded otherwise in this spec with the reason — the record, not a grep for the
name, is what distinguishes "kept after looking" from "never considered".

## Decisions

- [ ] **D-043-01 — Cut list ordered in four commits (dedup → delete → shrink → hooks), changelog entry per commit per AGENTS.md rule 4's second clause**.
      **Rationale:** one pass per primitive class keeps the diff reviewable while producing a bisect-friendly history; excluded items carry explicit rationale tied to spec-010's design decision and the orphan register. Box stays unticked until the commits land; promotion waits for a named person (`ai-eng decide`).

## Accepted risks

<!-- none; see unresolved risks -->

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
