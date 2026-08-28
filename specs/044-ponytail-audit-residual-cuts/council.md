# Council — spec 044 "Ponytail audit residual cuts" (round 1)

Environment note, stated once so every output below is readable: commands ran in the
repository root; `python3` served the tomllib one-liners. Nothing substitutes for the
spec's own commands.

## Round one — five lenses, isolated

Each lens read only the spec and the tree. Verdicts: WRONG / UNPROVEN / verified.

### Lens 1 — what does this cost?

- **C-1 — ~650 src lines across eleven orphan modules.** Spec: "the harm: ~650 lines of
  wheel (src-side total for the eleven) plus their test modules". Command:

  ```
  wc -l src/ai_engineering/{constellation,decision_fw,decision_boundary,intake,trim,versions,lane_merge,loopgate,skillify,verify_cold,evidencing}.py | tail -1
  ```

  Output: `  645 total`. **verified** — within 1% of the estimate.

- **C-2 — the 25 holds; "twenty after family (a)" does not.** Spec: "the `sys.path.insert
  + # noqa: E402` idiom in twenty-five pytest modules (twenty after family (a) deletes
  the orphan suites...)". Commands:

  ```
  grep -rln "noqa: E402" tests/ --include="test_*.py" | wc -l
  ```

  Output: `25`, and a companion sweep found `10` of those files importing orphans —
  25 − 10 = **15** remain, not 20. **WRONG** on the residual. (Confirmed by the
  cross-read.)

- **C-3 — five digest-pinned loaders, one `_parse_legacy`.** Spec: "five digest-pinned
  policy loaders". Command:

  ```
  grep -c "_EXPECTED_SCHEMA_DIGEST" src/ai_engineering/{acceptance,capability,evidence,madr,outcome}.py && grep -rln "def _parse_legacy" src/ai_engineering/*.py
  ```

  Output: `1` × 5 files; `src/ai_engineering/acceptance.py`. **verified**.

- **C-4 — four `git ls-files` readers; "five `git -C` wrappers" read as unverifiable.**
  Spec: "four `git ls-files` readers and five `git -C` wrappers". Command:

  ```
  grep -rln "ls-files" src/ai_engineering/*.py && grep -rln "git -C" src/ai_engineering/*.py
  ```

  Output: 4 ls-files files; literal `git -C` in 2. **UNPROVEN** (as scanned — the
  cross-read later inverted it; see the refuted section).

### Lens 2 — can we get out of it, going back?

- **R-1 — `git revert` does not restore a deleted module's ecosystem in one command.**
  Spec: "`git revert` restores any module in one command". Command:

  ```
  grep -rn "from ai_engineering\." tests/ --include="*.py" | grep -E "constellation|decision_fw|decision_boundary|intake|trim|versions|lane_merge|loopgate|skillify|verify_cold|evidencing" | wc -l
  ```

  Output: `15` import lines across a dozen test files. **WRONG** as an unqualified
  sentence — reinstatement is a multi-file restore (module + tests + register row +
  pythonpath wiring).

- **R-2 — `test_036_validation.py` importlib-imports orphans via its ROWS loop.**
  Spec: "the deletion list is the eleven modules plus every test file that imports one of
  them". Command:

  ```
  grep -n "import_module\|ROWS" tests/test_036_validation.py | head -6
  ```

  Output: `22:ROWS = [` / `24: ("verify_cold", ...)` / `29: ("trim", ...)` / `30:
  ("decision_fw", ...)` / `40: module = importlib.import_module(f"ai_engineering.{name}")`.
  **verified** — a second coupling layer the spec treats parenthetically.

- **R-3 — the corpus names nine of the eleven; `constellation` is genuinely absent.**
  Spec: "`constellation` not at all". Command:

  ```
  grep -rn "constellation" .agents/skills/ --include="*.md" --include="*.txt" 2>&1; grep -rn "constellation" policy/ --include="*.toml" | head -2
  ```

  Output: no corpus hits; `policy/skill-map-accepted.toml:104`,
  `policy/module-status.toml:39`. **verified** — corpus coupling real for nine names,
  zero for constellation.

- **R-4 — design provenance is reachable; true because the spec layer is untouched.**
  Spec: "the design work lives in the specs and the git history, not in the bytes".
  Command:

  ```
  git log --oneline -- src/ai_engineering/constellation.py src/ai_engineering/decision_fw.py src/ai_engineering/loopgate.py src/ai_engineering/trim.py | head -6
  ```

  Output: six feat commits, each citing its spec (031/033/034/036/037). **verified**.

