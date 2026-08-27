# Council — spec 043 "Ponytail audit cuts" (round 1)

Environment note, stated once so every output below is readable: commands ran through
/bin/sh in the repository root. `uv run python` could not warm its cache in this
sandbox (EPERM), so python commands ran with `.venv/bin/python` — the same interpreter
uv resolves to. `.venv` has no pytest module; that fact is itself an output below.
Nothing else substitutes for the spec's own commands.

## Round one — five lenses, isolated

Each lens read only the spec and the tree. Verdicts: WRONG / UNPROVEN / verified.

### Lens 1 — what does this cost?

- **C-1 — the canonical-JSON duplication is real and byte-exact.** Spec: "byte-identical
  `_canonical_json` in 4 modules". Command:

  ```
  .venv/bin/python -c 'import hashlib,pathlib,re
  for m in ("capability","evidence","madr","outcome"):
      s=pathlib.Path("src/ai_engineering",m+".py").read_text()
      f=re.search(r"def _canonical_json.*?(?=\n\ndef |\n\nclass |\Z)",s,re.S).group(0)
      print(m,len(f.encode()),hashlib.sha256(f.encode()).hexdigest()[:16])'
  ```

  Output: `capability 170 6cceb756fff7c77b / evidence 170 6cceb756fff7c77b / madr 170
  6cceb756fff7c77b / outcome 170 6cceb756fff7c77b`. **verified** — four copies, 170
  bytes each, same hash. The dedup is cheap and the claim is true.

- **C-2 — "six frontmatter parsers" looked off by one.** Command:

  ```
  grep -rn "def _frontmatter\|def frontmatter" src/ai_engineering/*.py
  grep -rn 'split("---' src/ai_engineering/*.py
  ```

  Output: intent.py:443, blocked.py:282, solution_intent.py:95, text.py:42 (four named
  functions) plus the inline split at contract.py:638 — the lens counted five. (The
  cross-read later refuted this; see the refuted section.)

- **C-3 — "four ISO-date validators" cannot be reproduced as a count.** Named validators
  found: `accept._date`, `acceptance._valid_date`, `acceptance_privacy._ISO_DATE` —
  three helpers; `fromisoformat` appears in seven modules (accept, acceptance, doctor,
  evidence, madr, readiness, surface). Whether the fourth exists depends on a
  definition the spec never gives. **UNPROVEN**.

- **C-4 — "five near-identical git subprocess wrappers": the five exist, the
  "near-identical" fits only three.** Command:

  ```
  grep -rn "def _git" src/ai_engineering/*.py
  ```

  Output: checkpoint.py:30 (→str), claim.py:41 (→CompletedProcess), madr.py:337
  (→bytes), plus uninstall.py:240 `_git_value` and uninstall.py:255
  `_git_value_global`. Three runners with different return contracts; two config
  getters that are not wrappers of the same call at all. **verified** with the
  adjective narrowed: the consolidation target is three, not five.

- **C-5 — the dead-code deletions shed only tens of tests, so the cost sentence is
  weak.** "each dead module still costs its test suite on every CI run":
  `grep -c "def test" tests/test_answer_key.py` → 8; `grep -c "def test"
  tests/test_ui.py` → 39; `grep -rc "def test_" tests/*.py` sums to 1674 in 123 files.
  Tens out of ~1.7k. (The cross-read refuted the proxy; see below.)

### Lens 2 — can we get out of it, going back?

- **R-1 — the retraction rationale lives outside version control, so the retracted
  state is the one part that does not come back by git.** Spec: "report 020 documents
  why". Command:

  ```
  git check-ignore -v .ai/reports/020-dead-module-removal-research.md; echo exit=$?
  ```

  Output: `.ai/.gitignore:1:*  .ai/reports/020-dead-module-removal-research.md` and
  `exit=0` — the file exists (19 KB, 214 lines) and is ignored. Four of the seven
  original cut targets were withdrawn on its authority; nothing in CI would notice if
  it vanished. **verified** (a reversibility defect of the governance, not of the code).

- **R-2 — D-043-01 is ticked as applied; the tree says it has not been.** Spec:
  "`[X]` **D-043-01 — Cut list applied in four ordered commits**" and the success
  example says "Given the repository at this spec's HEAD". Commands:

  ```
  git log --oneline --all --grep 043 | head -3
  git status --porcelain -- specs/043-ponytail-audit-cuts
  grep -rn "def _canonical_json" src/ai_engineering/*.py | wc -l
  ```

  Output: the three --grep hits are 034/042-era false matches on other digits — no 043
  commit exists; the spec directory is untracked (`??`); and the four
  `_canonical_json` copies are all still in place. The box certifies a past action
  ("applied") for a future state; front-matter status is `draft`. **WRONG** as written.

