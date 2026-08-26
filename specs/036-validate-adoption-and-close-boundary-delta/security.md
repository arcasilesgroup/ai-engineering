# Security review: spec 036 (decision-boundary delta)

Reviewed by the `ai-security` skill contract, over commit range `47ec9093..HEAD`
(5 commits: `tests/test_036_boundary.py`, `tests/test_036_validation.py`,
`src/ai_engineering/decision_boundary.py`, corpus/description routes on
`ai-review` + `ai-verify` (+ one `ai-spec` corpus row), `policy/pilot-register.toml`
baseline 363→368, `docs/requirements.toml` notes). Review date 2026-08-26.
This review accepts no risk and declares no compliance.

## 1. The boundary

What crosses it, who controls each side, what an attacker on one side reaches on the other.

| Crossing | From (controlled by) | To | Attacker on the source side reaches |
|---|---|---|---|
| Request text carrying a decision (`"ai-explore:default"`, `"promote"`, …) | the user / prompt-injection attacker | `classify(decision, declarations)` | a verdict class and the `blocks` flag; today no production surface invokes `classify` (finding S-4), so nothing live is reached |
| Declaration data (`policy/capabilities.toml`: `id`/`modes`/`human_gate`) | repo authors; whoever can write into `policy/` (threat-model row `policy-data`, control `src/ai_engineering/capability.py`) | `from_capability_manifest` / `load_capability_classes` | the whole classification: gates flip between Always/Ask-first/Never; writes into `policy/` are refused by `hooks/self_protect.py` (threat-model row `dispatcher-input`) |
| Skill metadata and corpus text (`SKILL.md` description refusals, `corpus.md` rows) | repo authors, commit-controlled | the routing harness (`tests/skill_eval.py` `_REFUSAL`/`cases()`) and, as instructions, the model | routing decisions (which skill a refusal points at) and model behaviour (refuse + report `CANNOT DECIDE`); text is static and own-authored, inside threat-model row `skill-instructions` (control `src/ai_engineering/contract.py`) |

The attacker model that matters for this delta: a prompt-injection attacker who controls
request text only. That attacker cannot edit `policy/capabilities.toml`, the SKILL.md
descriptions or the corpus (all in-tree, policy/ additionally write-protected), cannot
redirect the manifest path (derived from `__file__`, finding S-5), and cannot reach the
classifier's blocking at all because nothing calls it (finding S-4). The attacker who
*can* write into `policy/` is the supply-chain/OS compromise already modelled by the
`policy-data` and `dispatcher-input` rows; this delta adds no new way to reach that.

## 2. Where the data is

- New data: none. The delta adds one stdlib-only module, three corpus rows, two
  description clauses, a baseline number and requirements notes. No dependency, no
  network call, no second hop, no URL.
- Classification: happens in-process on request strings and manifest data read via
  `tomllib` from `policy/capabilities.toml` (`decision_boundary.py:21,100-104`). Nothing
  is written, logged or transmitted by the module.
- Rest: declarations rest in the repo (`policy/capabilities.toml`, schema-validated and
  digest-pinned by `capability.py`); corpus refusals rest in the repo under
  `.agents/skills/`. Readable by anyone with repo access; writable by repo authors and
  by anything that can write into `policy/` (guarded by `self_protect.py`).
- Travels: nowhere. No data leaves the machine.
- Who can read it: the model at run time (corpus/description text is loaded as skill
  instructions), the routing harness, and the classifier when wired.

## 3. Scanners (pinned versions, output pasted)

Version pins verified before the run: gitleaks `8.30.1` (`gitleaks version` → `8.30.1`),
trivy `0.73.0` (`Version: 0.73.0`), semgrep `1.172.0` (via `uv run --with semgrep==1.172.0`).
Command run: `just security` in `/Users/soydachi/repos/ai-engineering` (gitleaks in
gitless `dir` mode, semgrep against `policy/semgrep.yml`, trivy `fs` with
`--include-dev-deps`; three lanes through `scan.baseline(Path('.'))`).

