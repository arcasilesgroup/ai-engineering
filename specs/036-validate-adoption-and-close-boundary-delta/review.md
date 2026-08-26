# Review — spec 036 build (commits `ed4d3c22..HEAD`, the five-commit 036 block)

Reviewed per `.agents/skills/ai-review/SKILL.md`. Full diff of the five commits read first
(`git diff ed4d3c22..HEAD`; the listed range `47ec9093..HEAD` is the same build minus the
red-fixtures commit that is its base — parent `ed4d3c22` is reviewed so the fixtures are
included). Spec and plan read before the diff. Every lens in `references/` worked, one at a
time; the ones a Python module + markdown corpus cannot touch are named and skipped below.

I ran, and may claim only: `pytest -q tests/test_036_boundary.py tests/test_036_validation.py`
→ `6 passed`; the harness' `corpus()`/`problems()` over the current tree and over a
`git archive` copy of the base tree (to pin the baseline counts). I did **not** run `just
check`, the madr gate, or the full suite, and this report claims no gate result.

## What this is not, and what is

Verdicts below are separated into **blocking** and **merge-without**; nothing here is
accepted by this review. A person or a gate decides.

---

## BLOCKING

### BLOCK-1 — the freshness check does not watch two of the nine symbols the validation table promises
`tests/test_036_validation.py:27` (and the omitted row after `:25`)

B-036-3 is the spec's central mechanism: *"asserts the validation table does not rot: every
row's module exists and exports the **named contract symbol from the table above** — the
symbol per row is the check's input (council G3)"*. The spec's table names
`capability.py · preflight` and a second `contract.py` row named `_anti_rationalization_problems`.

As built, `ROWS` asserts `("capability", "Action", None)` and lists `contract` once
(`audit_one`). The table's named symbols are watched differently:

- `policy` of `preflight` — `hasattr(capability, "preflight")` is true (`src/ai_engineering/capability.py:365`),
  so the real symbol the table promises is importable and the row chose a different one.
- `_anti_rationalization_problems` (`src/ai_engineering/contract.py:429`) has **no row at all**.

