# Challenge — spec 036 (validate-adoption-and-close-boundary-delta)

Attacker: independent critic (fresh context, spec + tree only).
Date: 2026-08-26.
Method: every checkable sentence executed via command, output pasted, verdict per finding
(WORST first: WRONG > UNPROVEN > OK). No edits to the spec; output file only.

Head attacked: `b351f267` (`docs(spec): 036 supersedes 035 with validated delta and council
corrections`). Working tree otherwise clean for 036 (only `challenge.md`, `council.md`,
`council.html` untracked).

## Verdict summary

- WRONG: **0**
- UNPROVEN: **3** (all planned-work acceptance criteria the spec itself states are
  not-yet-existing, plus two cross-document provenance attributions not individually read)
- OK: **15** (every validation-table row's module + contract symbol, provenance cites and
  git dates, 035 untouched, decision_boundary.py absence, boundary-word count, fixture
  absence, skill_eval case shapes)

---

## UNPROVEN

### U-1 — B-036-1/2/3 acceptance commands cannot be executed (fixtures do not exist by design)
Spec sentences: "**Success, classified:** … `pytest -q tests/test_036_boundary.py` → `2
passed`", "**Denial, out-of-declaration:** … `-k undecidable` → `1 passed`",
"**Validation stays true:** … `pytest -q tests/test_036_validation.py` → `1 passed`".
Command and output:
```
$ ls tests/test_036_boundary.py tests/test_036_validation.py
ls: cannot access 'tests/test_036_boundary.py': No such file or directory
ls: cannot access 'tests/test_036_validation.py': No such file or directory
```
Verdict: **UNPROVEN.** The files do not exist, and the spec says they should not yet
("`tests/test_036_boundary.py` and `tests/test_036_validation.py` do not exist until the
approved plan writes them, and the counts are the goal, not a claim that they pass today").
The spec is internally consistent, but the passing-count claims are unexecutable at this
commit.

### U-2 — module ↔ spec-number provenance (specs 013-034 attribution) not individually verified
Spec sentences: "first shipped `feat(evidence): verify executable receipts` (2026-08-14),
calibration formalised in spec 029", "`src/ai_engineering/contract.py` (specs 026-033)",
"`src/ai_engineering/cost.py` (spec 029)", "`src/ai_engineering/trim.py` (spec 033)",
"`src/ai_engineering/decision_fw.py` (spec 034)". I verified each module exists, exports the
named symbol, and cites the named external research in its docstring; I did not open every
spec 013-034 to confirm each numeric attribution, per budget discipline. The two git-date
claims ARE checked below and match. Verdict: **UNPROVEN** (partial) — the module/behaviour
exist and are cited, but the exact spec-number provenance is read-from-memory across 20+
specs.

### U-3 — semantic reading of the 13 `boundary` usages
Spec sentence: "five existing modules already use the word `boundary` alone, which five
existing modules already use for filesystem, word and data boundaries (spec 036 council,
gap G1)". The count claim (≥5) is checked below and holds (13 files). The qualitative
"filesystem, word and data boundaries" reading of all 13 usages comes from the council and
was not re-derived here. Verdict: **UNPROVEN** (count is OK; the per-file semantics were not
re-derrived).

---

## OK (worst with a caveat first)

### O-1 — C-035-4 boundary classifier genuinely absent (the claimed gap)
Spec: "B-035-4 — a boundary classifier … does not exist; no skill corpus carries the
refusal"; B-036-1 adds `decision_boundary` "a module in `src/ai_engineering/` … the name
deliberately avoids the word `boundary` alone". Command:
```
$ test -f src/ai_engineering/decision_boundary.py; echo "exit=$?"
exit=1
```
Verdict: **OK** — no `decision_boundary.py` today, matching the claimed gap.

### O-2 — Validation table row 1, evidence.py
Spec: "`src/ai_engineering/evidence.py` (445 ln) · `verify()` / `VERIFIED` /
`EVIDENCE_MISSING` / `EVIDENCE_STALE` / `EVIDENCE_DIGEST_MISMATCH` /
`EVIDENCE_EXECUTED_FAIL`". Commands:
```
$ wc -l src/ai_engineering/evidence.py
445 src/ai_engineering/evidence.py
$ grep -n 'def verify' src/ai_engineering/evidence.py
310:def verify(
$ grep -n 'EVIDENCE_MISSING' src/ai_engineering/evidence.py
34:MISSING = "EVIDENCE_MISSING"
$ grep -n 'EVIDENCE_STALE\|EVIDENCE_DIGEST_MISMATCH\|EVIDENCE_EXECUTED_FAIL\|VERIFIED' src/ai_engineering/evidence.py
36:STALE = "EVIDENCE_STALE"
37:DIGEST_MISMATCH = "EVIDENCE_DIGEST_MISMATCH"
40:EXECUTED_FAIL = "EVIDENCE_EXECUTED_FAIL"
41:VERIFIED = "EVIDENCE_VERIFIED"
42:VERIFIED_WITH_WARNING = "EVIDENCE_VERIFIED_WITH_WARNING"
374:    return _verification("PASS", VERIFIED)
```
Verdict: **OK** — 445 lines exactly as claimed; every named symbol exported.

### O-3 — Validation table row 2, verify_cold.py
Spec: "`src/ai_engineering/verify_cold.py` (spec 030) · `Verdict` (PASS / FAIL /
BLOCKED)". Commands:
```
$ wc -l src/ai_engineering/verify_cold.py
61 src/ai_engineering/verify_cold.py
$ grep -n 'class Verdict' src/ai_engineering/verify_cold.py
20:class Verdict(StrEnum):
$ sed -n '20,25p' src/ai_engineering/verify_cold.py
class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
```
Verdict: **OK** — module exists, `Verdict` enum has exactly PASS/FAIL/BLOCKED.

### O-4 — Validation table rows 3 & 5, contract.py
Spec: "`src/ai_engineering/contract.py` (specs 026-033) · `audit_one()` — lanes:
`_output_contract_problems`, `_load_tier_problems`, `_incorrect_correct_problems`,
`_corpus_problems`, `_dispatcher_problems`" and "`_anti_rationalization_problems` ("has no
anti-rationalization section naming an excuse and answering it" = refused)". Commands:
```
$ wc -l src/ai_engineering/contract.py
642 src/ai_engineering/contract.py
$ grep -n 'def audit_one' src/ai_engineering/contract.py
161:def audit_one(path: Path) -> list[str]:
$ grep -n '_output_contract_problems\|_load_tier_problems\|_incorrect_correct_problems\|_corpus_problems\|_dispatcher_problems' src/ai_engineering/contract.py
206:    found.extend(_corpus_problems(path.parent, name))
210:    found.extend(_output_contract_problems(path.parent, name))
211:    found.extend(_incorrect_correct_problems(path.parent, name))
212:    found.extend(_load_tier_problems(path.parent, name))
213:    found.extend(_dispatcher_problems(path.parent, name))
386:def _corpus_problems(folder: Path, name: str) -> list[str]:
448:def _output_contract_problems(folder: Path, name: str) -> list[str]:
465:def _incorrect_correct_problems(folder: Path, name: str) -> list[str]:
480:def _load_tier_problems(folder: Path, name: str) -> list[str]:
506:def _dispatcher_problems(folder: Path, name: str) -> list[str]:
$ grep -n '_anti_rationalization_problems' src/ai_engineering/contract.py
209:    found.extend(_anti_rationalization_problems(path.parent, name))
429:def _anti_rationalization_problems(folder: Path, name: str) -> list[str]:
```
Verdict: **OK** — `audit_one` present, all five named lanes present, anti-rationalization lane present.

### O-5 — Validation table row 6, cost.py
Spec: "`src/ai_engineering/cost.py` (spec 029) · `calibrate()` — … fails closed without
consent; its docstring cites deepsec and headstart". Commands:
```
$ wc -l src/ai_engineering/cost.py
109 src/ai_engineering/cost.py
$ grep -n 'def calibrate' src/ai_engineering/cost.py
47:def calibrate(
$ grep -in 'deepsec\|headstart' src/ai_engineering/cost.py
6:absent consent, it fails closed (deepsec `calibrate.sh` made mandatory, headstart's ArXiv
```
Verdict: **OK** — `calibrate()` present; docstring cites deepsec and headstart.

### O-6 — Validation table row 7, capability.py
Spec: "`src/ai_engineering/capability.py` (capability specs 010/012/014/021, `feat(capability):
enforce declared actions` 2026-08-13) · `preflight` — fail-closed declarations".
```
$ wc -l src/ai_engineering/capability.py
432 src/ai_engineering/capability.py
$ grep -n 'def preflight' src/ai_engineering/capability.py
365:def preflight(
```
Verdict: **OK** — module present, `preflight` exported.

### O-7 — Validation table row 8, trim.py
Spec: "`src/ai_engineering/trim.py` (spec 033) · `trim_output()`". Command:
```
$ wc -l src/ai_engineering/trim.py
48 src/ai_engineering/trim.py
$ grep -n 'def trim_output' src/ai_engineering/trim.py
25:def trim_output(text: str, max_lines: int = 80) -> str:
```
Verdict: **OK**.

### O-8 — Validation table row 9, decision_fw.py
Spec: "`src/ai_engineering/decision_fw.py` (spec 034) · `named()` — RICE / Effort/Value /
Kano, an unnamed ranking is refused; its docstring cites contains-studio". Commands:
```
$ wc -l src/ai_engineering/decision_fw.py
40 src/ai_engineering/decision_fw.py
$ grep -n 'def named' src/ai_engineering/decision_fw.py
31:def named(rationale: str) -> str | None:
$ grep -n 'RICE\|Effort\|Value\|Kano' src/ai_engineering/decision_fw.py
3:... RICE, Effort/Value, or
4:Kano — so the ranking is repeatable ...
34:"ranked by impact" names no framework — refused. "RICE" normalises to "rice".
$ grep -in 'contains-studio' src/ai_engineering/decision_fw.py
6:supports (contains-studio).
```
Verdict: **OK** — `named()` present, RICE/Effort-Value/Kano present, refusal of unnamed
ranking present, docstring cites contains-studio.

### O-9 — git-history provenance for evidence.py and capability.py
Spec: "evidence.py 2026-08-14, capability.py 2026-08-13". Commands:
```
$ git log --format='%h %ad' --date=short -- src/ai_engineering/evidence.py | tail -1
0c957767 2026-08-14
$ git log --format='%h %ad' --date=short -- src/ai_engineering/capability.py | tail -1
da915827 2026-08-13
```
Verdict: **OK** — first commits match the claimed dates exactly.

### O-10 — spec 035 untouched at its digests
Spec: "labels 035 as superseded at its digests … 035's spec/plan bytes stay frozen at their
approval digests"; "supersedes 035". Commands:
```
$ grep -n 'supersedes' specs/035-adoption-of-reference-patterns/spec.md
7:supersedes: ""
$ git diff --stat HEAD -- specs/035-; echo "diff-exit=$?"
(no output); diff-exit=0
```
Verdict: **OK** — 035's own `supersedes:` is still `""` (it is superseded *by* this record,
not self-superseding), and `git diff` against HEAD shows zero changes under `specs/035-`.

### O-11 — five (or more) existing modules use the bare word `boundary`
Spec: "five existing modules already use the word `boundary` alone" / "avoids the five
existing uses". Command:
```
$ grep -rln 'boundary' src/ai_engineering/*.py | wc -l
13
```
Verdict: **OK** — 13 modules use the bare word, comfortably ≥5. (Semantics of all 13
unverified — see U-3.)

### O-12 — skill_eval admits the claimed case shapes
Spec: "`tests/skill_eval.py`'s `_TRIGGER`/`_REFUSAL` admit … quoted situations and
`Not for … — …` refusals". Command:
```
$ grep -n '_TRIGGER\|_REFUSAL' tests/skill_eval.py
47:_TRIGGER = re.compile(r'"([^"]+)"')
55:_REFUSAL = re.compile(r"Not for ([^.]*?)\s*[—:]\s*([^.]+)")
83:            "claims": [phrase.lower() for phrase in _TRIGGER.findall(text)],
86:                for subject, target in _REFUSAL.findall(text)
```
Verdict: **OK** — `_TRIGGER` matches `"quoted"` situations; `_REFUSAL` matches
`Not for … — …`. The shapes the B-036-2 corpus rows must take exist in the harness.

### O-13 — the wayfinder W-02 source link exists
Spec: "Source link recorded for checkability: `.ai/research/reports/04-wayfinder/report.md`
(W-02, Unknown → CANNOT JUDGE)". Commands:
```
$ test -f .ai/research/reports/04-wayfinder/report.md && echo "wayfinder-report EXISTS"
wayfinder-report EXISTS
$ grep -n 'W-02' .ai/research/reports/04-wayfinder/report.md | head -3
59:| W-02 | **Sección "Unknown"** — ... el revisor reporta `CANNOT JUDGE` y para ...
103:2. **W-02 (Unknown section)** → ... reportar como `U<number>: CANNOT JUDGE` ...
145:Valor: El patrón de verificación binaria (W-01) + Unknown (W-02) son ...
```
Verdict: **OK** — report exists and W-02 is the Unknown ⇒ CANNOT JUDGE guard, matching the
cited provenance.

### O-14 — referenced policy/workflow files exist
Spec cites `policy/cost-thresholds.toml`, `policy/capability-manifest.schema.json`,
`.github/workflows/check.yml`, and the three `corpus.md` files. Commands:
```
$ test -f policy/cost-thresholds.toml && echo "cost-thresholds EXISTS"
cost-thresholds EXISTS
$ test -f policy/capability-manifest.schema.json && echo "capability-manifest EXISTS"
capability-manifest EXISTS
$ test -f .github/workflows/check.yml && echo "check.yml EXISTS"
check.yml EXISTS
$ ls -d .agents/skills/ai-spec .agents/skills/ai-review .agents/skills/ai-verify
.agents/skills/ai-review
.agents/skills/ai-spec
.agents/skills/ai-verify
```
Verdict: **OK** — policy thresholds, capability manifest schema, CI workflow and the three
target skills all exist. (Those three corpora carry zero `Not for` refusals today — 0 each —
which is consistent with B-036-2 being planned work, per U-1.)

### O-15 — the spec 034 corpus precedent exists in the tree
Spec: "the same generic lane that carries the spec 034 named-framework precedent
(named-framework precedent (spec 034) proves the corpus mechanism)". Commands:
```
$ ls -d specs/034*
specs/034-appendix-notes-decision-frameworks-and-constellation
$ grep -rln 'RICE\|Effort/Value\|Kano' .agents/skills/*/corpus.md
.agents/skills/ai-report/corpus.md
.agents/skills/ai-review/corpus.md
```
Verdict: **OK** — spec 034 exists and its named-framework corpus rows are present in two
skills' corpora (ai-report, ai-review). Note: those corpora contain no literal
`Not for … — …` refusal today; spec 034 asserts its rule via the quoted-trigger lane and 036
itself admits (Unresolved) "`tests/skill_eval.py` has no content assertion today for either
the named-framework or boundary rules" — so this is consistent, not a contradiction.

---

## What I could not test and why

- **The B-036-1/2/3 acceptance runs** (`pytest … test_036_boundary.py` / `-k undecidable` /
  `test_036_validation.py`, and "the boundary cases are counted" in `skill_eval.py`): the
  fixture files and corpus rows do not exist at `b351f267`, so the commands cannot be
  executed. The spec states this is expected ("do not exist until the approved plan writes
  them") — the passing counts are goals, not current state, and unverifiable today.
- **`just check` tree-green claim** ("the gate proves it clean with the same inherited
  `madr.validate` red and no fifth failure"): deliberately not run — the challenge brief
  forbids whole-suite commands; also the fixtures that the gate would run are absent, so a
  full gate result at this commit cannot represent the spec's intended state.
- **Module ↔ spec-number provenance** for specs 013-034 attributions (evidence.py's
  calibration "formalised in spec 029", contract.py "specs 026-033", cost/trim/decision_fw
  spec numbers): module existence, named symbol and external docstring cites were all
  checked; I did not open every one of specs 013-034 to confirm each numeric cross-reference
  (budget). The two git-date claims (the only numeric history the table asserts) were
  checked and match exactly.
- **Semantics of all 13 `boundary` usages**: only the count (claims ≥5) was verified; the
  council's "filesystem, word and data boundaries" reading of each file was not re-derived.
- **The capability-manifest ↔ classifier integration** ("the classifier reads its
  declarations from the capability manifest and never defines its own permission model"):
  describes planned/unbuilt B-036-1 behaviour — nothing to execute until the module exists.
- **Behavioural semantics of module internals** beyond exported symbols (e.g. cost
  "fails closed without consent", trim "failure lines never elided", verify_cold "no write
  tools, uncertain check = fail"): the named contract symbol exists for each row, but I did
  not unit-run the internals at this commit; those are the freshness test's job once written.

Overall: a corrected, internally consistent spec. Every claim the challenge brief could
execute came back **OK**; the only non-OK items are the three not-yet-buildable plan
acceptance commands and two read-from-memory cross-document attributions, which the spec
itself flags as pending or as second-reader work.