```
# Through the lane contract rather than as three bare commands: a missing engine, missing
# rules, a crash, a timeout or zero inputs each read as INCOMPLETE, and INCOMPLETE fails
# this gate exactly as a finding does. Three bare commands could not tell those apart.
uv run --with semgrep==1.172.0 python -c "import sys; from pathlib import Path; from ai_engineering import scan; sys.exit(scan.baseline(Path('.')))"
  FAIL        secrets       it ran over 1 input(s) and found something
  INCOMPLETE  secrets       generic-api-key has detected secret for file .skill-map/serve.json.
                            decided by gitleaks dir — .skill-map/serve.json:9
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  FAIL        semantic      it ran over 1 input(s) and found something
  INCOMPLETE  semantic      Silencing the linter hides the finding rather than answering it. Refactor, or record an accepted risk with ai-eng accept. Rule 3 is not about one language.
                            decided by semgrep scan — src/ai_engineering/answer_key.py:152
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  INCOMPLETE  semantic      Silencing the linter hides the finding rather than answering it. Refactor, or record an accepted risk with ai-eng accept. Rule 3 is not about one language.
                            decided by semgrep scan — src/ai_engineering/cost.py:40
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  INCOMPLETE  semantic      Silencing the linter hides the finding rather than answering it. Refactor, or record an accepted risk with ai-eng accept. Rule 3 is not about one language.
                            decided by semgrep scan — src/ai_engineering/cost.py:93
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  INCOMPLETE  semantic      A shell string built from a variable. Pass a list of arguments instead.
                            decided by semgrep scan — src/ai_engineering/evidencing.py:40
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  INCOMPLETE  semantic      Silencing the linter hides the finding rather than answering it. Refactor, or record an accepted risk with ai-eng accept. Rule 3 is not about one language.
                            decided by semgrep scan — src/ai_engineering/evidencing.py:67
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  INCOMPLETE  semantic      A shell string built from a variable. Pass a list of arguments instead.
                            decided by semgrep scan — src/ai_engineering/verify_cold.py:28
                            nobody has answered: boundary, attacker_controls, refutation, closed_by
  PASS        dependencies  it ran over 1 input(s) and found nothing
  OBSERVED    boundaries    15 declared, 13 with a control this tree holds whole
  OBSERVED    manifests     package.json, pyproject.toml
  OBSERVED    coverage      the engine read a file for every manifest here
  SKIPPED     images        no container image here, so no container lane runs
  SKIPPED     dast          nothing here scanned a running target: that needs a URL somebody authorised, and this gate never has one
  SKIPPED     skillspector  skillspector is not installed here, so there is no second opinion to read
  SKIPPED     claude-security claude-security is not installed here, so there is no second opinion to read
error: recipe `security` failed on line 107 with exit code 1
EXIT=1
```

Lane outcomes, each with its command:

| Lane | Command | Outcome |
|---|---|---|
| secrets | `gitleaks dir --redact --no-banner --exit-code 1` (via `scan.baseline`) | **FAIL** (found `generic-api-key` at `.skill-map/serve.json:9`); the lane itself marks the finding **INCOMPLETE** (nobody has answered its fields). File is a gitignored, untracked local runtime state file of the skill-map.ai daemon (`smVersion 1.12.2`, localhost scope, token `57dc13…`), dated 2026-08-25, outside the 036 delta (`git check-ignore .skill-map/serve.json` → ignored; not in `git diff 47ec9093..HEAD`). |
| semantic | `semgrep scan --config policy/semgrep.yml --error --quiet` (via `scan.baseline`) | **FAIL** (6 findings, all in pre-existing files outside the delta: `answer_key.py:152`, `cost.py:40`, `cost.py:93`, `evidencing.py:40`, `evidencing.py:67`, `verify_cold.py:28`); each marked **INCOMPLETE** (no answer recorded). Zero findings in `decision_boundary.py`, `tests/test_036_*.py`, or the corpus/description files. |
| dependencies | `trivy fs --scanners vuln,license,misconfig --exit-code 1 --severity CRITICAL,HIGH,MEDIUM --include-dev-deps` (via `scan.baseline`) | **PASS** (found nothing over the manifests the engine read: `package.json`, `pyproject.toml`; coverage observed). |
| dast / running target | `scan.baseline` dast lane | **SKIPPED** with reason: nothing here scans a running target. No service is deployed by this delta or this repository's gate; nothing running is declared safe on the strength of file scans. |
| cross-checks | skillspector, claude-security | **SKIPPED** (not installed); they are optional second opinions, not this repository's baseline. |

