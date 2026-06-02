---
execution_route:
  version: 1
  spec: spec-160
  executor: build
  automation: assisted
  concern_count: 3
  estimated_files: 9
  reason: >
    Three coupled hardening facets (fail-closed, doc-context, path-equivalence)
    all land in one hot-path module (prompt-injection-guard.py) plus one shared
    test file. A single phased /ai-build run with TDD pairs fits better than a
    sub-spec DAG. /ai-autopilot is a valid override if wave decomposition is
    preferred.
  safe_next_command: "/ai-build"
status: approved
spec: spec-160
title: "Plan — Harden Sentinel IOC runtime (fail-closed + doc-context + path-equivalence)"
pipeline: full
---

# Plan — spec-160 Harden Sentinel IOC runtime

## Pipeline classification

`full` — security-sensitive hardening of an existing hot-path guard, ~9 files,
new manifest config + schema + docs parity. Steps: discover (done) → architecture
→ risk → test-plan → decompose → dispatch.

## Executor route

`executor: build` (single cohesive module, TDD-friendly). The three gaps are
facets of one concern sharing `prompt-injection-guard.py` + `test_sentinel_runtime_iocs.py`,
so a phased build run is preferred over autopilot's sub-spec DAG. Override with
`/ai-autopilot` if you'd rather decompose into waves.

## Design routing

Skipped — backend security plumbing, no UI/UX surface (`--skip-design` rationale:
hook-internal logic + config + tests only).

## Architecture

Pattern: **ad-hoc hot-path hook hardening** (no canonical pattern applies). The
guard is a single PreToolUse filter module. All changes are additive seams inside
the existing decision flow:

```
main() decision lanes (unchanged order)
  ├─ tool not guarded / too short / sub-agent / trusted-script / whitelist
  ├─ _is_test_fixture_target  → full IOC skip (existing)
  ├─ [NEW] _is_doc_target     → narrowed IOC skip (sensitive_paths + sensitive_env_vars)
  └─ evaluate_against_iocs(..., skip_categories=…)
        ├─ load_iocs → empty?
        │     ├─ [NEW] fail-closed enabled + catalog unavailable → deny
        │     └─ else → allow (today's default, test-pinned)
        ├─ per-category match via _match_pattern
        │     └─ [NEW] _expand_user_path → POSIX+Windows equivalence
        └─ verdict allow/deny/warn
  └─ Layer-2 _lib/injection_patterns scan  (ALWAYS runs — untouched)
```

Key invariants preserved: Layer-2 injection scan never bypassed; default posture
unchanged (fail-open) unless flag set; risk-accept lane fires before IOC eval.

## Risk register (plan-level)

- Touching `evaluate_against_iocs` / `_match_pattern` is hot-path — every guarded
  Bash/Write call. Mitigation: precompile expanded forms with `functools.lru_cache`;
  keep per-call allocation minimal.
- Two existing tests pin fail-open (`test_hook_fail_open_when_catalog_missing` @184,
  `test_hook_exposes_load_iocs_fail_open` @132). Must be made flag-aware, NOT deleted.
- `manifest.schema.json` is `additionalProperties:false` → unscoped `security:` key
  fails validation. Schema patch is a hard dependency of the manifest task.
- `tests/architecture/test_tunables_docs_match_code.py` enforces env-tunable↔doc
  parity → `AIENG_IOC_FAIL_CLOSED` must be added to BOTH code and the tunables doc
  source (`scripts/sync_mirrors/core.py`) in the same change.
- CLAUDE.md is generated — never hand-edit; edit `scripts/sync_mirrors/core.py`
  then run `ai-eng dev sync`.
- Meta-gotcha: building/testing this with the guard active will itself trip the IOC
  scan + risk accumulator on security test content. Until the doc-bypass lands,
  prefer test-fixture paths (already bypassed) for IOC literals; clear
  `.ai-engineering/runtime/risk-score.json` if the accumulator locks the session.

---

## Phase 1 — Gap #3: path-equivalence matcher (POSIX + Windows)

Self-contained, no config; highest evasion-risk. TDD first.

- [x] **T-1 — RED: path-equivalence test matrix**
  - Agent: build
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): _none — judgment._ Add a parametrized test asserting
    `evaluate_against_iocs(root, payload)["verdict"] == "deny"` for each equivalent
    form of one catalog sensitive-path entry (pick an `~/`-prefixed catalog literal):
    `~/X`, `$HOME/X`, `${HOME}/X`, `/Users/u/X`, `/home/u/X`, and Windows
    `C:\Users\u\X` (backslash, mixed-case). Use the real vendored catalog. These
    FAIL today (only the `~/X` form matches).
  - Gate: new tests RED (5 of 6 forms currently allow).

