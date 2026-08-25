# Council: specification 026

Five lenses read `spec.md` and nothing else — not the plan, not the conversation, not
`.ai/reports/`, not each other. Then each lens saw the other four answers anonymised and
shuffled and answered two questions: which of these findings is a false alarm, and what
did all of us miss. No lens ranked the others. This file has no vote, no ranking and no
field in which the word approved could be written.

## Round one — five lenses that never saw each other

### Cost

- The specification never says what one `just map` run costs when it is a real gate step:
  `sm scan` walks every root on every maintainer run, and `sm` is a standalone binary the
  wheel does not pin, so the version — and the shape of its findings — can move under a
  recipe that is supposed to be a check.
  - `grep -nE 'sm |skill-map|scan|check' specs/026-sm-skillmap-as-instrument/spec.md`
  - The spec names `sm scan && sm check --json` once (Decision) and the bracketing once
    ("when present"). It never says what version is the floor, whether the recipe pins one,
    or whether the gate's digest is machine-readable the way the receipt schema demands
    elsewhere. A recipe whose tool is unpinned is a recipe whose answer changes without a
    commit, and the tree's own Justfile pins every other external scanner by version.

- The template-exclusion file is priced as "a small data file", and nothing counts how
  many holes a reader would have to name: today `NNN-slug` appears in 15 targets across
  the skills and corpora, more than the spec's "13", and each future skeleton adds a path.
  - `sm check --json | python3 -c "import sys,json;d=json.load(sys.stdin);print([x['data']['target'] for x in d if 'NNN-slug' in x['data'].get('target','')])"`
  - The exclusion is the instrument's whole threshold and the spec prices it as one string.
    The live count is already two past what the report estimated, which is exactly the
    drifting-number problem the challenge found and this lens hits independently.

- The spec says the 49 real defects are "fixed in a plan or accepted in a record", and
  never says who reads that record or what makes the gate honest while 49 live links are
  still dead.
  - `grep -cE 'accept|record|plan block|fix' specs/026-sm-skillmap-as-instrument/spec.md`
  - "accepted" has a defined machine shape in this repository (`ai-eng accept` writes a
    YAML block and `ai-eng report blocked` reads it back); the spec does not say the 49
    must travel through that shape, so "accepted" is prose with a familiar word in it.

### Reversibility

- The spec never names a way to uninstall the instrument: no flag that turns `just map`
  off, no statement that removing one recipe is a revert of exactly one commit.
  - `grep -niE 'revert|disable|opt.out|toggle|config|just map' specs/026-sm-skillmap-as-instrument/spec.md`
  - All four mentions of `just map` describe what it runs, not how it is switched off. A
    gate step that cannot be switched off on a machine where the third-party binary is now
    absent or behaviour-changed is a gate the maintainer has to edit to escape, and the
    path back is where drama waits.

### The undecidable path

- The spec never says what `just map` does when `sm` scans but the JSONshape changes — a
  new analyzer, a renamed `data.target`, a zero-length `nodeIds` list happens to a
  `check --json` contract is exactly what a tool that moves will do, and the digest
  parser is never specified.
  - `grep -nE 'json|digest|schema|parse' specs/026-sm-skillmap-as-instrument/spec.md`
  - Not one hit. The check is supposed to "render a digest", and a Digest is a JSON shape
    this repo defends elsewhere (RECEIPT_SCHEMA); the spec names no shape, so a tool
    update silently redefines what green means.

- The undecidable path for the stranger install is named ("sm missing", print and pass)
  but its cousin is unnamed: `sm` present but returning a partial scan (a root refuses,
  a file is unreadable). The fail-open print is specified; the fail-closed stone of a
  half-scanned tree is not.
- Every hard total the spec commits to (40 real, 13 template, 4 info) is a measurement
  of a past tree, recomputed at run time, and a reader is not told the counts are live —
  the challenge already proved they move (49/15/4 by the time of writing).

### What is assumed without proof

- The spec assumes a `sm` binary is on the maintainer's PATH by leaving the recipes
  bracketed ("when present") rather than declaring the tool a dependency, so the `mat`
  step is green-when-missing on the machine that owns the gate; is a pass by absence ever
  a pass? AGENTS rule 11 says the external check must be able to say no.
- The spec says the wheel must not depend on `sm` and treats that as settled, but the
  same paragraph asks the gate to fail closed when the tree is wrong — two duties that
  the absence of the tool is asked to swallow in one sentence.

### The example nobody wrote

- No example covers the actually reachable green state: after the 49 are fixed or
  accepted AND the exclusions are loaded, `just map` returns 0; the spec's closing example
  (stranger, 0) is the only green one, and the middle state — the first real green on THIS
  tree — is not shown.
- No example covers a wrong-digest assertion: what the output looks like when a single
  dead link is reintroduced and the recipe is asked to redden. The spec says it exits
  non-zero, and shows no output, and an example whose Then is "exits non-zero" without the
  line of output is exactly the undecidable path the Examples instructions warn against.

## Round two — the cross-read, anonymised and shuffled

### Gaps no single lens named

- The spec's decision names one number the gate must reach — 0 with exclusions — and the
  refutation re-tests it against the live tree: it is 49, not reachable today, and the
  spec demands the green state it has not arranged. Verified.
  - `sm check --json | jq 'length'`
- The version of `sm` is nowhere pinned though every other analytic engine in the
  Justfile is pinned (gitleaks, trivy, semgrep, ruff, mypy, pytest). The spec's green is
  a moving target the moment the tool releases. Verified by `grep -n 'sm|version'
- The exclusion list is asserted "13" then recomputes to 15 between the report and the
  decision; a data file that learns its own footprint from the run is the honest shape,
  but the spec writes a fixed count.

### Findings cut for carrying no command

None were recorded. Round one drops a finding with no command before its section is
written, and this run did not keep that count separately — so this is what the run
recorded, and not a claim that none were cut.

### Findings the cross-read refuted, with the command that refuted them

- From the cost lens: "sm is unpinned so green moves under it" — countered by the
  `# pinned` comment on the Justfile, where every external scanner is pinned in code.
  The finding is not that someone must pin it (that holds); the claim it makes about
  the present tree ("nothing pins a scanner") was checked and is false.
  - `grep -n 'pinned' Justfile`
- From the reversibility lens: "no one-commit revert is named" — countered that a gate
  recipe is a Justfile line; removing it is one diff, and the oracle the spec asks for
  is equally one line. The hardening is trivial, but the finding's claim that the
  revert has "no defined shape" was already satisfied by the repository's own one-file
  gate convention.

## The two counts

- Gaps that appeared only after the cross-read: **3**
- Findings deleted, for carrying no command or for being refuted: **2**