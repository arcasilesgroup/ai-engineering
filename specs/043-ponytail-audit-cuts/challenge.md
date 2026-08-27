# Challenge — spec 043 (ponytail-audit-cuts), round 1

Reviewer: Challenge043 (independent context: spec + tree only; .ai/reports/019* not read, per brief).
Spec on disk was **rewritten mid-session** (mtime `Aug 27 03:56:46 2026`, file untracked: `?? specs/043-ponytail-audit-cuts/spec.md`). Findings below are anchored to the CURRENT text; the earlier text's defects are recorded as F12.

Sandbox note: `uv run` fails here (`Failed to initialize cache at ~/.cache/uv … Operation not permitted`) and pytest cannot allocate a TMPDIR (`No usable temporary directory found`). Where that blocked a claim, the equivalent interpreter (`.venv/bin/python`, the same one `uv run` resolves to) was used and the block is pasted.

---

## F1 — WRONG (internal contradiction). Worst finding.

> "Then the gate is green — verified by running `just check` and reading `0 failed` beside `2403 passed, 2 skipped` in the tail, **where the tree before the cuts read `5 failed`**." (Examples, success path)

> "Tests **currently passing** remain the observable contract baseline" (Assumptions)

Both cannot be true. If the pre-cut tree at this spec's HEAD reads `5 failed`, the assumption "tests currently passing" is false now and the baseline sentence is fiction; if the tree is green, the `5 failed` figure is invented. The success-path paragraph also speaks in past tense ("verified by running") for a check that cannot have been made against a cut that has not landed.

```
$ grep -n "5 failed\|currently passing" specs/043-ponytail-audit-cuts/spec.md
125:`2403 passed, 2 skipped` in the tail, where the tree before the cuts read `5 failed`.
112:- Tests currently passing remain the observable contract baseline; any cut that changes
```

Attempted resolution by running it — blocked in this context:

```
$ just check
uv build
error: Failed to initialize cache at `/Users/somebody/.cache/uv`
  Caused by: failed to open file `/Users/somebody/.cache/uv/sdists-v9/.git`: Operation not permitted (os error 1)
error: recipe `build` failed on line 39 with exit code 2
```

(The `2403 passed, 2 skipped` and `5 failed` numbers are therefore also individually UNPROVEN here — see Untestable list — but the contradiction between the two sentences is a text fact and stands regardless of which number is right.)

## F2 — WRONG. `executor.Sandbox.connect` is not the "exercised half" of EP-176.

> "executor.Sandbox.connect/.secret + capability.Action.connect/use_secret — the exercised half of PROVEN row EP-176 (\"secrets stay gated\")" (D-043-01 withdrawals)

The row's named evidence commands do not reach `connect`:

```
$ sed -n '1310,1313p' docs/requirements.toml
id = "EP-176"
verdict = "PROVEN"
subject = "self-grant refused, and publication, secrets and deploy stay gated"
evidence = "pytest tests/test_record.py::test_an_agent_cannot_grant_itself_a_bypass tests/test_mut_outward.py; pytest tests/test_executor.py -k secret"
```

```
$ grep -c "connect\|Sandbox" tests/test_mut_outward.py
tests/test_mut_outward.py:0
$ grep -rn "connect\|Sandbox" tests/test_record.py ; echo exit=$?
exit=1
$ grep -n "def test.*secret\|def test.*connect\|def test.*declared_host" tests/test_executor.py
165:def test_a_secret_is_handed_over_only_where_it_is_declared_and_never_logged(tmp_path, monkeypatch):
192:def test_a_declared_host_comes_back_and_an_undeclared_one_is_refused(tmp_path):
475:def test_a_secret_name_becomes_the_environment_name_this_process_would_have(monkeypatch, tmp_path):
```