- [x] **T-2 — GREEN: implement `_expand_user_path` + Windows branch in `_match_pattern`**
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/prompt-injection-guard.py:654-733`
  - Principles applied: §10.4 DRY, §10.1 KISS, §10.7 Clean Code
  - Patch (deterministic): _none — regex judgment._ Replace the identity stub so an
    `~/`-prefixed literal pattern matches its equivalence set. Sketch:
    - `_expanded_literals(pattern) -> list[str]`: for `~/X` return
      `["~/X", "$HOME/X", "${HOME}/X"]`; else `[pattern]`. `@functools.lru_cache`.
    - `_home_path_regex(pattern) -> re.Pattern | None`: for `~/X` compile a POSIX
      absolute-home alternative `(?:/Users/[^/\s]+|/home/[^/\s]+)/<escaped X>` plus a
      Windows alternative `[A-Za-z]:\\Users\\[^\\\s]+\\<escaped X, / → \\>` with
      `re.IGNORECASE`. Cache it. Return None for non-home patterns.
    - `_match_pattern` literal branch: `any(f in content for f in _expanded_literals(pattern))`
      `or` (`rx := _home_path_regex(pattern)`) and `rx.search(content)`. Backslash-
      normalize a COPY of content for the Windows compare only — never mutate the
      POSIX match path (R3).
  - Gate: T-1 GREEN; existing `~/`-form sensitive-path tests still pass.

- [x] **T-3 — VERIFY: Phase 1 regression**
  - Agent: verify
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): _none._
  - Gate: `uv run --python .venv/bin/python pytest -q tests/integration/test_sentinel_runtime_iocs.py` green.

## Phase 2 — Gap #2: doc-context bypass (scoped to credential categories)

- [x] **T-4 — RED: doc-target bypass tests (allow + still-deny)**
  - Agent: build
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): _none — judgment._ Tests via the hook `main()` entrypoint
    (or a `tool_input`-shaped helper) asserting:
    (a) `Write` to `notes.md` with a sensitive-path/env-var literal → allow + an
        `ioc-scan-doc-context-bypass` event emitted;
    (b) same content to `notes.py` / `config.yml` → deny;
    (c) same literal via `Bash` → deny;
    (d) doc target containing a catalog malicious-domain → STILL deny;
    (e) doc target containing a Layer-2 injection phrase → STILL blocked.
  - Gate: new tests RED.

- [x] **T-5 — GREEN: `_is_doc_target` classifier**
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/prompt-injection-guard.py` (new fn near `:417`)
  - Principles applied: §10.3 SOLID (single-responsibility), §10.4 DRY
  - Patch (deterministic):
    ```python
    _DOC_EXTENSIONS = (".md", ".mdx", ".markdown", ".rst", ".txt")


    def _is_doc_target(tool_name: str, tool_input: dict) -> str | None:
        """Return file_path when Write/Edit targets a non-executable doc file.

        spec-160 D-160-04: documentation/spec/runbook text legitimately cites
        sensitive-path and env-var literals. Such targets bypass ONLY the
        sensitive_paths / sensitive_env_vars IOC categories (D-160-05); the
        malicious_domains / shell_patterns categories and the Layer-2 injection
        scan still apply. The call site emits an auditable bypass event.
        """
        if tool_name not in ("Write", "Edit", "MultiEdit"):
            return None
        file_path = tool_input.get("file_path") or ""
        if not isinstance(file_path, str) or not file_path:
            return None
        if Path(file_path).suffix.lower() in _DOC_EXTENSIONS:
            return file_path
        return None
    ```
  - Gate: unit import + classifier truth-table.

- [x] **T-6 — GREEN: `skip_categories` param on `evaluate_against_iocs`**
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/prompt-injection-guard.py:736-770`
  - Principles applied: §10.3 SOLID, §10.1 KISS
  - Patch (deterministic):
    ```python
    def evaluate_against_iocs(
        project_root: Path,
        content: str,
        *,
        catalog: dict[str, Any] | None = None,
        now: datetime | None = None,
        skip_categories: tuple[str, ...] = (),
    ) -> dict[str, Any]:
    ```
    and in the category loop:
    ```python
        for category in _IOC_CATEGORIES:
            if category in skip_categories:
                continue
            for kind, pattern in _category_patterns(cat, category):
    ```
  - Gate: existing eval tests unaffected (default `skip_categories=()`).

- [x] **T-7 — GREEN: wire doc bypass into `main()` + emit audit event**
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/prompt-injection-guard.py:1000-1012`
  - Principles applied: §10.4 DRY (mirror fixture-bypass block), §10.7 Clean Code
  - Patch (deterministic): _partial — mirror the `_is_test_fixture_target` block at
    `:985-1002` but DO NOT `return`; instead set the skip set and thread it into the
    eval call._ Insert before the `evaluate_against_iocs` call:
    ```python
        doc_path = _is_doc_target(tool_name, tool_input)
        skip_cats: tuple[str, ...] = ()
        if doc_path is not None:
            skip_cats = ("sensitive_paths", "sensitive_env_vars")
            with contextlib.suppress(Exception):
                emit_control_outcome(
                    ctx.project_root,
                    category="security",
                    control="ioc-scan-doc-context-bypass",
                    component="hook.prompt-injection-guard",
                    outcome="success",
                    source="hook",
                    metadata={"tool": tool_name, "file_path": doc_path,
                              "skipped_categories": list(skip_cats)},
                )
        ioc_result = evaluate_against_iocs(ctx.project_root, scan_content, skip_categories=skip_cats)
    ```
    (replaces the existing bare `ioc_result = evaluate_against_iocs(ctx.project_root, scan_content)`).
  - Gate: T-4 GREEN.

