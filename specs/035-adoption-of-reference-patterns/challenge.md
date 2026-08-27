# Challenge — spec 035 (adoption-of-reference-patterns)

Challenger: independent critic, fresh context. Read only the spec and the tree. Verdicts:
`WRONG` (tree contradicts), `UNPROVEN` (nothing in the tree can decide it yet), `OK`
(command confirmed it). Every finding carries the command that tested it and what it
printed. Ordered worst first.

## UNPROVEN — the seven `-k` fixture lines all reference a file that does not exist

The spec's "Examples somebody can check" block asserts each `-k` selector on
`tests/test_035_adoption.py` produces exactly `1 passed`:

- `uv run --with pytest==9.1.1 pytest -q tests/test_035_adoption.py -k evidence` -> `1 passed`
- same fixture, `-k evidence_unmet` -> `1 passed`
- `-k verifier_no_edit` -> `1 passed`
- `-k not_covered` -> `1 passed`
- `-k boundary_undecidable` -> `1 passed`
- `-k unnamed_ranking` -> `1 passed`
- `-k cost_preflight` -> `1 passed`

Command (all seven):

```
pytest -q tests/test_035_adoption.py -k <each selector in turn>
```

Printed (identical for every selector):

```
no tests ran in 0.00s
ERROR: file or directory not found: tests/test_035_adoption.py
```

`ls tests/test_035_adoption.py` -> `No such file or directory`. The fixture file does not
exist yet (`tests/` has 114 entries, none named `test_035_adoption.py`). Nothing in the
tree can decide whether any of these runs would show `1 passed`; every one is UNPROVEN,
reported honestly, not faked. The same non-existence makes the Production-ready bullets
that lean on this file unprovable too (below).

## UNPROVEN — Production-ready bullets describing the not-yet-written eval/fixture work

- "CI/CD — `just check` runs the new behaviour fixtures on every push (`just check` -> ...)"
  Command: `sed -n '263p' justfile` prints
  `check: build sbom lint typecheck test cover security register skilleval evals counts intent-page lenses council map ran`.
  The gate recipe exists and runs, but the *new behaviour fixtures* do not (`tests/test_035_adoption.py` missing) — the tree cannot decide "runs the new behaviour fixtures".
- "Health and data age — `tests/test_035_adoption.py` runs in `just test` on every gate"
  Command: `sed -n '98,100p' justfile` prints
  `test:` / `    uv run --with {{pytest}} --with {{xdist}} pytest -q -n auto -k "fast_enough"`.
  The recipe exists; the file it is asserted to run does not. UNPROVEN.
- "External check — ... the named-framework and boundary rules are additionally asserted by
  `tests/skill_eval.py`, the independent route over the same corpora"
  Command: `grep -niE "boundary|named.?framework|rice|kano|effort" tests/skill_eval.py`
  prints nothing (zero matches). The file exists (`tests/skill_eval.py`, 452 lines) but has
  `def test_` functions (`grep -nE "^def test_"` -> empty) and no boundary/named-framework
  assertion today. Whether the implemented spec adds it is undecidable in the tree. UNPROVEN.
- "Second path — each behaviour is read by its module and its fixture with no shared line
  (`test_035_adoption.py` is the independent reader ...)"
  `ls tests/test_035_adoption.py` -> `No such file or directory`. The named independent
  reader does not exist. UNPROVEN.

## OK — research counts and the research record all match the tree

- "`.ai/research`, 17 leaf reports + `SINTESIS.md`"
  Commands: `find .ai/research/leaves -maxdepth 1 -type f | wc -l` -> `17`;
  `ls .ai/research/SINTESIS.md` -> present. The 17 leaf files are `01-unlazy … 17-AL-Design`.
  OK.
- "read sixteen external reference implementations — … cc-creators-skill (×2) …"
  Command: `ls .ai/research/leaves/` -> exactly the named list, with
  `11-cc-creators-skill.prompt.md` and `13-cc-creators-skill-b.prompt.md` (the ×2).
  `grep "Referencias analizadas" .ai/research/SINTESIS.md` ->
  `| Referencias analizadas | 16 (17 hojas; cc-creators-skill ×2 enfoques) |`. OK.
- "distilled roughly 190 adoptable items"
  Command: `grep -n "~190" .ai/research/SINTESIS.md` ->
  `**Total de items de adopción identificados: ~190**, consolidados aquí por componente destino.`. OK.
- "… into eight meta-patterns"
  Command: `grep -n "8 meta-patrones" .ai/research/SINTESIS.md` ->
  `## 2. Hallazgos transversales (los 8 meta-patrones que se repiten)`. OK.
- "The full registry of 190 items stays in `.ai/research/SINTESIS.md`"
  Command: `ls .ai/research/SINTESIS.md` -> present (192 lines), header states `~190`;
  the adopted-item tables are in it. OK.

## OK — the "specs 034 and earlier committed" claim

- "measured in this tree on 2026-08-26 (specs 034 and earlier committed)"
  Commands:
  `for i in $(seq -f "%03g" 1 34); do [ -d "specs/${i}-"* ] || echo MISSING $i; done` ->
  no MISSING lines (missing=0); `git ls-files 'specs/0*-*/spec.md' | wc -l` -> `35`;
  `git status --porcelain specs/` -> empty (nothing uncommitted).
  `git log --oneline -1` -> `6f2a058c docs(spec): adopt reference patterns as checked behaviours (R0/R1/R2)`.
  Spec 034 (`specs/034-…/spec.md`) is tracked at HEAD. OK.

