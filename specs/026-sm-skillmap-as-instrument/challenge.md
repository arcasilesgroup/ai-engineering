---
id: "026"
slug: sm-skillmap-as-instrument
status: draft
date: 2026-08-25
---

# Challenge — skill-map as the reference-integrity instrument

Every finding carries the sentence it attacks, the command that tested it, and what the
command printed. Worst first. `WRONG` where the tree contradicts the sentence; `UNPROVEN`
where nothing in the tree can decide it.

## Findings

### 1 · WRONG — the spec pins numbers that are already stale (they move every scan)

> `sm check` → 53 errores + 4 info … 40 real defects … 13 template holes (reporte 009 y
> especificación 026, ambos reposan en los mismos conteos).

Command: `sm check --json` (fresh run, after writing report 009 and spec 026).

Output: `{reference-broken: error: 64, reference-redundant: info: 4}` · template holes
(`NNN-slug` in target): 15 · real broken: 49.

The report-spec pair claims "40 real / 13 template / 57 total". A fresh scan prints 49
real, 15 template, 68 total. The numbers shifted because the very documents that assert
them (report 009, spec 026) added 11 broken references to the tree and are scanned. The
conclusion is not wrong — most broken links are real, the `NNN-slug` hole is a template —
but the exact figures in the report/spec are measurements of a previous tree, published
as if they were a constant. A spec that names counts must name the exact `sm scan`
invocation and tree it was measured on, or the count must be recomputed at gate time.

Fix: replace the floating numbers with "counted by `sm check --json` at gate time and
rendered into the digest", and remove the four hard totals from the report/spec ("40",
"13", "53+4") or stamp them "measured at commit X".

---

### 2 · WRONG — the gate recipe, as specified, cannot pass today (40 real defects are
not fixed and the digest still fails)

Sentence: "just map runs sm scan && sm check --json and exits non-zero if the digest
contains a real reference-broken finding, and 0 once the 13 template holes are excluded
and the 40 real defects are either fixed or tracked."

Command: `sm check --json | jq 'length'` (fresh tree).

Output: 64 errors, of which 49 are real reference-broken targets in the tree. Only 15 are
template. The decision says the 40 defects are "not fixed in this trip" (Decision §4)
and that the template list covers `NNN-slug` only. But the fresh map shows 49 real,
not 40, and only 15 covered. Until the 49 are fixed or individually accepted, `just map`
cannot return the promised 0. So the spec's observable "Then … and 0 once … either fixed
or tracked" is not reachable on this tree as written.

Fix: either (a) do not deploy `just map` into `just check` until the real findings are
accepted, or (b) state the acceptance gate: the recipe is green only after every real
finding is either fixed or named in a dated acceptance record. The current text defers
the fix and demands a green gate in the same breath — that is the opaque promise the
constitution warns about.

---

### 3 · UNPROVEN — the 4 `info` redundancies are "deliberate"

Sentence: "the four redundant info findings are recorded (if severity) as deliberate, not
suppressed."

Command: `sm check --json` filter `severity == info`.

Output: 4 `reference-redundant` info rows. Two are in `specs/010` plan/spec (target
reached twice via `spec.md` and a full path), two in `specs/023` council/spec. The
spec's claim that the tree "declares the overlap intentional" (reporte) is not proven
here: the two `023` cases are exactly the "self-reference plus path" pattern that
that `sm` flags, and nothing in `023`'s frontmatter or spec body says the double link is a
deliberate decision. It is consistent with a deliberate pointer, but the spec has not
shown the command that would prove it.
and if the decision wants to call them deliberate, add the explicit sentence in the spec
that this redundancy is kept.

---

### 4 · UNPROVEN — the stranger machine without `sm` still has a green gate

Sentence: "the stranger install has no sm and the gate must still pass false-closed …
`just map` prints 'map not exercised; sm missing'".

Nothing in the repo today has a `just map` recipe and no recipe gates on `sm`, so there
is no code path to test. The claim is a design intention. It is reasonable (it mirrors
the trivy/gitleaks bracket), but as written in a spec it is not tested. What already
exists and is tested: other gates check for `trivy --version` / `gitleaks version`
fail closed when the tool is absent (Justfile `security`). So a model to copy exists;
the sentence as written still has no command that would fail if the future path broke.

---

### What could not be tested

The template list beyond `NNN-slug`: the spec assumes that is the only hole. A fuller
list would require reading every string that points at `specs/NNN-slug` and every
future skeleton; not done. Deciding whether the 49 real defects (not 40) are "fix
inline" vs "plan block" is a person's call, not a command's.

## Verdict

The instrument is real and works; the spec's recommendation (use the `sm` map's
deterministic reference check, exclude the template hole, record the real defects) is
sound. But two commands contradict the written numbers: the rock is a river—49 real
defects, 15 template, 64 errors on the live tree, not 40/13/53+4 — and the green gate
as specified cannot be reached today unless the 49 are first accepted. Fix the counts
to be computed-at-gate, and think: acceptance (both the real findings and the four
"deliberate" redundancies) must be a dated record, not prose.