**Failing scenario:** a refactor deletes `capability.preflight` (or `contract._anti_rationalization_problems`)
while the validation table still claims they ship. The fresh test the spec built to fail on
exactly that stays green, and the record rots silently — the precise rot B-036-3 exists to
stop ("a future refactor that deletes or splits one of the validated modules fails this
check with the reason to update the record first"). Plan task 3's done-when ("every table
row's module exists **with its symbol**") is unmet for two rows. Plan task 2 also asks for a
"parallel test proves `capability.preflight` still behaves (no second model)" —
`tests/test_036_boundary.py` has no such probe (its fifth test maps the manifest but never
calls `preflight`).

**Smallest fix:** in `tests/test_036_validation.py`, change `("capability", "Action", None)`
→ `("capability", "preflight", None)` and add `("contract", "_anti_rationalization_problems", None)`
after the existing `contract` row. Both symbols are module attributes, so the asserts hold
with no production change. (Optional, to satisfy plan task 2's parallel-probe item: drive
`capability.preflight` on a deny case inside `test_036_boundary.py`, or record that
`tests/test_capabilities.py` already exercises it and drop the plan's item.)

---

## What I tried to kill, and what lived (before ranking)

- **Circular routing (description refusals):** `/ai-review`'s new clause sends
  out-of-boundary decisions to `/ai-verify` (`.agents/skills/ai-review/SKILL.md:10`), and
  `/ai-verify`'s new clause refuses the *same subject* with no destination
  (`.agents/skills/ai-verify/SKILL.md:10`). This looks like the harness's own "two skills
  refusing the same case leaves the person with nowhere to go" defect, and the harness has
  no pairwise description-refusal check to see it. **Killed — not a bug.** The spec's stated
  outcome for an out-of-declaration decision is exactly `CANNOT DECIDE` + block with no
  skill guessing; the review routes the situation on, verify reports the block, and a human
  decides. That is the designed terminal, not a dead end. Noted because it would have been
  the easiest wrong blocker in this diff.
- **`from_capability_manifest` defaulting an unknown gate to Ask-first (fail-open?):** the
  manifest schema `policy/capability-manifest.schema.json:190-196` constrains `human_gate` to
  `never | before_write | before_exec | before_network | before_publish`, and the live
  `policy/capabilities.toml` uses exactly those (plus `never`). Every valid non-`never`
  gate is genuinely ask-first; the default is semantically exact over the schema-valid
  vocabulary. The malformed-gate case cannot reach the mapper (the schema refuses it first).
  **Killed as a fail-open finding** — but see M-4/M-5 for the residue (dead `"always"` key,
  mismatched-malformed behavior between the module's two entry points).
- **`_VALID_CLASSES` is dead, `_unknown_index()` returns a constant:** the spec says
  "indexed reason (`U1`, `U2`, … for each out-of-declaration class)". With one flat
  declaration mapping there is exactly one out class, so a constant `U1` is honest; but the
  indirection and the unused constant survive. **Lived** as a simplification finding M-6.
- **Zero production callers of the classifier:** nothing in `src/`, hooks, or the harness
  imports `decision_boundary`. **Killed — by design:** the spec's "Second path" box states
  "the module is read by its fixture and the corpus rows are read by `skill_eval.py` with no
  shared line". The module is the machine-articulated proof object, not yet wired; flagging
  its lack of an integration caller would be a rewrite opinion, so it is a comment, not a
  blocker.
- **"lower bound of 368" in `docs/requirements.toml:273`:** the mechanism is a pin with
  `margin = 0` (exact match), not a floor. The phrase pre-dates this range; the diff only
  corrected the number (363→368) correctly. **Killed** — outside the diff's semantic change.
- **The `368` total itself:** I recomputed it two ways (base tree 81+42+115+125=363, current
  tree 81+44+118+125=368) and it is honest despite the why-block's narrative errors (M-1).
  `tests/test_skill_eval.py::test_the_baseline_is_the_number_this_tree_actually_measures`
  pins `RAN skilleval=368` against the register by running the real script, so the number is
  machine-held even if the prose around it is wrong.

## What is good (once, where load-bearing)

The classifier's structure is the load-bearing good: `Classified.decided`/`undecided`
split with `blocks` owned by the undecided path means `None` can never be coerced into a
class — the fail-closed property the spec names, and the parallel clean-control test
(`test_never_coerces_an_undecided_class`) actually defends it rather than restating it. The
proof-first sequencing is real (fixtures commit `47ec9093` lands before the module commit
`5e26a83d`), and the baseline is machine-pinned by a test that runs the real script rather
than asserting the constant twice.

---

## MERGE-WITHOUT findings (ranked by what I would actually object to)

### M-1 — the register's baseline `why` mis-states the moving columns
`policy/pilot-register.toml:344`

The "363 to 368" rationale says "hand-offs 42 to 42 … labelled cases 240 to 245 … two
refusals and three quoted corpus cases added. **81+42+245 is 368**." The added rows are two
description refusals and three corpus takes, so: hand-offs are 42 → **44** (not 42→42),
labelled cases are 240 → **243** (not 240→245), and the arithmetic is **81+44+243 = 368**,
not 81+42+245. The total `368` is right and pinned; the two column numbers and the
arithmetic line are wrong.
**Failing scenario:** a reader auditing whether "nothing was withdrawn" reconciles the five
added rows against the register to confirm the count; the columns don't add up to the stated
total, so the approval rationale reads as fabricated even though the pin is honest.
**Smallest fix:** change `42 to 42` → `42 to 44`, `240 to 245` → `240 to 243`, `81+42+245`
→ `81+44+243`.

### M-2 — `/ai-spec`'s description carries no boundary refusal; the approved plan's three-file list is not honoured
`.agents/skills/ai-spec/SKILL.md:7-13`; plan task 4 named `.agents/skills/ai-spec/SKILL.md`
explicitly; the range delivers the refusal only in `/ai-review` and `/ai-verify`.

`7109fc96` added the clause to all three (`measured = 369`); `8ccae280` reverted the
ai-spec description (`measured = 368`) and the baseline `why` records the narrower route
("`/ai-spec` keeps its closed-contract frontmatter untouched — its corpus carries the quoted
route instead"). The cause is real: `tests/test_contracts.py::ai_spec_problems`
(`AI_SPEC_FRONTMATTER`, line 665) locks the raw frontmatter bytes, so any description edit
reddens a governed test the plan did not authorise touching.
**Failing scenario:** a user sends an out-of-declaration request to `/ai-spec` ("write the
spec for deciding whether to grant access"). The routing surface the matcher reads — the
description — never refuses it (the corpus row is a *labelled sample*, read by `cases()`,
not the description surface `_REFUSAL` reads), so the request routes to ai-spec as a
spec-writing ask instead of reporting `CANNOT DECIDE`. The spec's own acceptance example
("Given the boundary refusal in **each** `SKILL.md` description") is unsatisfiable as built.
**Smallest fix:** either amend the record so the approved route is named as two descriptions
+ three corpus rows (the description-side omission being a closed-contract trade), or add
the clause back to ai-spec's description *and* update `AI_SPEC_FRONTMATTER` in the same
commit — the latter touches a governed test the frozen plan did not authorise, which is why
the author's call is defensible but the plan's file list is left unmet. Do not silently
accept; record it.

### M-3 — declaration keys are folded differently from decisions, so natural-language keys never match
`src/ai_engineering/decision_boundary.py:69-70`

`classify` normalises the decision with `.casefold().replace(" ", "_")` (and the canonical
value normaliser at `:50` also folds `-`), but the declaration **keys** are only
`k.casefold()` — no space/hyphen fold. A declaration written as a real vocabulary entry
(`"Ask First": …` or `"ask-first": …`) never matches a decision folded to `ask_first`, and
an in-scope decision reports `U1`/blocks instead of classifying.
**Failing scenario:** a caller builds declarations in human casing (the only dialect a
non-code reader would write) and every in-scope decision is refused as out-of-declaration.
The shipped tests only use keys already identical to folded decisions, so nothing covers it.
**Smallest fix:** fold keys with the same helper as decisions (e.g. `_normalise_k(k)` or
apply the `:50` fold to key comparison).

### M-4 — `_GATES["always"]` is unreachable and the mapping's `Never` branch is untested and dead against the schema
`src/ai_engineering/decision_boundary.py:23`

`human_gate` is schema-constrained to five values (`policy/capability-manifest.schema.json:190`),
none of which is `"always"`, and the live `capabilities.toml` uses none. So the
`"always": "Never"` entry can never fire; every live gate maps to `Always` (never) or
`Ask-first` (all four `before_*` via the default at `:95`), and `from_capability_manifest`
can never return `Never`.
**Failing scenario:** none today (the branch is unreachable), which is the finding — the
`Never` class the classifier advertises is not producible through the manifest surface it
swears by, and the `"always"` key is dead code that future readers will assume is live.
**Smallest fix:** either drop `"always"` (with a note that `Never` is unreachable via the
manifest surface) or keep it and add a fixture proving the `Never` branch, and say why a
schema-forbidden value is mapped.

### M-5 — the module's two entry points disagree on malformed input
`src/ai_engineering/decision_boundary.py:95` vs `:72-76`

`classify` treats a malformed class value as `U0` and blocks. `from_capability_manifest`
**silently coerces** any unknown/missing gate to `Ask-first`. The spec's fail-closed claim is
"a `None` boundary is never coerced into a guessed class" — the mapper guesses a class for
exactly the inputs the classifier refuses. (It happens to be semantically correct over the
schema-valid vocabulary — see the kill note — but the two halves of one module treat "malformed"
oppositely.)
**Smallest fix:** make the mapper's fallback explicit (`before_write`/`before_exec`/
`before_publish` → `Ask-first` by name, anything else → `U0`/block), so the "guessed class"
and "refused class" behaviors are one rule.

### M-6 — dead constant and constant-returning helper
`src/ai_engineering/decision_boundary.py:24` (`_VALID_CLASSES`, unused) and `:54`
(`_unknown_index()`, always returns `"U1"` while the spec and docstring promise `U1, U2, …`)

Neither is wrong at runtime; both overstate the design. `_VALID_CLASSES` is never read; the
docstring's "indexed `U1..`" implies per-class indices the code cannot produce.
**Smallest fix:** delete `_VALID_CLASSES`; either add real indexing or soften the docstring
to "U1 (the single out-of-declaration class)".

### M-7 — class-mapping edge branches are untested
`tests/test_036_boundary.py:48-59`

The manifest-mapping test covers `never`→`Always` and `before_network`→`Ask-first` only.
`before_exec`/`before_publish`/`before_write`→`Ask-first` (the shipped default), blank/missing
capability or mode id, and empty `modes` have no fixture.
**Failing scenario:** a future typo in the default (e.g. defaulting to `Always`)
would pass all five current tests because the live gate values (`before_write`,
`before_exec`, `before_publish`) are never exercised.
**Smallest fix:** add one fixture asserting the three `before_*` gates and the blank-id skip.

### M-8 — the module docstring claims behavior the code does not perform
`src/ai_engineering/decision_boundary.py:5`

"reporting CANNOT DECIDE and blocking" — the module never emits the string `CANNOT DECIDE`
(only the corpus prose and tests do); it returns a `Classified` struct whose `blocks` flag a
*caller* renders. This is the exact docstring-promises-more-than-it-does shape the docs lens
warns about.
**Smallest fix:** reword to "returning an undecided `Classified` whose caller reports
`CANNOT DECIDE` and blocks".

### Skipped lenses, named

- **frontend, motion** (`references/frontend.md`, `motion.md`): the diff is one Python module
  and markdown/TOML prose; no markup, gesture, or transition exists to judge. Skipped.
- **performance**: nothing measurable — `classify` is O(n) over a handful of keys with no I/O,
  `load_capability_classes` opens one trusted file and has no caller; there is no hot path to
  budget. Skipped, with that reason.
- **security**: no new trust boundary (a repo-owned file read-only, no shell, no network, no
  secrets, no dependency added — stdlib only). The only gate-shaped surface
  (M-4/M-5) is a permission-class *mapping* and defaults to ask-first, never an allow. No
  security finding beyond M-4/M-5 already filed under correctness.

### Notes / comments (not findings)

- The same refusal subject in `/ai-review` and `/ai-verify` descriptions is invisible to
  `tests/skill_eval.py` (no pairwise description-refusal check) and is the *intended*
  review-on/verify-blocks chain — see kill note. Worth a harness-level look only if the
  "blocks" destination ever becomes a real skill.

---

## What I did not run

I did not run `just check`, the madr/ADR 0025 gate, or the full suite, and I claim nothing
about them. I ran the two new fixture files (`6 passed`) and the routing harness' counting
functions on the current and base trees; the register's `measured = 368`, the baseline
pin, and the classifier behavior are grounded on those runs, not on a CI claim.

## Verdict counts

- **Blocking: 1** (BLOCK-1 — freshness check misses 2 of 9 promised symbols / wrong symbol for `preflight`; plan task 2's parallel preflight probe absent).
- **Merge-without: 8** (M-1..M-8, ranked M-1 first — the register rationale — then M-2 the
  /ai-spec description deviation, then the module-level edge cases).
- **Skipped lenses: 4 named** (frontend, motion, performance, security).
- Accepted by this review: **none**.