- **R-5 — `hooks/loop_guard.py` reasons about `trim` in a comment, not an import.**
  Command: `grep -n "trim" hooks/loop_guard.py`. Output: `95: # and the trim below drops
  the ones nothing has touched.` **verified** — the sweep correctly finds zero
  production importers; the concept survives in prose.

### Lens 3 — the undecidable path

- **U-1 — this lens's census re-read was itself wrong.** Spec: "A tomllib census on this
  branch reads 19 rows, of which 16 have no production importer". Command:

  ```
  grep -c 'name = ' policy/module-status.toml
  ```

  Output: `19`; the lens read 17 non-consumers where the true count is 16 — exactly the
  spec's number. **WRONG** as this lens stated it. (Refuted by the cross-read; the
  omitted name inside the finding survives as G-2.)

- **U-2 — `sbom` and `scan` have callers the census sentence misses.** Spec: the census
  framing placing `sbom` among the caller-less. Command:

  ```
  grep -n 'from ai_engineering import sbom' .github/workflows/release.yml; grep -n 'from ai_engineering import scan' justfile
  ```

  Output: `release.yml:110`; `justfile:107`. **verified** — the register's own reasons
  ("no local command invokes it yet") are contradicted by `just sbom` (justfile:47) and
  `just security`. (One cross-reader dismissed the workflow import as a heredoc;
  another's justfile evidence sustained the finding — where one refutes and another
  agrees, it stays.)

- **U-3 — the Excluded list is unenforceable as specified.** Spec: "its name is recorded
  under this spec's Excluded list in the changelog entry". Command:

  ```
  grep -n 'Excluded' CHANGELOG.md || echo "NO EXCLUDED HEADER FOUND"
  ```

  Output: `NO EXCLUDED HEADER FOUND`. **UNPROVEN** — the changelog has `### Removed`,
  no Excluded convention, no enforcing tool.

- **U-4 — `test_cli_migration.py`'s dynamic imports were read as uncovered residual
  callers.** Command:

  ```
  grep -n 'import_module\|__import__' tests/test_cli_migration.py
  ```

  Output: seven `import_module` calls naming digest, report, plan, exception.
  **UNPROVEN** as framed. (Refuted by the cross-read; see the refuted section.)

- **U-5 — `answer-key.yaml` is read by the module the spec cuts, and the record's only
  enforcement dies in family (a).** Spec: "`answer_key.valid`/`apply` and root
  `answer-key.yaml`". Command:

  ```
  ls -la answer-key.yaml && grep -n 'answer-key.yaml' src/ai_engineering/answer_key.py
  ```

  Output: 268-byte file; `answer_key.py:156: p = Path("answer-key.yaml")`. **UNPROVEN**.

### Lens 4 — what is taken on trust?

- **T-1 — the whole-tree audit has no committed witness.** Spec: "A whole-tree
  over-engineering audit ran on 2026-08-27 (four independent scans plus a verification
  pass; net estimate -1,900 lines src-side)". Command:

  ```
  git log --all --since="2026-08-27" --grep="audit" --oneline
  ```

  Output: empty. **UNPROVEN** — a trust item closing the problem statement.

- **T-2 — report 020 is gitignored.** Spec: "Research report 020 swept the
  dynamic-resolver sites for 043's seven targets only". Command:

  ```
  git check-ignore .ai/reports/020-dead-module-removal-research.md
  ```

  Output: the path echoed, exit 0. **UNPROVEN** — unverifiable from committed state.

- **T-3 — EP-254/EP-016/EP-176 exist committed in docs/requirements.toml.** Command:

  ```
  grep -n 'id = "EP-254"\|id = "EP-016"\|id = "EP-176"' docs/requirements.toml
  ```

  Output: `182:id = "EP-016"` / `1310:id = "EP-176"` / `1865:id = "EP-254"`.
  **verified** — D-044-02's keep-list rests on committed artifacts.

- **T-4 — the census counts hold; the prose names one row fewer than the register.**
  Command: tomllib census. Output: `total: 19 orphans: 16`, list including `skillmap`.
  **verified** with a rider — the prose names 15 of 16; `skillmap` is silently unnamed
  (survives as G-2).

- **T-5 — "(C-1 verified four byte-identical copies)" was read as a misattribution.**
  Command: `grep -A3 '^C-1' specs/043-ponytail-audit-cuts/council.md`. Output: `- **C-1 —
  the canonical-JSON duplication is real and byte-exact.**`. **UNPROVEN** as read.
  (Refuted by the cross-read; see the refuted section.)

### Lens 5 — the example nobody wrote

- **E-1 — zero-caller `spec.self_contained` has no example exercising its deletion.**
  Command:

  ```
  grep -rn "self_contained" src/ hooks/ surfaces/ git-hooks/ --include="*.py" | grep -v "def self_contained"
  ```

  Output: no hits. **verified** — the sweep is right and no example would notice a cut
  that left a caller behind.