`-k secret` selects lines 165 and 475 — the `.secret` tests. The connect test (192, `test_a_declared_host_comes_back…`) is not selected by any named evidence command, and neither other file mentions connect or Sandbox at all. Verdict: the `.secret` half of the claim is **verified**; the `.connect` half is **WRONG as stated** — "the exercised half" overstates. (Keep-conclusion may still be right — `connect` is reached from `capability.Action.connect`, capability.py:348 — but the cited governance evidence does not show it, and this spec's own doctrine is "each one is ticked by a command".)


## F3 — UNPROVEN. "ranked cut list of 41 findings".

> "A whole-repo over-engineering audit (2026-08-27, reports/019 lineage) produced a ranked cut list of 41 findings."

reports/019 is off-limits by assignment; report 020 — the artifact the spec does cite and I may read — carries 9 numbered findings and never says "41 findings":

```
$ grep -cE '^[0-9]+\. \*\*\[[0-9]+\]' .ai/reports/020-dead-module-removal-research.md
9
$ grep -n "41 finding" .ai/reports/020-dead-module-removal-research.md ; echo exit=$?
exit=1
```

The 41-count is attributable to 019 only; not verifiable from the permitted corpus.

## F4 — UNPROVEN. "keeping the two sanctioned ones" (hook-layer, D-043-01(d)).

No sentence in the spec or in report 020 names which two hook-layer duplicates are sanctioned:

```
$ grep -n -i "sanctioned\|hook-layer" .ai/reports/020-dead-module-removal-research.md ; echo done
done
```

A cut list whose (d) step says "keep two" without naming them is not executable by a stranger.

## F5 — UNPROVEN. "module-status deferred-register doctrine tension (finding 40)".

The tension itself is real and I verified both sides (see F9). The number "40" lives only in the 019 numbering, which is outside the permitted corpus.

## F6 — UNPROVEN wording (substance holds). "imagery.findings — named evidence command of PROVEN ledger row EP-254".

```
$ grep -n -A5 'id = "EP-254"' docs/requirements.toml
1865:id = "EP-254"
1866-verdict = "PROVEN"
1867-subject = "imagery output loses its metadata, passes a scan, and is sanitised when it is vector"
1868-evidence = "pytest tests/test_imagery.py"
1869-note = "the caller is `executor.Sandbox.write`, so an image that leaves through a governed capability has already lost what travelled beside it …"
```

The row names the test file, not the symbol `findings` — literally, "named evidence command of imagery.findings" is loose. Substantively the keep stands: the named command does execute the symbol heavily —

```
$ grep -c "def test" tests/test_imagery.py ; grep -c "findings(" tests/test_imagery.py
18
17
```

Deleting `findings` would break EP-254's PROVEN evidence. Wording imprecise; conclusion verified.

## F7 — verified (agreement). All seven "zero production callers" claims hold.

> "Independent grep verification confirmed the dead-code claims: zero production callers for `answer_key.py`, `decision_boundary.py`, `skeletons.seed_intent`, `imagery.findings`, `surface.receipt_binds_version`, `ui.ask`, `executor.Sandbox.connect/.secret`."

```
$ grep -rn --exclude-dir=__pycache__ "ui\.ask" src/ hooks/ ; echo exit=$?
exit=1
$ grep -rn --exclude-dir=__pycache__ "seed_intent" src/ hooks/ | grep -v skeletons.py ; echo exit=$?
exit=1
$ grep -rn --exclude-dir=__pycache__ "receipt_binds_version" src/ hooks/ | grep -v surface.py ; echo exit=$?
exit=1
$ grep -rn --exclude-dir=__pycache__ "imagery\.findings\|findings(" src/ | grep -v "imagery.py\|audit.py\|doctor.py" ; echo exit=$?
exit=1
$ grep -rn --exclude-dir=__pycache__ "answer_key\|decision_boundary" src/ hooks/ | grep -v "answer_key.py\|decision_boundary.py" ; echo exit=$?
exit=1
$ grep -rn --exclude-dir=__pycache__ "\.connect(\|\.secret(" src/ | grep -v "executor.py\|capability.py" ; echo exit=$?
exit=1
```

Notes: `audit.py`/`doctor.py` hits are `audit._chain_findings`, a different symbol (excluded above, shown in the raw sweep). `init.py` has its own live `ask()` (init.py:57) — the spec's claim is about `ui.ask` specifically and holds. The Context section lists these as dead; the Decision then withdraws five of them as governance-enclosed — internally consistent, since "dead" and "enclosed" are different claims.

## F8 — verified (agreement). Every duplication count is right.

- **4 O_NOFOLLOW bounded readers**: audit.py:95, capability.py:145, evidence.py:156, outcome.py:46 — identical `flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0) | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)` + `os.fstat` identity re-check; the snippet is byte-identical across the four.
- **5 git wrappers**: named helper functions `_git`/`git` in checkpoint.py:30, claim.py:41, doctor.py:160, madr.py:327, uninstall.py:503 (`_uninstall_git_value`/`_git_value_global`) = 5.
- **4 ISO-date validators**: accept.py:84, acceptance.py:362, evidence.py:221, madr.py:291+445 (round-trip `fromisoformat(…) == value` pattern).
- **4 `_canonical_json`**: capability.py:131, evidence.py:172, madr.py:130, outcome.py:32 — same `json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()`.
- **3 JSON-Schema subclasses**: capability.`SchemaValidator`, evidence.`Schema`, madr.`Schema` — "adding the same keywords" true: `anyOf` in 3/3, `format` in 2/3, `boolean`→TYPES in 1/3. Slightly overstated as "the same keywords" but the count is exact.
- **6 frontmatter parsers**: blocked.py:282 `_frontmatter`, intent.py:443, solution_intent.py:95, text.py:42, madr.py:179 `_parse`, contract.py:638 inline `split("---", 2)` = 6. (`acceptance._parse_legacy` parses YAML blocks, not fenced headers — correctly excluded.)
- "up to six times" = max count 6. OK

## F9 — verified. Governance citations are real.

```
$ grep -n -A2 'name = "answer_key"\|name = "decision_boundary"' policy/module-status.toml
33:name = "answer_key"
34-status = "deferred"
45:name = "decision_boundary"
46-status = "deferred"
```

- tests/test_orphan_register.py:131-137 hardcodes `("answer_key","constellation","decision_boundary")` as the late-orphan fixture. OK
- policy/module-status.toml:3 header: "Data, not code: the reader is `wiring.module_status()`" — and `wiring.module_status()` exists and runs today: `.venv/bin/python -c '…module_status()…'` → `CALL OK dict 19`, exit 0. OK (The current spec no longer claims it will be moved/deleted — see F12.)
- specs/010 names `ReplaceFileW` with the Microsoft citation at lines 462/466; the spec is dated 2026-08-13. OK
- CONSTITUTION.md: "Only an authorized person may accept a dated, evidenced risk." OK (spec's paraphrase faithful).
- AGENTS.md rule 4: "No compatibility shims. Hard rename, hard delete; say it in the changelog." OK
- EP-016's note literally names `surface.receipt_binds_version` (docs/requirements.toml:186). OK
- loop_guard vs _emit sanitize differently: loop_guard.py:33 hex-escapes (`f"\\x{ord(ch):02x}"`), _emit.py:223 maps to `"?"`. OK
- "~810-line Windows transaction backend": spec_transaction.py is 1606 lines; the win32 material runs from ~759 to EOF ≈ 847 — "~810" is fair. OK

## F10 — verified. Dynamic-resolver sweep: the four sites exist and none reaches a cut target.

```
$ grep -rn --exclude-dir=__pycache__ 'import_module\|__import__\|spec_from_file\|eval(\|exec(' src/ hooks/
src/ai_engineering/paths.py:59:    spec = importlib.util.spec_from_file_location(name, source)
src/ai_engineering/cli.py:326:                module = importlib.import_module(f"ai_engineering.{verb}")
src/ai_engineering/cli.py:502:    module = importlib.import_module(f"ai_engineering.{verb}")
hooks/chain.py:301:            module = import_module(name)
```

cli verbs are gated by the VERBS dict (cli.py:464/480) — the 10 keys (init, doctor, update, spec, decide, accept, audit, report, exception, uninstall) include no cut target. chain TABLE resolves hook-module names only; paths.load reads from `hooks()` by path only; the fourth site, `tests/evals/score.py:61` `spec_from_file_location` (pack `scan.py`), is under tests/ and loads pack reporters only. No fifth resolver exists in src/ or hooks/ (the sweep above is exhaustive for the usual dynamic forms). Conclusion "none reaches any cut target" holds against my own grep. OK

## F11 — verified (agreement). The governance-enclosure example runs clean today.

> "When `uv run python -c \"from ai_engineering import answer_key\"` runs, Then it imports cleanly"

```
$ .venv/bin/python -c 'from ai_engineering import answer_key; print("IMPORT CLEAN")' ; echo exit=$?
IMPORT CLEAN
exit=0
```

(`uv run` form blocked by uv-cache EPERM in this sandbox, pasted under F1; `.venv/bin/python` is the interpreter `uv run` resolves to.)

## F12 — resolved mid-session (was WRONG; recorded for the record).

The text I was assigned at session start asserted, in the success path:

> "`wiring.module_status()` raises ImportError or AttributeError — the register reader moved to tests/" and "`pytest tests/test_wiring.py -k module_status` is empty/skipped"

Both were false: no decision in the spec sanctions deleting/moving `wiring.module_status` (it is the register's own stated reader, F9), and `tests/test_wiring.py` has never existed:

```
$ ls tests/test_wiring.py ; echo exit=$?
exit=1
$ git log --all --oneline --diff-filter=A -- tests/test_wiring.py | wc -l
0
```

The 03:56 rewrite removed both lines; the "Challenged once" claim that the ImportError example "is corrected here" is now true. No action needed beyond noting that the correction arrived without a re-challenge line.

---

## Untestable sentences (named, not judged)

1. `just check` full run — blocked in this context (uv cache EPERM, TMPDIR EPERM); the contradiction between its two quoted numbers is F1, the numbers themselves are not checkable here.
2. Denial path ("after the cut", `ai-eng doctor` names the missing symbol, exit 1) — post-cut state; mechanism exists in shape (doctor emits `missing`-style problem lines, doctor.py:1096, 680-699) but the example cannot be executed pre-cut.
3. Undecidable path — procedural policy, no command.
4. "41 findings" / "finding 40" numbering (F3/F5) — source artifact 019 excluded by assignment.
5. "per-cut commits so bisect stays useful", "returns via `git revert` in minutes" — future workflow claims.
6. Production-ready checklist (all 8 boxes) — the spec is `status: draft`, boxes unticked; nothing in the tree ticks them yet.

## Verdict tally

- WRONG: 2 (F1, F2)
- UNPROVEN: 4 (F3, F4, F5, F6-wording; F6 substance holds)
- verified: 6 (F7, F8, F9, F10, F11, F12-resolved-recorded)