The gate overall is **FAIL** (exit 1). None of the red is in the 036 delta; all of it is
pre-existing tree state or a local gitignored artifact.

## 4. What the scanners cannot read

**The classifier's treatment of malformed/undeclared input (U0).** `classify()`
(`decision_boundary.py:58-77`) is fail-closed: empty/non-string decision → `U0` +
`blocks=True`; no/empty declarations → `U0` + `blocks=True`; declared-but-malformed class
value → `U0` + `blocks=True`; out-of-declaration → `U1` + `blocks=True`. The fixture
proves all four paths (`tests/test_036_boundary.py:26-38`). But the module's own manifest
surface never emits a malformed value: `from_capability_manifest` maps every gate through
`_GATES.get(gate, "Ask-first")` (`decision_boundary.py:79-98`), so any unknown, missing,
typo'd or non-string `human_gate` becomes a *decided* `Ask-first` with `blocks=False` and
`reason=None` — no `U0`, no block. Measured: `human_gate = "soemtimes"` and `human_gate = 7`
both produce `Ask-first / None / blocks=False`. On the live manifest, 15 of 25 modes
classify `Ask-first` (2 `before_network` + 1 `before_exec` + 2 `before_publish` + 10
`before_write` — the latter three are legitimate schema-enum gates that are not in
`_GATES`), 10 classify `Always` (the `never` gates), zero `Never`. So the U0 „malformed
declarations" branch of `classify()` is unreachable from the single source of truth the
spec claims, and the module's own docstring advertises the default as „the safe default,
never a silent allow" — it is *not* a block.

**Does the default Ask-first ever allow silently?** It never yields `Always` (the
strongest class) for an unknown gate — that is the one thing it cannot do. But it *does*
yield a decided, non-blocking class for data the spec says must produce `U0` + `CANNOT
DECIDE` + block. Whether Ask-first is a silent allow depends entirely on a downstream
„ask" mechanism, and no such mechanism exists (finding S-4). Contrast with the
capability contract the classifier claims to mirror: `capability.py:425` fails closed on
an unrecognised gate word (`GATES.get(mode["human_gate"], tuple(_ACTION_CONTROLS))` —
an unknown word gates *everything*), while `decision_boundary.py:95` fails to the
non-blocking class. Two readers of the same file with opposite failure postures.

**The default Ask-first and the inverted vocabulary.** `_GATES = {"never": "Always",
"before_network": "Ask-first", "always": "Never"}` is the gate *semantics* translated to
the three-class vocabulary: a mode whose human gate is `never` needs no approval, so its
decisions are Always; a mode that always hits the network is Never. That inversion is
correct and matches `capability.py:247` (`human_gate != "never"` ⇒ human-gate
required). Minor contract drift, not security: `"always"` is not a legal schema-enum
value (schema enum is `never/before_write/before_exec/before_network/before_publish`),
and every out-of-declaration decision is stamped `U1` by `_unknown_index()`
(`decision_boundary.py:54-55`) — the spec's `U1,U2,…` per-out-of-declaration-class
numbering is not implemented.

**The corpus refusals as instruction sources.** The added clauses
(`ai-review/SKILL.md:10`, `ai-verify/SKILL.md:10`, `ai-review/corpus.md:18`,
`ai-verify/corpus.md:16`, `ai-spec/corpus.md:18`) are text a model loads and follows:
refuse,report `CANNOT DECIDE`, route (ai-review → /ai-verify; the others → block). This
is exactly the `skill-instructions` threat-model row: „a skill is executable text, and
one that ships … an edited refusal is an instruction nobody reviewed", whose control is
`contract.py`'s `_corpus_problems` lane. The text is own-authored, commit-controlled and
not attacker-writable in-tree, so no prompt-injection attacker redirects it. Residual:
fail-closed over-refusal — a user quoting one of the refused shapes can make the model
refuse an in-scope request or route it to another skill. That is an availability cost
bought deliberately by the spec's fail-closed design, not a bypass.