## OK — the framework-backbone claims are grounded

- "one writer makes the commits (`AGENTS.md`)"
  Command: `grep -niE "one writer|single writer" AGENTS.md` ->
  `53:## One writer, and readers only when independence is what you are buying`. OK.
- "`skill-sequence.toml` is a checked copy of the governed order"
  Commands: `find . -name 'skill-sequence.toml'` -> `./policy/skill-sequence.toml`;
  its head reads `# One checked copy of which stage follows which. This used to be prose in
  \`ai-cycle/SKILL.md\`, which no test read …` and
  `grep -rln "skill_sequence" tests/` -> `tests/test_skill_sequence.py` (the checker).
  OK (at `policy/`, under the bare name the spec uses).
- "a `just check` gate runs a green rule"
  Command: `sed -n '263p' justfile` ->
  `check: build sbom lint typecheck test cover security register skilleval evals counts intent-page lenses council map ran`
  — the recipe exists and chains the lanes, including the `lenses` and `council` recipes.
  OK.
- "`.github/workflows/check.yml` runs the whole gate on every push"
  Command: `read .github/workflows/check.yml` -> `on: push: branches: [main, v1]` plus
  `pull_request`/`merge_group`, and the step "the gate, exactly as a developer runs it" runs
  `just check | tee …`. File exists (`ls .github/workflows/` -> `check.yml install-matrix.yml release.yml`). OK.
- "`just security`: gitleaks, semgrep and trivy on every push"
  Commands: `sed -n '101,109p' justfile` prints the `security:` recipe invoking `gitleaks
  version` (pinned), `trivy --version` (pinned), and `ai_engineering scan` over semgrep;
  `check.yml` installs gitleaks and trivy and runs the gate on push. OK.

## OK — the research-item citations exist in the research record

The spec cites reference IDs as proof ("unlazy U01/U02", "okf OKF-03", "graph-eng G-17/G-09",
"Graph-engineering G-01/02/03/16", "Loop-Engineering LE-01", "wayfinder W-01/02/03",
"addyosmani ASK-14/ASK-02/ASK-01/ASK-08", "deepsec D-01/D-05", "model-router MR-01/02/MR-03",
"contains-studio CS-01/02/03", "cc-creators A-07/CC-05", "headstart H02", "AL-Design
D-01/A-01/A-02", "graph-eng G-04/05/06/07", "adopt-001..005", "LOOP-ENG LE-07/LE-03",
"al-design-system A-14", "unlazy U06/U07", "graph-eng G-10").

Command (per ID): `grep -cw "<ID>" .ai/research/SINTESIS.md` — every cited ID counts ≥ 1
(e.g. `D-05=3, G-17=1, U01=2, G-16=1, ASK-14=1, CC-05=1, A-14=2, adopt-005=1, U06=2,
A-01=2, ASK-12=1`). The single exception, `H02`, is absent from SINTESIS but present in the
per-reference report: `grep -niE "H0?2" .ai/research/reports/06-headstart/report.md` ->
`H02 | "Un camino, no una shortlist" …` (line 59) — so the citation is grounded in the
research record. All citations OK.

## OK — the spec-034 cross-references are accurate

- "same stance as spec 034 B-034-2"
  Command: `grep -n "B-034-2" specs/034-…/spec.md` ->
  `84:### B-034-2 — Named decision frameworks (research N27)`. OK.
- "the same way spec 034 answered it for its three behaviours"
  Command: `grep -nE "three behaviou?r" specs/034-…/spec.md` ->
  `72:extends the target with the three behaviours below; …`. OK.
- "the inherited `madr.validate` red from ADR 0025 (recorded in spec 034) stays open"
  Command: `grep -niE "madr\.validate|ADR 0025" specs/034-…/spec.md` ->
  `127:- Unresolved: the inherited \`madr.validate\` red from ADR 0025; recorded, not fixed here.`
  OK — and `check.yml` (guards job) independently confirms the red is real
  ("a one-commit checkout … `madr.validate` … returns INCOMPLETE, so the baseline is red").

## OK — the research goals' own gates file exists

- (context framing) `.ai/research/GATES.md` present; `PLAN.md`, `SINTESIS.md`, `leaves/`,
  `reports/`, `logs/` all present under `.ai/research/`.

## What I could not test, and why

- **"guards fail closed, telemetry fails open"** (context block). No single command decides
  a whole guard suite's fail-closed property or the telemetry fail-open property; the spec
  offers no path or count to run. UNPROVEN by design; I did not invent a substitute check.
- **"it never changes `.ai/intent.md` or `CONSTITUTION.md`"** (decision). A claim about a
  *future absence of change*; nothing in the current tree can disprove or prove it. I
  verified both files exist (`ls .ai/intent.md`, `ls CONSTITUTION.md` -> present) but the
  "will not change" half is untestable from this snapshot.
- **The seven `-k` fixture runs.** All fail identically with
  `ERROR: file or directory not found: tests/test_035_adoption.py` / `no tests ran` because
  the file does not exist yet — listed under UNPROVEN above, with exact output.
- **Any verdict on whether the fixtures would actually give `1 passed` green.** The
  behaviours, modules and fixtures described do not exist in the tree; no command can reach
  them yet.
- **Reference-vendor content the spec rejects as lock-in** (Vercel, `claude -p`,
  SkillSpector/NVIDIA, Playwright-only, `model: opus`) — claims about external
  implementations' internals that this tree does not contain; only their research-ID
  citations (above) are decidable here.