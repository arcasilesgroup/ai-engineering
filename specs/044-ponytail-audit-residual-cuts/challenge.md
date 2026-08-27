# Challenge - spec 044 (ponytail-audit-residual-cuts), round 1

Reviewer: Challenge044 (independent context: spec + tree only; `.ai/reports/019*` not read, per brief; 043's challenge read for format only).
Branch `audit/044-ponytail-residual-cuts`, HEAD `c33b96fd` ("docs(044): write the residual-cuts specification"), main = `b4a525c9`.

Sandbox note: unlike the 043 challenge, `uv` works here (`uv 0.12.2 (Homebrew 2026-08-05)`); `.venv/bin/python` (3.14.6) exists but carries no pytest — the gate's own recipe injects it (`justfile:99` `uv run --with {{pytest}} --with {{xdist}} pytest ...`), and that is what was run.

---

## F1 - WRONG (P1, gate-breaking). The orphan cut list is incomplete: dynamic-import consumers reach three of the eleven.

> "Research report 020 swept every dynamic-resolver site in the tree: none reaches any orphan." (Context §1)
> "the orphan layer — delete the eleven modules, their test modules, the register reader `wiring.module_status`, `policy/module-status.toml`, and `tests/test_orphan_register.py`" (Options 1a)

Report 020's conclusion is scoped to **043's seven targets**, and 020 itself names the site that reaches 044's orphans:

```
$ grep -n "seven\|test_036" .ai/reports/020-dead-module-removal-research.md
14:**No dynamic consumer reaches any of the seven targets.** Every dynamic-resolver site in the tree
44:   `tests/test_036_validation.py:23-31,40` loops a hardcoded ROWS list (evidence, verify_cold,
```

And the site is live:

```
$ sed -n '22,40p' tests/test_036_validation.py
ROWS = [
    ("evidence", "verify", None),
    ("verify_cold", "Verdict", "spec 030"),
    ...
    ("trim", "trim_output", "spec 033"),
    ("decision_fw", "named", "spec 034"),
]
...
        module = importlib.import_module(f"ai_engineering.{name}")
```
```
$ grep -n "import" tests/test_decision_and_notes.py | head -8
17:from ai_engineering import contract, decision_fw  # noqa: E402
```

`tests/test_036_validation.py` and `tests/test_decision_and_notes.py` are neither of the eleven's own test modules nor named in the deletion list, and both are green today:

```
$ uv run --with pytest==9.1.1 python -m pytest tests/test_036_validation.py tests/test_decision_and_notes.py tests/test_orphan_register.py tests/test_skill_bounds.py -q
.......... [100%]
10 passed in 7.83s
```

So family (a) as ordered deletes `verify_cold.py`, `trim.py`, `decision_fw.py` while `test_036_validation.py` still `importlib.import_module`s them — `ModuleNotFoundError` at the gate — and `test_decision_and_notes.py` fails to import `decision_fw` at collection. This contradicts the spec's own rule ("Any cut that turns a test red without deleting that test's subject in the same commit is an incorrect cut") and its "0 failed" gate-path example. Fix: the family must also delete/retire `test_036_validation.py`'s three orphan rows and `test_decision_and_notes.py` (which also covers `contract`, not only `decision_fw` — retiring it loses contract coverage; that must be a decision, not a side effect).

## F2 - WRONG (P2). The register names sixteen caller-less modules, not thirteen; no row "died with 043's cuts"; the parenthetical is self-contradictory.

> "Two more of the register's rows died with spec 043's cuts (`answer_key`, `decision_boundary` were deleted? — no: 043 kept them; only `ui.ask` and `skeletons.seed_intent` died), so the register today still names thirteen caller-less modules and a fourteenth contradiction" (Context §1)

```
$ .venv/bin/python - <<'EOF'
import tomllib
d = tomllib.load(open("policy/module-status.toml","rb"))
rows = d["module"]
print(f"total rows: {len(rows)}")
nc = [m["name"] for m in rows if m["status"] in ("deferred","orchestrator-future")]
cons = [(m["name"],m["status"]) for m in rows if m["status"] not in ("deferred","orchestrator-future")]
print(f"non-consumer rows: {len(nc)} ->", ", ".join(nc))
print("other statuses:", cons)
EOF
total rows: 19
non-consumer rows: 16 -> answer_key, constellation, decision_boundary, coverage, sbom, scan, skillmap, versions, lane_merge, loopgate, skillify, intake, verify_cold, evidencing, trim, decision_fw
other statuses: [('model_router', 'consumer'), ('revalidate', 'consumer'), ('cost', 'consumer')]
```

Sixteen, not thirteen — and the extra five (`coverage`, `sbom`, `scan`, `skillmap`, `answer_key`) are themselves caller-less (AST sweep over src/hooks/surfaces/git-hooks: `coverage: ZERO production importers`, `sbom: ZERO`, `scan: ZERO`, `skillmap: ZERO`, `answer_key: ZERO`), so "thirteen" is wrong under any reading. The parenthetical fails three ways: (1) `decision_boundary` is already in the eleven, so it cannot be "two more" beside them; (2) no register row died with 043 — the register was created whole by `c8a95fc0 feat(042)` and `git log --oneline 2f242968..6450495b -- policy/module-status.toml` is empty; (3) `ui.ask` and `skeletons.seed_intent` were functions inside surviving modules and were never register rows at all (`git show c8a95fc0:policy/module-status.toml | grep "ui\|skeleton"` → only the header comment line matches).

## F3 - WRONG (P2). 043's cut family is mis-cited: the range `2f242968..6450495b` contains no cuts.

> "Spec 043 then landed its cut family on this tree (commits 2f242968..6450495b): `ui.ask`, `skeletons.seed_intent`, the four `_canonical_json` copies..." (Context)

```
$ git log --oneline 2f242968..6450495b | cat
6450495b docs(043): rebuild the intent page over the review response
01925d64 fix(043): review response — guard restored, truths corrected, bool minimum kept
34f416ff docs(043): rebuild the intent page after the cut commits
d0a0f771 fix(043): follow the reader to paths and drop the deleted template key in suites
8cfd4bae fix(043): satisfy mypy on the owned dispatch and plugin unlink
```
```
$ git log --oneline --all -S "seed_intent" -- src/ai_engineering/skeletons.py | head -2
fa2fb510 refactor(043): delete seed_intent and its two suites, nobody calls it
$ git merge-base --is-ancestor fa2fb510 2f242968 && echo "fa2fb510 is BEFORE 2f242968 — outside the cited range"
fa2fb510 is BEFORE 2f242968 — outside the cited range
$ git log --oneline 2f242968..6450495b -- policy/module-status.toml src/ai_engineering/ui.py src/ai_engineering/skeletons.py | wc -l
0
```

The cuts landed in earlier commits (e.g. `fa2fb510`); the cited range is only the review-response/docs tail. The substance (the deletions happened) is true; the citation as evidence is wrong.

## F4 - WRONG (P2). `wiring.module_status`'s only consumer is `test_orphan_register.py`; `test_mut_wiring.py` never mentions it.

> "Verified: the reader's only consumers are `tests/test_orphan_register.py` and `tests/test_mut_wiring.py` (which tests the reader itself)." (Challenged once)

```
$ grep -rn "module_status" tests/ --include="*.py" | grep -v __pycache__
tests/test_orphan_register.py:4:an infrastructure lane. `policy/module-status.toml` (data) + `wiring.module_status()` (a
tests/test_orphan_register.py:72:    rows = wiring.module_status()
tests/test_orphan_register.py:84:    rows = wiring.module_status()
tests/test_orphan_register.py:100:    rows = wiring.module_status()
tests/test_orphan_register.py:110:    rows = wiring.module_status()
tests/test_orphan_register.py:135:    rows = wiring.module_status()
$ grep -rn "module_status" tests/test_mut_wiring.py | wc -l
0
```

`test_mut_wiring.py` has 57 `def test`s and zero references to the reader. The deletion is still safe (only `test_orphan_register.py` consumes it, and the family deletes that file), so the conclusion survives — but the "Verified:" sentence states a fact the tree contradicts, and the same grep over `src/` confirms the register-path example's premise: `grep -rn "module_status" src/ hooks/` prints only `src/ai_engineering/wiring.py:502`, so post-deletion "no hits" is consistent.

## F5 - WRONG (P2). Three of the "dead constants" have exactly one live production caller each.

> "`spec.self_contained`/`_LEAKS`, `model_router.bail_out`, `audit.replay` (the verb path calls `_replay` directly at audit.py:549), `cli.UNEXPECTED`, `solution_intent.NOT_HASHED` (empty tuple), `spec._document_relations` (one-use alias), `answer_key.valid`/`apply` and root `answer-key.yaml` have zero production or CLI callers." (Context §3)

```
$ grep -n "UNEXPECTED" src/ai_engineering/cli.py | head
423:UNEXPECTED = EXEC_FACTS_FAIL
437:    return outcome.error("UNEXPECTED_ERROR", UNEXPECTED, False, "rerun with --debug for the trace")
$ grep -n "crash(" src/ai_engineering/cli.py
426:def crash(exc: BaseException, *, debug: bool) -> outcome.Error:
545:        failure = crash(exc, debug=debug)
```
```
$ grep -n "NOT_HASHED" src/ai_engineering/solution_intent.py; sed -n '299,303p' src/ai_engineering/solution_intent.py
296:NOT_HASHED: tuple[str, ...] = ()
303:    return {name: value for name, value in asdict(tree).items() if name not in NOT_HASHED}
def digested(tree: Tree) -> dict:
...
$ grep -n "_document_relations" src/ai_engineering/spec.py
37:_document_relations = intent._document_relations
982:                linked = _document_relations(observed.body)
```

`cli.UNEXPECTED` is read at `cli.py:437` inside `crash()`, which `cli.py:545` calls for every uncaught exception — one live caller, not zero. `NOT_HASHED` is read inside `digested()`, which `digest()` calls (`solution_intent.py:317`). `_document_relations` is called at `spec.py:982`. The parenthetical "(one-use alias)" concedes the last one, but the sentence's predicate "zero production or CLI callers" is false for these three; it is true for `audit.replay` (`def replay` at `audit.py:389`, verb path uses `_replay` at `audit.py:549`, no other callers in src/hooks/surfaces), `spec.self_contained`/`_LEAKS` (def at `spec.py:790`, `_LEAKS` only read by it), `model_router.bail_out` (docstring mention only), `answer_key.valid`/`apply` (tests only), and root `answer-key.yaml` (read only by `answer_key.py:156` in its own `__main__`).

## F6 - WRONG (P2). `acceptance._parse_legacy` is not a "line-by-line" clone of `text.flat_yaml`.

> "`acceptance._parse_legacy` line-by-line cloning `text.flat_yaml` (text.py:21-39 vs acceptance.py:332-357)" (Context §2)

The line ranges are exact (verified: `flat_yaml` def at text.py:21, `return data` at 39; `_parse_legacy` def at 332, `return fields` at 358-359). But the bodies diverge materially:

```
$ sed -n '21,39p' src/ai_engineering/text.py   # 19 lines, 3 raise sites
$ sed -n '332,357p' src/ai_engineering/acceptance.py  # 27 lines, 7 raise sites
```

`_parse_legacy` adds: container-value refusals on continuation lines (`-`/`?`), duplicate-key refusal, `[`/`{` start refusals, and the `finding`+`expires` presence gate returning `None`; and it raises `Refusal(code, msg)` where `flat_yaml` raises bare `ValueError`. The shared home needs the error as a parameter (D-044-03 allows it) plus the extra arms as options — "line-by-line" understates the merge and oversells the dedup win.

## F7 - WRONG (P3). The skills corpus does not name `verify_cold` or `constellation`.

> "The skills corpus names some orphans (`trim`, `skillify`, `intake`, `verify_cold`, `loopgate`) as prompt-routed instruments" (Context §1); "**D-044-01**: The skill-corpus names (`trim`, `skillify`, `intake`, `verify_cold`, `loopgate`, `constellation`) stay in the corpus"

```
$ for n in trim skillify intake verify_cold loopgate constellation; do c=$(grep -rl "$n" .agents/skills/ 2>/dev/null | wc -l | tr -d ' '); echo "$n: $c files"; done
trim: 1 files
skillify: 1 files
intake: 2 files
verify_cold: 0 files
loopgate: 2 files
constellation: 0 files
```

`ai-verify/corpus.md:15` names the *concept* ("verify this cold") without the module name; `constellation` appears nowhere in the corpus, so "stay in the corpus" is vacuous for it. The `loopgate`/`test_skill_bounds` claim checks out (`tests/test_skill_bounds.py:35` asserts `"loopgate" in body` — corpus text, not the module — and the corpus does name it), as does "no test asserts an import of a deleted module from skill text" (no corpus-reading test imports any orphan).

## F8 - WRONG (P3). The `sys.path.insert + # noqa: E402` idiom lives in 25 test modules, not twenty.

> "the `sys.path.insert + # noqa: E402` idiom in twenty pytest modules" (Context §3); "leaves rule 3 violated in twenty files" (Option 2 costs)

```
$ grep -rln "noqa: E402" tests/ --include="test_*.py" | grep -v __pycache__ | wc -l
25
$ grep -rln "sys.path.insert" tests/ --include="test_*.py" | grep -v __pycache__ | wc -l
29
$ comm -12 <(grep -rln "noqa: E402" tests/ --include="test_*.py" | sort) <(grep -rln "sys.path.insert" tests/ --include="test_*.py" | sort) | wc -l
25
```

25 files carry both. After family (a) deletes the orphan suites the residue is 14, not 20 — the number in the sentence matches neither the current tree nor any post-cut state. (The "noqa criterion" example itself is fine: post-migration `grep -rn "noqa: E402" tests/ --include="test_*.py" | wc -l` printing `0` is achievable.)

## F9 - WRONG (P3, with a caveat) / counts. The duplication inventory's numbers are each off by one or a factor.

> "four `git ls-files` readers and four `git -C` wrappers" · "a GIT-identity env dict ×6" · "five identical `def git()` wrappers" · "byte-identical `home` fixtures ×4" · "a 15-gram-identical lifecycle dict ×4" · "~1,000 lines of wheel" (Context §2/§3/§1)

- `git -C` wrappers: **5** named helpers — `checkpoint.py:35`, `madr.py:334`, `claim.py:41`, `uninstall.py:470` (`git(root,key)` runs `git -C`), `doctor.py:165`. (`git ls-files` readers: 4 files — `madr`, `contract`, `evidence`, `doctor` — correct.)
- GIT-identity env dict: **7** sites (`madr.py` ×2 at 503/522, `test_mut_spec.py:69`, `test_mut_madr.py:419`, `test_spec_marker.py:59`, `test_model_event.py` ×2 at 36/146, plus `claim.py:34`'s prod dict) vs claimed 6.
- `def git()` in tests: 4 byte-identical (`test_wave.py:23`, `test_claim.py:21`, `test_merge_gate.py:20`, `test_checkpoint.py:23`), `test_doctor.py:53` differs (returns `None`); the remaining matches (`red_then_green.py`, `adversarial/run.py`, `unreviewed.py`, `one_home.py`) are non-test helpers, so "five identical" is 4+1, not 5.
- `home` fixtures "byte-identical ×4": the largest byte-identical set is **2** (`mut_init`/`install` share docstring+body; `emit_home` differs; the fake-HOME trio differs in kwargs) — "byte-identical" is false for the set of four.
- lifecycle dict "15-gram-identical ×4": 3 exact copies + 1 with two differing dates.
- orphan wheel mass: `wc -l` of the eleven src modules = **645** lines (their named test suites 597 + register suite 138); "~1,000 lines of wheel plus their test modules" overstates the wheel by ~1.5× unless tests are counted in the wheel, and they are not shipped.

Each class of duplication is real and the commands above locate it; the multipliers are not load-bearing for the decision, but every one printed a different number than the spec.

## F10 - WRONG (P2, example contradicted by the branch itself). "0 failed at every commit in the branch" already fails at the spec commit.

> "**The gate path.** Given every commit in the branch, When `just check` runs at the head commit, Then the tail reads `0 failed`..." (Examples); "The gate's baseline is the current green on `main` (b4a525c9)." (Assumptions)

```
$ uv run --with pytest==9.1.1 --with "pytest-xdist[psutil]==3.8.0" pytest -q -n auto 2>&1 | tail -3
assert False
 +  where False = any(<generator object test_this_branch_is_measured_rather_than_described.<locals>.<genexpr> at 0x1075a7060>)
1 failed, 2402 passed, 2 skipped in 69.02s (0:01:09)
```

The failure is `tests/test_one_home.py::test_this_branch_is_measured_rather_than_described`: it walks `git rev-list main..HEAD` and asserts some commit touches more than one "home"; this branch's only commit (`c33b96fd`, the spec itself) touches one file, so the assertion fails — and its own message says the remedy is to "regrade [PO-16] rather than leaving this assertion." The main-baseline assumption survives (on main the `rev-list` is empty and the test returns early; everything else in the suite passed), but the gate-path example is contradicted at the branch's current head, and every future single-home commit on the branch (a spec-only or changelog-only commit) re-reds it. The cut families will pass only because they touch many homes — worth knowing before promising "0 failed at every commit."

---

## Claims that checked out (verified OK)

- **The eleven orphans have zero production importers** — own AST sweep over `src/`, `hooks/`, `surfaces/`, `git-hooks/` (relative-import aware, same-package excluded): all eleven print `ZERO production importers`; `justfile`/`.github/` name none of them as a verb. `cli.py:31` `VERBS` and `hooks/chain.py:38` `TABLE` are closed dicts; zero `pkgutil`/`entry_points`/`load_module` hits in src+hooks; `paths.load()` is a fixed-name hook loader (`_emit`, `_otlp`), not a directory scan — the Assumption holds, with `paths.load` as a third (closed) site 020 already counted.
- **The register records all eleven** as `deferred`/`orchestrator-future` (16-row census above includes all eleven; statuses verified per row).
- **`tests/test_orphan_register.py` hardcodes three names** — `("answer_key", "constellation", "decision_boundary")` at line 136; `test_a_consumer_must_be_imported_by_a_production_file` exists (the AST-definition enforcer D-044-01 cites).
- **Five digest-pinned loaders**: `EXPECTED_SCHEMA_DIGEST` in exactly `acceptance`, `capability`, `evidence`, `madr`, `outcome`.
- **`doctor._run_cli` mirrors `wiring.cli_answers`**: both run `[sys.executable, "-m", "ai_engineering.cli", ...]` with `PYTHONSAFEPATH=1` and `timeout=30`; "same argv" holds only for the `--version` invocation (`_run_cli` takes arguments and a cwd; `cli_answers` fixes `["--version"]`) — mirroring is real, the phrase is loose.
- **`ui._consoles`** is a hand-rolled `dict[bool, Console]` memo (`ui.py:64-98`) with a manual `.clear()` — `functools.cache`-shaped, as claimed.
- **`uninstall._hex`** is a char-loop (`all(character in "0123456789abcdef" ...)`) called at line 410 beside `len(recorded) != 64` — `re.fullmatch` is the native form, as claimed.
- **`verify_cold.verify` takes `allow_write`/`constructor_reasoning` only to raise** — `verify_cold.py:45-58`, its own docstring says so.
- **`cost.calibrate`'s single call site** is `audit.py:494` with hardcoded `[(0.01, 35.0)]`; the body reads only the first tuple field (`sum(c for c, _ in samples)`), and nothing else reads the second.
- **`spec_transaction.publish` returns `Published` both production callers discard**: `spec.py:1244` and `accept.py:249` call it as a statement.
- **`audit.replay` dead**: def at `audit.py:389`, verb path calls `_replay` directly — and indeed at `audit.py:549`, the exact line cited.
- **Root `answer-key.yaml`**: read only by `answer_key.py:156` inside its own `__main__`; no production or CLI caller.
- **Six hand-rolled JSON-Schema-subset validators** in tests (`_valid`/`_schema_accepts`-shaped helpers in `test_acceptance`, `test_capabilities`, `test_evidence`, `test_intent`, `test_madr`, `test_outcomes`) — 6.
- **`json.loads(json.dumps())` deep-copy idiom** exists in tests (5 occurrences).
- **pyproject `pythonpath = ["src","hooks","tests"]`** replaces the `sys.path.insert` idiom (comment at pyproject.toml:56-65 even narrates the noqa problem).
- **043 consolidated `_canonical_json`**: zero `_canonical_json` left in src; `intent.canonical_json` is the home — the criterion's parenthetical is true.
- **`b4a525c9` is main** (`git rev-parse main` → `b4a525c9`).
- **The register-path example is internally consistent**: `module_status` occurs in src only at `wiring.py:502`, so deleting the reader + toml genuinely yields "no hits"; `test ! -f policy/module-status.toml` post-cut is a goal, not testable now.
- **D-044-02's keep-list exists**: EP-254/EP-016/EP-176 rows in `docs/requirements.toml`; 020 itself argues `imagery.findings` and `surface.receipt_binds_version` are named evidence; `executor.Sandbox.connect` was flagged in 043 ("an owner should either wire connect" — 043 spec line 98).

## Untestable in this context

1. "four independent scans plus a verification pass; net estimate -1,900 lines src-side" — the audit artifact is `.ai/reports/019*`, excluded by the assignment brief; 020 quotes it but the estimate's derivation cannot be re-executed here.
2. "the gate burns minutes on tests of unreachable code" — measurable in principle (the orphan suites run in <1s of a 69s run; the claim's magnitude is rhetorical), not worth a verdict either way.
3. All post-cut examples (`ModuleNotFoundError`, toml gone, noqa count 0, dedup criterion ≤1, "0 failed" at head) — goals about a branch that does not exist yet; their *preconditions* were checked where possible (F10 shows the gate-path example already has a red head on the current branch).
4. "the wheel shrinks by ~1,900 lines" (Option 1 gives) — depends on the 019 estimate (item 1) and on family (d) test deletions not yet enumerated file-by-file.
5. The "undecidable path" — procedural policy (record under an Excluded list in the changelog); no command ticks it.
6. Production-ready checklist (all 8 boxes) — `status: draft`, boxes unticked; nothing in the tree ticks them yet.
7. "reinstatement is `git revert` plus re-registration, cost bounded by the specs" — future workflow claim.

## Verdict tally

- WRONG: 10 (F1 gate-breaking; F2-F6 substantive; F7-F9 accuracy/counts; F10 example contradicted at branch head)
- verified OK: the 24 bullets above (the orphan sweep itself, the register's per-row statuses, the duplication *classes*, the flexibility *classes*, the six validators, the closed-resolver assumption)
- UNPROVEN: 7 (listed above)

The spec's core thesis — eleven caller-less orphans, a register with no production reader, real duplication families, real test-shaped flexibility — survives every attack. What does not survive: the deletion list (F1 misses two live consumers), the register arithmetic (F2), and most of the cited evidence numbers (F3-F9).