- **E-2 — `spec_transaction.publish`'s discarded return has no example either.** Spec:
  "returns a `Published` both production callers discard". Command:

  ```
  grep -n "publish(" src/ai_engineering/spec.py
  ```

  Output: `1244:            transaction.publish(pending, final_name)`. **verified**.
  (A cross-reader located the missing second caller; see G-5.)

- **E-3 — D-044-03's "asserted byte-for-byte" is not what the acceptance suite asserts.**
  Spec: "same refusal messages (the messages are contractual — several are asserted
  byte-for-byte)". Command:

  ```
  grep -n "ACCEPTANCE_MALFORMED" tests/test_acceptance.py
  ```

  Output: four assertions, all comparing the code, none the message text. **WRONG** as a
  description of the suite. (Refined by the cross-read: see G-6.)

- **E-4 — `test_decision_and_notes.py` tests both the orphan and a survivor.** Spec:
  "every test file the same AST sweep shows importing one of them". Command:

  ```
  grep -n "def test_\|contract\.\|decision_fw\." tests/test_decision_and_notes.py
  ```

  Output: six test functions — two exercising `contract.audit_one`, four `decision_fw`.
  **verified** as a mixed-file observation. (Its stronger clause was refuted; see the
  refuted section.)

- **E-5 — the changelog Excluded list does not exist and no command can verify its
  future existence.** Command: `grep -n "Excluded\|excluded\|044" CHANGELOG.md`. Output:
  no hits. **UNPROVEN** — convergent with U-3 from a second seat.

## Round two — the cross-read

The five answers were relabelled A–E, shuffled, and each seat received the other four
and not its own. Every refutation below is a command this round actually executed. Three
refutation attempts failed and are recorded under the refuted heading rather than the
findings they aimed at; where one seat refuted and another sustained (the sbom caller,
the publish count), the finding stayed.

### Gaps no single lens named

- **G-1 — the register's scan/sbom rows are contradicted by the justfile the sweep
  claims to cover.** Command:

  ```
  grep -n 'ai_engineering.sbom\|from ai_engineering import scan' justfile
  ```

  Output: `47: uv run python -m ai_engineering.sbom dist/*.whl`; `107: ... from
  ai_engineering import scan ...`. Both rows carry `consumer = ""` while `just sbom` and
  `just security` invoke them at gate time.

- **G-2 — `skillmap` is the sixteenth orphan and the prose never says its name.**
  Command:

  ```
  python3 -c "import tomllib; data=tomllib.load(open('policy/module-status.toml','rb')); print(sorted(m['name'] for m in data['module'] if m['status']!='consumer'))"
  ```

  Output: a 16-name list ending `..., 'skillmap', 'trim', 'verify_cold', 'versions']`.
  The spec's sentence names fifteen.

- **G-3 — the sweep's completeness was asserted, never re-shown: two more importing test
  files surfaced when a cross-reader re-ran it.** Command:

  ```
  grep -rn "from ai_engineering import intake\|from ai_engineering import decision_boundary" tests/ --include="*.py"
  ```

  Output: `tests/test_037_intake.py:13` and `tests/test_036_boundary.py:12`. Neither
  file was named by any seat; the family-(a) rule covers both by construction, but no
  example re-runs the sweep.

- **G-4 — the assumption's loader list omits `paths.load`, a by-path loader 043's own
  record knew about.** Command:

  ```
  grep -n "spec_from_file_location\|exec_module" src/ai_engineering/paths.py
  ```

  Output: `61: spec = importlib.util.spec_from_file_location(name, source)` / `68:
  spec.loader.exec_module(module)`. It reads only `hooks/*.py`, so it cannot reach the
  eleven — but the assumption sentence is false as written.

- **G-5 — the second discarded `publish` at accept.py:249 completes the "both
  production callers" count.** Command:

  ```
  grep -n "publish(" src/ai_engineering/accept.py
  ```

  Output: `216: def publish(...)` / `249: writer.publish(pending, final)` (return
  unassigned) / `429: published = publish(root, slug, record)`. One seat's two-file
  grep missed this caller; another seat found it.

- **G-6 — what the gate actually asserts about refusal messages: codes in one suite,
  fragments in another, whole strings nowhere.** Command:

  ```
  grep -n "assert.*indents a line\|assert.*repeats the key" tests/test_mut_acceptance.py
  ```

  Output: `300` / `329` — `assert "... in str(_rejected(block))"`. The mutation suite
  holds message fragments; nothing holds byte-for-byte strings. D-044-03 overstates the
  contract — but the contract is not empty.