**Can `policy/capabilities.toml` parsing be pointed anywhere hostile?** The path is
`ROOT = Path(__file__).resolve().parents[2]` (`decision_boundary.py:20-21`) — derived
from the module file location, not from environment, config or request data. A prompt
cannot redirect it. The file itself sits in `policy/`, whose writes `self_protect.py`
refuses (threat-model `dispatcher-input` row). What can read hostile input here: an
attacker who can already write into the installed package's policy directory controls
the manifest and flips classifications — that is the pre-existing `policy-data` row, not
a new surface. The one divergence: this module hand-rolls the package root instead of
using `paths.policy()` (which resolves the *shipped* policy inside the wheel via
`shipped()`), so in an installed (wheel) layout `load_capability_classes()` points at
`<env>/policy/capabilities.toml`, which does not exist, and raises `FileNotFoundError`
instead of failing cleanly (finding S-3).

**Reachability.** `grep -rn "decision_boundary\|from_capability_manifest\|classify" src/
hooks/` finds the module only in `src/ai_engineering/decision_boundary.py` and its own
`__pycache__`. No CLI verb, no router, no guard imports it. The blocking control exists
only in fixtures (finding S-4).

## 5. MCP servers

The repository declares no MCP servers: no `.mcp.json` at the root, none anywhere in the
tree (`find . -name "*.mcp.json" -o -name "mcp*.json"` → nothing; the only `mcp`
mention in the tree is a requirements note naming `hooks/chain.py`). The MCP servers
visible in this session (pencil, node_repl, arcasiles-brand) are declared by the hosting
harness, not by this repository, and are out of scope of a repo-level review — but this
review records them as external trust boundaries with no repo-side declaration to audit.
Pass: nothing undeclared on the repo side.

## 6. Findings (each: boundary crossed · attacker control · reachable effect · state ·
command/file:line · refutation tried · what closes it)