- [x] **T-8 — VERIFY: Phase 2 regression + audit-event shape**
  - Agent: verify
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`
  - Principles applied: §10.5 TDD
  - Gate: doc-bypass tests green; no audit metadata carries the raw matched literal
    (Open Question resolution: category + path only).

## Phase 3 — Gap #1: opt-in fail-closed

- [x] **T-9 — RED: fail-closed tests (flag on/off × missing/corrupt)**
  - Agent: build
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): _none — judgment._ Add (monkeypatching env / a tmp manifest):
    (a) flag OFF (default) + missing catalog → `verdict == "allow"` (keeps contract);
    (b) `AIENG_IOC_FAIL_CLOSED=1` + missing → `verdict == "deny"`, reason names recovery;
    (c) flag on + corrupt JSON → `verdict == "deny"`;
    (d) flag on + valid-but-empty `{}` catalog supplied via `catalog=` param → allow
        (supplied empty ≠ unavailable file).
  - Gate: new tests RED.

- [x] **T-10 — GREEN: `_fail_closed_enabled` + `_ioc_catalog_unavailable` + deny branch**
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/prompt-injection-guard.py:481-530,763-765`
  - Principles applied: §10.3 SOLID, §10.7 Clean Code
  - Patch (deterministic): _none — judgment._ Implement:
    - `_fail_closed_enabled(project_root) -> bool`: env `AIENG_IOC_FAIL_CLOSED` in
      `{"1","0"}` wins; else lazy `import yaml` read of `manifest.yml`
      `security.iocs.fail_closed` (precedent: `_lib/instincts.py:24`); fail-open to
      `False` on any ImportError/parse error.
    - `_ioc_catalog_unavailable(project_root) -> bool`: True iff the catalog file is
      missing OR read/parse raises (distinguishes unavailable from valid-empty).
    - In `evaluate_against_iocs`, change the `if not cat:` branch: only when the
      catalog was loaded from disk (i.e. `catalog is None` arg) AND
      `_fail_closed_enabled` AND `_ioc_catalog_unavailable` → return
      `{"verdict":"deny","matches":[], "reason": <recovery message>}`; else keep
      `allow`. Recovery message names: restore `iocs.json`, set
      `AIENG_IOC_FAIL_CLOSED=0`, or `ai-eng risk accept`.
  - Gate: T-9 GREEN; the two pinned fail-open tests still pass under default (flag off).

- [x] **T-11 — GREEN: make the two pinned fail-open tests flag-aware**
  - Agent: build
  - Files: `tests/integration/test_sentinel_runtime_iocs.py:132,184`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): _none — judgment._ Ensure both tests run with the flag
    explicitly OFF (clear `AIENG_IOC_FAIL_CLOSED`) so they keep asserting `allow`,
    documenting that default = fail-open. Do NOT delete them (D-160-09).
  - Gate: both pass; intent comment references D-160-01.