- **G-7 — family (a) deletes two mixed test files and never says so; the census shows
  the coverage survives anyway.** Command:

  ```
  grep -rln "audit_one" tests/*.py | wc -l
  ```

  Output: `9` files exercise contract.audit_one; family (a) deletes two of them
  (test_skillify.py, test_decision_and_notes.py), leaving seven — no coverage cliff,
  but the rule is silent on mixed files.

- **G-8 — the corpus coupling is a hard string-match for loopgate and nothing at all
  for verify_cold; the spec treats every name as equally soft prose.** Command:

  ```
  grep -n "loopgate" tests/test_skill_bounds.py
  ```

  Output: `35: assert "loopgate" in body, ...`. D-044-01 handles loopgate's
  corpus-drops-the-name case; for verify_cold the coupling is zero — the reinstatement
  cost differs per name and the record does not say so.

### Findings cut for carrying no command

- "every CI second pays for code no command runs": a wall-clock claim about CI; no
  command available to a lens times a gate. Cut rather than timed.
- The "~50 files" diff estimate: only a landed `git diff --stat` measures it; a number
  would have been invented. Cut.
- "the gate's baseline is the current green on `main` (b4a525c9)": b4a525c9 is a
  verified ancestor of HEAD, but greenness is a property of a run, not a tree. Cut.
- "skill corpus prose naming deleted modules stays valid as prose": a claim about future
  agent runs; the tree has no instrument for it. Cut.
- "a future orchestrator spec may want lane_merge/loopgate back": a prediction about
  requirements that do not exist. Cut.
- The audit's "net estimate -1,900 lines src-side": the scans' outputs were never
  committed; the estimate cannot be recomputed. Cut rather than re-estimated.
- Reachability of dynamic-import sites report 020 never scoped: deciding them needs a
  new sweep; no existing command decides them. Cut, with the boundary recorded here.
- Whether corpus couplings name a module or a concept: a judgment about authorial intent
  in prose; the tree cannot tell instrument from homonym. Cut.

### Findings the cross-read refuted, with the command that refuted them

- ~~**U-1 — "17 of the 19 rows have status≠consumer; the count is 17, not 16."**~~
  Refuted independently by three cross-readers; the register reads 19 rows with exactly
  3 consumer rows. Command:

  ```
  python3 -c "import tomllib; data=tomllib.load(open('policy/module-status.toml','rb')); print(len(data['module']), sum(1 for m in data['module'] if m['status']!='consumer'))"
  ```

  Output: `19 16` — the spec's count. The buried observation (the prose omits
  `skillmap`) survives as G-2.

- ~~**U-4 — `test_cli_migration.py`'s dynamic imports are uncovered residual callers.**~~
  Refuted: digest and plan no longer exist (the imports sit inside
  `pytest.raises(ModuleNotFoundError)` as negative tests); report and exception are live
  cli VERBS modules. Command:

  ```
  ls src/ai_engineering/digest.py src/ai_engineering/plan.py 2>&1; ls src/ai_engineering/report.py src/ai_engineering/exception.py
  ```

  Output: two `No such file or directory` lines; both report.py and exception.py listed.
  Deleted.

- ~~**T-5 — "(C-1 verified four byte-identical copies)" cites a measurement not made in
  that form.**~~ Refuted: the count of four was inside the very spec sentence C-1 tested
  ("byte-identical `_canonical_json` in 4 modules"), and C-1's output showed four
  same-hash copies. The dedup has since landed entirely. Command:

  ```
  grep -rln "_canonical_json" src/ai_engineering/*.py; echo "exit=$?"
  ```

  Output: nothing, `exit=1` — `intent.canonical_json` is the single home today. Deleted.

- ~~**C-4 — the five `git -C` wrappers "cannot be verified by this tree scan"
  (UNPROVEN).**~~ Refuted by the scan itself: the wrappers build argv lists, so the
  literal string `git -C` never appears and the lens's grep was the artifact. Command:

  ```
  grep -rl '"-C"' src/ai_engineering/*.py | wc -l
  ```

  Output: `10` files, including all five the spec names (checkpoint.py:46, claim.py:44,
  madr.py:339, argv form). The finding inverts: five is an under-count, not an
  unverifiable claim. Deleted; the corrected number informs the chairman's page.

- ~~**E-4 — deleting `test_decision_and_notes.py` kills `contract.audit_one` coverage
  "with no replacement".**~~ Refuted by census: Command: `grep -rln "audit_one"
  tests/*.py | wc -l`. Output: `9`; after family (a) deletes two, seven remain. The
  surviving half moves to G-7; the coverage-loss clause is deleted.

## The two counts

- Gaps that appeared only after the cross-read: **8**
- Findings deleted, for carrying no command or for being refuted: **13**