### S-1 — `just security` gates are red; none of the red is the delta
- **Boundary crossed:** committed tree + working tree vs secret/rules/dependency lanes.
- **Attacker control:** none by a prompt attacker; the gitleaks hit is a gitignored local
  runtime artifact (`.skill-map/serve.json:9`, skill-map.ai daemon token, localhost
 127.0.0.1:4242), the semgrep hits are pre-existing lint debt in `answer_key.py:152,
  `cost.py:40,93`, `evidencing.py:40,67`, `verify_cold.py:28`.
- **Reachable effect:** the security gate exits 1 today; no delta file carries a finding.
- **State:** FAIL (gate exit 1) — secrets FAIL, semantic FAIL, dependencies PASS.
- **Command:** `just security` (gitleaks 8.30.1 / trivy 0.73.0 / semgrep 1.172.0 pinned
  and verified before the run), output pasted in §3. Delta files: clean in every lane.
- **Refutation tried:** „serve.json is gitignored and not in the repo, so not a real
  secret" — fails: gitleaks `dir` scans the working tree and the lane's contract reads
  any hit as FAIL-until-answered, and the lane itself reports the finding INCOMPLETE
  (nobody answered its fields). „semgrep debt is pre-existing" — true, and irrelevant:
  the gate is still red.
- **What closes it:** remove/rotate the local `serve.json` artifact (or scope the
  secrets lane away from `.skill-map/`), and answer or `ai-eng accept`-close the six
  semgrep findings; no delta change needed.

### S-2 — malformed gates become decided Ask-first, never U0, at the manifest surface
- **Boundary crossed:** `policy/capabilities.toml` gate values → decision class.
- **Attacker control:** a gate word typo'd, a non-string gate, or a future schema-enum
  word not in `_GATES`; also any attacker who can write `policy/` (already modeled).
- **Reachable effect:** the spec's „undeclared or malformed declarations → U0 +
  CANNOT DECIDE + block" is dead from the single source of truth: the module silently
  returns `Ask-first / reason=None / blocks=False` (measured: `"soemtimes"` and `7` both
  classify Ask-first). A caller that treats Ask-first as „ask when convenient" allows
  silently; today no caller exists (S-4). 13 of 25 live modes take this default branch
  legitimately (`before_exec`, `before_publish`, `before_write` — declared enums absent from
  `_GATES`), so malformed input is indistinguishable from legitimate input.
- **State:** FAIL — contract mismatch between spec B-036-1 text and module behaviour,
  produced by reading `decision_boundary.py:23,79-98` plus the schema enums
  (`policy/capability-manifest.schema.json:192-201`) and this probe:
  ```
  uv run --with pytest==9.1.1 python -c "from ai_engineering import decision_boundary as db; m={'capabilities':[{'id':'x','modes':[{'id':'m','human_gate':'soemtimes'}]}]}; r=db.classify('x:m', db.from_capability_manifest(m)); print(r.verdict, r.reason, r.blocks)"
  → Ask-first None False
  ```
- **Refutation tried:** „the schema enum + digest pin in `capability.py` make malformed
  gates unreachable in the governed tree, so it cannot happen" — true, and it is why the
  live harm is latent; but it does not repair the contract: the module's own loader
  produces the decided class from data the spec says must block, and `capability.py`'s
  own posture for the same input is fail-closed-*everything* (`capability.py:425`). Two
  readers, opposite postures, same file. Kept.
- **What closes it:** make `from_capability_manifest` return the malformed gate as a
  `U0`/blocking state (or refuse to map non-enum gates), so the manifest surface and
  `classify()`'s U0 branch agree; add a fixture over the manifest surface that asserts a
  bad gate blocks.

### S-3 — `load_capability_classes` hand-rolls the package root; the wheel layout crashes
- **Boundary crossed:** policy data → classifier input.
- **Attacker control:** none at runtime — the path derives from `__file__`
  (`decision_boundary.py:20-21`), not from data; `_unknown_index` has no input. The
  divergence is a layout bug, not a redirect.
- **Reachable effect:** in an installed (wheel) layout, `CAPABILITIES` resolves to
  `<env>/policy/capabilities.toml` instead of the shipped `ai_engineering/policy/`
  that `paths.policy()`/`shipped()` resolve; the file is absent and
  `load_capability_classes()` raises `FileNotFoundError` — a crash, not a clean
  INCOMPLETE, and the „same single source of truth as tool gating" claim (spec B-036-1)
  holds only in checkout layout. Currently latent: nothing calls it (S-4).
- **State:** FAIL (mechanism divergence), from reading `decision_boundary.py:20-21`
  against `paths.py:10-13,32-34` (`shipped()`/`policy()`).
- **Command:** `grep -n "def policy\|shipped" src/ai_engineering/paths.py` + code read
  of `decision_boundary.py:20-21,100-104`.
- **Refutation tried:** „the framework runs from the checkout, where parents[2] is the
  repo root and matches" — true in this tree, fails for the installed tool; the module
  exists to be read by `ai-eng` consumers, and a boundary read that raises is unread.
  Kept.
- **What closes it:** use `paths.policy("capabilities.toml")` like `capability.py`
  (`MANIFEST_PATH`), and/or make the loader return a clean INCOMPLETE on a missing file.

### S-4 — the classifier has no production caller; its blocking is unreachable
- **Boundary crossed:** request text → decision verdict → block.
- **Attacker control:** a prompt-injection attacker controls request text, which is the
  one input the blocking control is built for.
- **Reachable effect:** none — positively, nothing can be bypassed (no fail-open);
  negatively, nothing is enforced: no request can ever hit a U0/U1 `CANNOT DECIDE`
  block, and no Ask-first is ever asked. The only live enforcement of the boundary rule
  is prompt-level instruction text (the description/corpus refusals), which is a soft
  control. A reader who believes „out-of-declaration blocks" is misled.
- **State:** INCOMPLETE (control exists, tested in isolation, not wired to any live
  decision surface).
- **Command:** `grep -rn "decision_boundary\|from_capability_manifest\|classify" src/
  hooks/` (only the module and its `__pycache__`), `grep -rn "decision_boundary" tests/`
  (only `tests/test_036_boundary.py`).
- **Refutation tried:** „spec 036 scopes B-036-1 as 'read by its fixture; the overlap is
  resolved by integration', so not wiring it is deliberate" — true for the plan, and it
  is why this is an honesty note rather than a defect verdict: the delta ships an
  unexercised control and calls it a control. Kept as INCOMPLETE, not FAIL.
- **What closes it:** rout a live decision surface (the CLI's decide path, a guard) to
  `classify()` so the block is reachable, or say in the spec that B-036-1 is library-only
  until wired.

### S-5 — the manifest path cannot be pointed anywhere hostile
- **Boundary crossed:** none — the read target is fixed by module location.
- **Attacker control:** none; no environment variable, config or request data feeds
  `CAPABILITIES` (`decision_boundary.py:20-21`). policy/ writes are refused by
  `hooks/self_protect.py` (threat-model `dispatcher-input` row).
- **Reachable effect:** none beyond S-3's layout crash.
- **State:** PASS.
- **Command:** code read `decision_boundary.py:20-21`; threat-model row
  `dispatcher-input` (`policy/threat-model.toml:26-44`).
- **Refutation tried:** „an attacker who can write policy/ flips the classes" — true,
  and already modelled by the `policy-data` row (`policy/threat-model.toml:85-92`,
  control `capability.py` + `tests/test_capabilities.py`); the classifier adds no new
  hostile-pointing surface. Kept as PASS.
- **What closes it:** nothing further required; wiring S-4 would inherit the existing
  policy-write protection.

### S-6 — corpus refusals as instruction sources are own-authored static text
- **Boundary crossed:** skill text → model instructions and routing (the
  `skill-instructions` row).
- **Attacker control:** none on the text (commit-controlled, in-tree, not writable);
  a prompt attacker can only *quote* the refused shapes back at the model.
- **Reachable effect:** over-refusal / mis-route of an in-scope request (availability
  cost of the designed fail-closed posture); the route target is regex-scraped from
  prose (`tests/skill_eval.py:55-56` `_REFUSAL` → `_SKILL_TARGET`), so a future
  description edit silently re-routes refusals — an authoring hazard, not an attacker
  path.
- **State:** PASS (within the modeled boundary; control `contract.py` `_corpus_`
  problems`, checked by `tests/test_contracts.py`).