- [x] **T-12 — VERIFY: Phase 3 regression**
  - Agent: verify
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`, `tests/integration/test_sentinel_risk_accept.py`
  - Principles applied: §10.5 TDD
  - Gate: full Sentinel slice green (target ≥ 44 + new cases).

## Phase 4 — Config, schema & docs parity

- [x] **T-13 — manifest `security.iocs.fail_closed` + schema**
  - Agent: build
  - Files: `.ai-engineering/manifest.yml`, `.ai-engineering/schemas/manifest.schema.json`
  - Principles applied: §10.6 SDD, §13.7 Single Source of Truth
  - Patch (deterministic): append to `manifest.yml`:
    ```yaml
    security:
      iocs:
        # spec-160 D-160-01: opt-in fail-closed. Default false = bootstrap-safe
        # fail-open. Env AIENG_IOC_FAIL_CLOSED overrides.
        fail_closed: false
    ```
    and add to `manifest.schema.json` `properties` (top-level `additionalProperties`
    is false, so the key MUST be declared):
    ```json
    "security": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "iocs": {
          "type": "object",
          "additionalProperties": false,
          "properties": { "fail_closed": { "type": "boolean" } }
        }
      }
    }
    ```
  - Gate: `ai-eng doctor` / manifest validation green; `manifest_coherence` validator passes.

- [x] **T-14 — document `AIENG_IOC_FAIL_CLOSED` tunable (source, not generated)**
  - Agent: build
  - Files: `scripts/sync_mirrors/core.py` (tunables block), then `ai-eng dev sync`
  - Principles applied: §13.7 Single Source of Truth, §10.6 SDD
  - Patch (deterministic): _none — locate the runtime-tunables block in core.py and
    add `AIENG_IOC_FAIL_CLOSED` (with a one-line description) alongside the other
    `AIENG_*` entries; regenerate `CLAUDE.md` + `templates/project/CLAUDE.md` via
    `ai-eng dev sync`. Never hand-edit the generated CLAUDE.md files._
  - Gate: `tests/architecture/test_tunables_docs_match_code.py` green; sync leaves
    no drift (`git diff` only the intended files).

- [x] **T-15 — CHANGELOG entry**
  - Agent: build
  - Files: `CHANGELOG.md`
  - Principles applied: §13 Hard Rules (CHANGELOG documents behavior changes)
  - Patch (deterministic): _none._ Add an entry under the unreleased section noting:
    opt-in IOC fail-closed (`security.iocs.fail_closed` / `AIENG_IOC_FAIL_CLOSED`),
    doc-context IOC bypass for `*.md`/`*.rst`/`*.txt` (credential categories only),
    and POSIX+Windows path-equivalence matching. Note the default behavior is unchanged.
  - Gate: docs gate (`/ai-docs` / pre-push) green.

## Phase 5 — Final quality loop

- [x] **T-16 — full guard + Sentinel battery**
  - Agent: verify
  - Files: `tests/integration/test_sentinel_runtime_iocs.py`, `tests/integration/test_sentinel_risk_accept.py`, `tests/unit/hooks/`, `tests/architecture/test_tunables_docs_match_code.py`
  - Principles applied: §10.4 Goal-Driven Execution
  - Gate: green; broader slice from issue #549 (74-test set) green.

- [x] **T-17 — hooks-manifest integrity re-pin**
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json`
  - Principles applied: §13 Hard Rules (hook integrity)
  - Patch (deterministic): _none._ Editing `prompt-injection-guard.py` changes its
    sha256 → regenerate the hooks integrity manifest so `enforce` mode does not kill
    the hook (known trap: editable installs + integrity drift).
  - Gate: `ai-eng doctor` hook-integrity check green; guard fires post-edit.

- [x] **T-18 — guard + review**
  - Agent: guard
  - Files: full changeset
  - Principles applied: §10.7 Clean Code, §13 Hard Rules
  - Gate: `/ai-verify` + `/ai-review` clean; no suppressions; secrets gate green.

---

## Gate summary

| Phase | Exit gate |
|-------|-----------|
| 1 | Path-equivalence matrix green; `~/`-form unregressed |
| 2 | Doc bypass allows cited literals on docs, still denies domain/injection/bash/source; audit event emitted, no literal in metadata |
| 3 | Fail-closed denies missing+corrupt under flag; default fail-open pins intact |
| 4 | Manifest+schema valid; tunables-docs parity test green; CHANGELOG present |
| 5 | Full Sentinel battery green; hook integrity re-pinned; verify+review clean |

## Open questions carried from spec

- Audit-event metadata shape for `ioc-scan-doc-context-bypass` — resolved in plan
  (T-8 gate): emit `category` + `file_path` + `skipped_categories`, never the raw
  matched literal.

safe_next_command: `/ai-build`

---

## Quality Outcome

Build complete (Phases 1–5). All 18 tasks done; no blocked tasks.

- **Tests**: Sentinel slice 64 passed; broad sweep (sentinel + hooks unit + tunables) 387 passed; docs 516 passed/3 skipped; surface/template/env-doc parity 16 passed. Combined guard battery 117 passed.
- **Integrity**: `hooks-manifest.json` re-pinned (75 hooks) after guard edit; integrity drift test green; enforce mode restored with hardened guard.
- **Review** (`/ai-review`, security lens): **SHIP** — 0 blocker/critical/high/medium. Two low/informational:
  - L1 — `_fail_closed_enabled` reads `manifest.yml` on the catalog-empty branch only (negligible; common path never hits it). No action.
  - L2 — pre-existing schema `required` drift (`skills`/`agents`/`ownership`/`tooling` absent from manifest) — out of scope, not CI-gated. Untouched.
- **Adversarial**: no path-form evasion and no new benign false-positive found.

Quality loop: PASS, zero remediation passes consumed. Ready for delivery (`/ai-pr`).