- **R-3 — the spec invokes AGENTS.md rule 4 as its defense and omits its duty.**
  Command:

  ```
  grep -n "No compatibility shims" AGENTS.md
  grep -ci changelog specs/043-ponytail-audit-cuts/spec.md
  ```

  Output: `4. No compatibility shims. Hard rename, hard delete; say it in the
  changelog.` and `0` — the word does not appear in the spec, and the four-commit plan
  has no changelog step. A landed cut without the entry is a rule breach that no
  `git revert` un-creates. **verified**.

### Lens 3 — the undecidable path

- **U-1 — the undecidable-path example cannot fail, so it verifies nothing.** Spec:
  "Then the module is kept — verified by `git grep` finding the module's name and
  `just check` reading `0 failed`." Command:

  ```
  git grep -l answer_key | head -4
  ```

  Output: `policy/module-status.toml / specs/029-evidence-executed-and-answer-keys/plan.md
  / specs/029-evidence-executed-and-answer-keys/spec.md
  / specs/030-cold-read-verification-and-revalidation/spec.md` — a kept module's name is findable
  whether or not it was ever undecidable, and `just check` is green before the cuts too
  (it is the pre-cut tree that reads `5 failed` per the spec's own baseline). The
  recipe does not distinguish "kept because evidence could not decide" from "never
  considered". **UNPROVEN** (vacuous verification).

- **U-2 — the baseline assumption is written backwards.** Spec: "any cut that changes
  a failing test outcome flags the cut as incorrect, not the tree." Read literally,
  flipping a *failing* test is what flags a cut; breaking a passing one is not
  mentioned — the opposite of the stated intent ("Tests currently passing remain the
  observable contract baseline"). And under the intended reading, cutting `ui.ask`
  collides with a passing test today:

  ```
  grep -rn "ui\.ask" src/ hooks/ surfaces/ tests/ --include=*.py | grep -v "def ask"
  ```

  Output: `tests/test_ui.py:636: assert ui.ask("Set up?", default) is answer` — the
  only caller is a green test the cut must delete, and the spec never says the test
  moves. **WRONG** (as written) / ambiguous (as intended).

- **U-3 — the success-path numbers are not reachable from this HEAD.** Spec: "verified
  by running `just check` and reading `0 failed` beside `2403 passed, 2 skipped` ...
  where the tree before the cuts read `5 failed`." Commands:

  ```
  .venv/bin/python -m pytest --collect-only -q 2>&1 | tail -1
  git log --oneline -1
  ```

  Output: `No module named pytest` (uv would fetch it; its cache is denied in this
  sandbox) and `e78bcb2f` — a HEAD with no cuts (R-2), so neither the after-numbers
  nor the "before" `5 failed` can be read from anything the council can run. The
  example describes a HEAD that does not exist yet, in past tense. **UNPROVEN**.

### Lens 4 — what is taken on trust?

- **T-1 — "41 findings" has no tree witness.** Command:

  ```
  grep -rn "41 findings" . --exclude-dir=.git 2>/dev/null
  ```

  Output: exactly one hit — `specs/043-ponytail-audit-cuts/spec.md:25`. The audit list
  itself lives in the gitignored `.ai/` tree (R-1). The number closing the problem
  statement is a trust item. **UNPROVEN** (trust named).

- **T-2 — the CONSTITUTION quotation is half in the document.** Spec: "(CONSTITUTION.md:
  only an authorized person may accept a risk, and unaccepting one needs the same
  authority)". Commands:

  ```
  grep -n -i "authorized person may accept" CONSTITUTION.md
  grep -rin "unaccept" CONSTITUTION.md; echo exit=$?
  ```

  Output: the first is at CONSTITUTION.md:76 ("Only an authorized person may accept a
  dated, evidenced risk"); the second prints nothing, `exit=1`. "Unaccepting" appears
  nowhere in the constitution. The second half of the cited authority model is the
  spec's paraphrase presented inside parentheses as a quote. **WRONG** (citation);
  directionally plausible, uncited.

- **T-3 — the biggest exclusion is justified by a risk record the cited spec says does
  not exist.** Spec: "spec_transaction Windows backend stays (spec-010 dated risk
  record)" and "doctrine yields to dated risk acceptance". Command:

  ```
  grep -n -A4 "## Accepted risks" specs/010-governed-agentic-engineering-foundation/spec.md
  ```

  Output: `765:## Accepted risks / 767:None. Every risk remains open until removed or
  explicitly accepted by authorized human or preapproved policy with complete evidence
  and expiry.` — spec-010 accepts zero risks. Searches for a record naming Windows
  (`grep -rn -i "windows" .ai/receipts/*.json policy/`) find nothing relevant. The
  ~810-line block is real (see F-1); its *governance shelter* is not. **WRONG** — the
  council's worst finding: the one item the spec refuses to cut for authority reasons
  rests on an authority the cited file denies.

- **T-4 — imagery.findings looked like a false grep claim.** Spec lists
  `imagery.findings` among "zero production callers"; the lens read executor.py's
  `imagery.stripped` call plus the docstring "it is why `findings` exists" as a call
  path. (The cross-read refuted this; see the refuted section.)

### Lens 5 — the example nobody wrote

- **E-1 — the denial-path example names a mechanism the doctor does not have.** Spec:
  "When `ai-eng doctor` runs after the cut, Then it fails closed — ... reading the
  missing symbol's name beside an `exit status 1`." Commands:

  ```
  grep -cE "import_module|importlib" src/ai_engineering/doctor.py
  grep -c "@check" src/ai_engineering/doctor.py
  ```

  Output: `0` and `26`. Doctor runs 26 checks; none imports the package's modules or
  probes symbols — it reads hook chains, receipts and cached state. After a cut that
  orphans a caller, doctor says nothing; the first red signal is a broken test, which
  is the thing U-2 says must not happen. The example nobody wrote is the
  counter-example: what `ai-eng doctor` prints today when `ui.ask` is deleted and
  `tests/test_ui.py:636` errors. **WRONG** (mechanism absent; see the refuted section
  for the softened cross-read verdict).

- **E-2 — "keeping the two sanctioned ones" has no referent.** D-043-01(d) cuts
  hook-layer duplicates "only, keeping the two sanctioned ones". Command:

  ```
  grep -rn "sanctioned" hooks/ policy/ docs/ 2>/dev/null; echo exit=$?
  ```

  Output: empty, `exit=1` — the only "sanctioned" in the repo is spec-043's own
  sentence. No marker, register or note names which two hook duplicates are
  sanctioned. The example nobody wrote: the command that shows a hook is sanctioned.
  **UNPROVEN**.

- **E-3 — no example covers the dedup's own success criterion.** The spec's four
  examples cover suite-green, import-clean, doctor-red and keep-on-doubt; none shows
  "each primitive lives once". The missing command is one line:

  ```
  grep -rc "def _canonical_json" src/ai_engineering/*.py | grep -v ":0" | wc -l
  ```

  Output today: `4` — the cut's own criterion is that this read `1`, and no example in
  the spec would catch a dedup that left two homes instead of one. **verified** (as a
  gap in the examples, with the command written).

- **E-4 — the drift claim's example pair is real and the spec understates it.** "each
  duplicated primitive drifts (loop_guard and _emit already sanitize differently)":

  ```
  grep -n "isprintable" hooks/loop_guard.py hooks/_emit.py
  ```

  Output: loop_guard.py:34 `f"\\x{ord(ch):02x}"` (escaped) vs _emit.py:223 `"?"`
  (replaced). Same job, different output — **verified**, and it strengthens the dedup
  case the examples never make.

## Round two — the cross-read

The five answers were shuffled and re-run against the tree: every refutation below is
a command this round actually executed, and every gap is something no single lens
raised.

### Gaps no single lens named

- **G-1 — the register fixture is a third, unwarned consumer of the move the success
  example celebrates.** No lens asked what breaks when the dedup stage lands.
  `tests/test_orphan_register.py` imports `wiring` and calls `wiring.module_status()`
  at lines 72, 84, 100 (and 132, the deferred-trio test); `policy/module-status.toml`
  carries `consumer = ""` deferred rows for answer_key/decision_boundary. The spec's
  success example wants `wiring.module_status` to raise ImportError/AttributeError
  after the cut — if that happens, this governance test goes red and `just check`
  fails. If it doesn't happen, the example is false. The spec never says the register
  reader moves to tests/, and moving it would edit a governance artifact spec-042
  claims authority over. Command (both consumers, one line):

  ```
  grep -n "module_status" tests/test_orphan_register.py src/ai_engineering/wiring.py
  ```

  Output: `72: rows = wiring.module_status() / 84: / 100: / 502: def module_status()
  -> dict[str, dict[str, str]]`.

- **G-2 — the spec's own plan has no changelog step, and the repo's convention proves
  the duty is real.** R-3 found the word missing; no lens connected it to the precedent
  that the sibling in-flight work honors. Command:

  ```
  git log --oneline -2
  ```

  Output includes `388c08e3 docs(changelog): tier retune entry for the dogfooding
  benchmark` — a changelog commit for a model-tier tune, while a 41-finding deletion
  plan schedules no entry. Rule 4's second clause is an obligation D-043-01's four
  commits do not carry.

- **G-3 — the cut's success criterion has no verification recipe anywhere in the
  plan.** E-3 wrote the missing command for canonical JSON; the general gap is that
  `just check` contains no dedup check — nothing in the acceptance stack would notice
  the primitives still living twice. Command:

  ```
  grep -n "^check:" justfile
  ```

  Output: `269:check: build sbom lint typecheck test cover security register skilleval
  evals counts intent-page lenses council map ran` — sixteen recipes, none of them
  "each primitive lives once".

- **G-4 — the withheld module is invisible to the spec.** The register fixture defers
  three modules; the spec's retraction list names two. Command:

  ```
  grep -n "constellation" tests/test_orphan_register.py specs/043-ponytail-audit-cuts/spec.md
  ```

  Output: `tests/test_orphan_register.py:132,135` (docstring and the deferred trio) and
  zero hits in the spec. If the delete stage walks "deferred" rows, constellation is in
  scope and unauthorized; if it walks the spec's list, the spec and the register
  disagree in writing.

### Findings cut for carrying no command

- The reading of "reviewers review the same code twice because it exists twice" as a
  checkable finding: a motive sentence with no observable that separates it from the
  duplication counts C-1..C-4 already carry. Cut.
- The reading of "every future change pays to read, test and keep those copies green"
  as a per-cut cost figure: no timing or effort measurement is possible from the tree
  (pytest is not even installed here — U-3's output), so a number would have been
  invented. Cut rather than proxied.
- The reading of D-043-01's "larger diff than an incremental trim" as a finding: the
  option text already concedes the cost and names the mitigation (per-cut commits,
  bisect); nothing in the tree contradicts it. Cut — no command could falsify it.

### Findings the cross-read refuted, with the command that refuted them

- ~~**C-2 — "six frontmatter parsers is WRONG; the tree has five parse sites."**~~
  Refuted: the count is six once the definition includes inline frontmatter
  recognizers, which is what "re-forks the same primitive" describes — intent.py:443,
  blocked.py:282, solution_intent.py:95, text.py:42, contract.py:638, and madr.py:181
  (`_parse`: `startswith((b"---\n", b"---\r\n"))` then `text.find("\n---\n", 4)`). The
  lens missed madr.py:181 because it grepped only `def _frontmatter` and
  `split("---`. Command:

  ```
  grep -rn 'startswith((b"---' src/ai_engineering/*.py
  ```

  Output: `src/ai_engineering/madr.py:181` (and 423, a second site in the same
  module). The spec's number stands; the finding is deleted.

- ~~**T-4 — "imagery.findings has a production caller via stripped(), so the grep
  verification sentence is WRONG."**~~ Refuted on the word "caller": the chain is
  one-directional — `executor.py:153` calls `imagery.stripped`; inside imagery,
  `stripped`'s SVG arm ends at `return _sanitised_svg(payload)` (line 141) and
  `findings` is never invoked from `stripped` — only mentioned in its docstring ("it is
  why `findings` exists") and a comment at 148. The only code call of `_svg_findings`
  is `findings` itself (imagery.py:193). So "zero production callers for
  imagery.findings" was true as grep would have shown it; the EP-254 retraction keeps
  the module, but it does not correct a false claim — the claim was not false. The
  finding confused "referenced by" with "called by". Commands:

  ```
  grep -n "findings\|return _sanitised_svg" src/ai_engineering/imagery.py | head -8
  grep -rn "findings(" src/ai_engineering/executor.py; echo exit=$?
  ```

  Output: `141: return _sanitised_svg(payload) / 170: def findings / 193: return
  _svg_findings(payload)` and executor: no match, `exit=1`. Finding deleted.

- ~~**C-5 — "the dead-code deletions shed only tens of tests, so the cost argument is
  weak."**~~ Refuted: `grep -c "def test"` undercounts parametrized expansion —
  `grep -rc "parametrize" tests/*.py` sums to 167 decorators across the suite, and CI
  collects through uv (`grep -n "setup-uv" .github/workflows/check.yml` → line 72),
  where the local `No module named pytest` (U-3) is an artifact of this sandbox, not
  of the tree's real cost. The suite is larger than the lens's proxy showed; the
  spec's harm sentence is not exaggerating. Finding deleted; C-1's materiality
  ranking survives it.

- ~~**E-1, hard edition — "doctor has no symbol probe at all, so the denial-path
  example is pure fiction."**~~ Refuted in its absolute form: doctor's 26 checks
  include chain-integrity machinery over the hook layer (`grep -n "chain_intact\|hook"
  src/ai_engineering/doctor.py | head -3` → the hook-chain check at doctor.py:504ff),
  so "names the missing symbol" is a small extension of an existing check, not an
  invention. The measured core stands — 0 of 26 checks import package modules (E-1's
  output) — but the recommendation changes from "rewrite the example" to "add the
  probe to the plan". Overstatement cut; finding kept in round one at lower severity.

## The two counts

- Gaps that appeared only after the cross-read: **4**
- Findings deleted for carrying no command or being refuted: **7**