- **Command:** `grep -n "Not for deciding" .agents/skills/ai-review/SKILL.md
  .agents/skills/ai-verify/SKILL.md` (lines 10/10) and corpus rows cited in §4.
- **Refutation tried:** „an edited refusal is an instruction nobody reviewed" — that is the
  threat-model harm for this exact asset; the added refusals were reviewed as part of
  this delta, and the control lane exists. The remaining risk is a *future* unreviewed
  edit, which is what the control is for. Kept as PASS.
- **What closes it:** nothing for this delta; the existing skill-instructions control
  stands.

### S-7 — no MCP servers declared by the repository
- **Boundary crossed:** n/a (none declared).
- **Attacker control:** n/a.
- **Reachable effect:** n/a.
- **State:** PASS (not applicable).
- **Command:** `find . -name "*.mcp.json" -o -name "mcp*.json"` (nothing);
  `grep -rn "mcp" --include="*.json" --include="*.toml" --include="*.yml" .`
  (only a requirements note naming `hooks/chain.py`).
- **Refutation tried:** „the session's MCP tools (pencil, node_repl, arcasiles-brand)
  are declared somewhere" — yes, in the hosting harness, outside this repository and
  outside its authority to audit; recorded as external, not counted as repo-declared.
  Kept as PASS for the repo question.
- **What closes it:** n/a.

### S-8 — nothing running is declared safe
- **Boundary crossed:** deployed service → scanner coverage.
- **Attacker control:** n/a — nothing is deployed by this delta or scanned as running.
- **Reachable effect:** n/a.
- **State:** INCOMPLETE is the honest answer for any running service — and here the dast
  lane says it out loud: „nothing here scanned a running target: that needs a URL
  somebody authorised, and this gate never has one" (SKIPPED).
- **Command:** `just security` dast lane (output in §3).
- **Refutation tried:** „there is nothing running, so nothing to scan" — true for this
  tree; a deployment would need the target-and-authorisation contract the skill names as
  unapproved. Kept as SKIPPED-with-reason, deciding nothing about any live service.
- **What closes it:** when a service is ever deployed, an authorised URL and target-and-
  authorisation contract must exist before any file-scan-based PASS is claimed.

## 7. Authority boundary

No risk is accepted in this file — that is `ai-eng accept` with a named person, a reason
and an expiry. No compliance is declared — the skill has no standing to. The gate is red
(S-1) and the red is recorded, not waved through. The delta's own files carry no scanner
finding; the findings that matter (S-2, S-3, S-4) are contract and reachability gaps in
the classifier as built, and each names what closes it.