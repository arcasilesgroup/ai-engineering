---
spec: spec-191
title: Plan — Injection Guard (read-side coverage + risk-accumulator precision)
status: approved
execution_route:
  version: 1
  spec: spec-191
  executor: autopilot
  automation: full
  concern_count: 4
  estimated_files: 26
  reason: >-
    Four concerns (D-191-03 IOC-core extraction refactor, D-191-02 allowlist wiring,
    D-191-01 new read-side PostToolUse hook, D-191-04 invariants) across the security
    plane. The extraction moves ~550 lines of IOC-eval logic into one _lib module; each
    hook change hits a byte-twin (canonical + template) with manifest regen. ≥3 concerns
    and >10 files → autopilot decomposes into sub-specs + waves; a single build would
    serialize four loosely-coupled tracks.
  safe_next_command: "/ai-autopilot"
---

Run /ai-plan after brainstorm approval.
# Plan — Injection Guard (spec-191)

## Summary

Close the injection guard's read-side blind spot and wire its dead allowlist. Decomposed
into four phases: (0) a characterization safety net, (1) extract the IOC-evaluation subsystem
into `_lib/ioc_eval.py` (single source, refactor-only), (2) wire the dead `allowlist` so
known-good hosts/paths stop driving false-positive deny/risk, (3) add a `PostToolUse`
`injection-read-guard.py` that scans fetched external content and warns (never blocks),
(4) integration + gates. Every hook edit is byte-twinned (canonical + template) and
regenerates the manifest.

## Architecture (ad-hoc — extends the existing layered `_lib` hook subsystem)

**Critical shared context — the guard is hook-only.** Unlike spec-190's telemetry layer
(three copies: pip `state/`, hook `_lib`, template twin), the injection guard lives in
exactly two copies:

| Copy | Path | Twin rule | Manifest |
|------|------|-----------|----------|
| hook canonical | `.ai-engineering/scripts/hooks/prompt-injection-guard.py` (+ new `injection-read-guard.py`, `_lib/ioc_eval.py`) | byte-identical to template twin (`cp`) | sha-pinned |
| hook template | `src/ai_engineering/templates/.ai-engineering/scripts/hooks/**` | byte-identical to canonical | (installer copy) |

No pip-side mirror of the guard logic exists (grep-confirmed `src/ai_engineering/` outside
`templates/` is empty). So the dual-writer surface here is **byte-twin parity only**, not
pip↔hook — simpler than spec-190, but the same byte-parity guard (landed in spec-190) must
stay green.

Hard rules (D-191-04), enforced as a gate on every hook-touching task:
1. Edit hook canonical → `cp` byte-identical to template twin.
2. Any hook byte change → `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`.
3. Hooks stay stdlib-only on the hot path (no `ai_engineering` import); pre-commit <1s.
4. Introspection/tests use `.venv/bin/python` (bare `python3` hits the py3.9 `datetime.UTC` trap).

**Extraction boundary (D-191-03):** `evaluate_against_iocs` (`:930`), `_host_ioc_regex`
(`:813`), `_category_patterns` (`:836`), `_match_pattern` (`:897`), `load_iocs` (`:504`),
the fail-closed helpers (`:562`–`:617`), the decision-store lookup
(`_decision_store_path` `:627`, `_load_decision_store` `:662`, `find_active_risk_acceptance`
`:697`, `canonical_finding_id` `:657`), and the path/host helpers (`_expand_literals` `:765`,
`_home_path_regex` `:784`) — the whole IOC-eval subsystem (~`:470`–`:1024`) plus the
`_IOC_CATEGORIES` const (`:210`) — move into `_lib/ioc_eval.py`. `prompt-injection-guard.py`
keeps `main()`, `_apply_risk`, the sub-agent/trusted-script lanes, and imports the evaluator
from `_lib.ioc_eval`.

## Phase 0 — Characterization safety net

- [ ] T-1 — RED: characterization test for `evaluate_against_iocs` verdicts
  - Agent: build
  - Files: `tests/unit/hooks/test_ioc_eval.py` (new)
  - Principles applied: §10.5 TDD (characterization before refactor)
  - Patch (deterministic): none — assert current behavior on fixtures: (a) clean content →
    `verdict=allow`; (b) content with a `pastebin_style` host → `verdict=deny` (unaccepted);
    (c) same host with an active risk-acceptance → `verdict=warn`; (d) a `.top` TLD in a
    benign dotted identifier → `allow` (boundary-anchored regex, spec-177).
  - Gate: `.venv/bin/python -m pytest tests/unit/hooks/test_ioc_eval.py` → FAIL (new file)

## Phase 1 — D-191-03 Extraction (refactor-only)

- [ ] T-2 — GREEN: create `_lib/ioc_eval.py` with the IOC-eval subsystem (+ template twin)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/ioc_eval.py` (new) → `cp` to
    `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/ioc_eval.py`
  - Principles applied: §10.4 DRY (single source of truth), §10.7 Clean Code (refactor, no
    behavior change)
  - Patch (deterministic): none — judgment (move the ~`:470`–`:1024` block verbatim into
    `_lib/ioc_eval.py`; add `from _lib.ioc_eval import evaluate_against_iocs,
    find_active_risk_acceptance, canonical_finding_id, load_iocs` at the guard's top; keep
    module docstring). Add `ioc_eval` to `__all__` in `_lib/__init__.py` if needed.
  - Gate: `.venv/bin/python -m pytest tests/unit/hooks/test_ioc_eval.py tests/unit/hooks/test_ioc_alias_loader.py tests/unit/hooks/test_prompt_injection_guard_cache.py` → PASS (characterization green, existing behavior identical)

- [ ] T-3 — GREEN: rewrite `prompt-injection-guard.py` to import the evaluator (+ twin + manifest)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/prompt-injection-guard.py` (delete moved defs,
    keep `main`/`_apply_risk`/lanes) → `cp` template twin
  - Principles applied: §10.3 SOLID (single responsibility), §10.4 DRY
  - Patch (deterministic): none — judgment (remove the duplicated block; `main()` continues
    to call `evaluate_against_iocs`/`_emit_ioc_outcomes` unchanged). No call-site change.
  - Gate: `cp` twin byte-identical → `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` → `.venv/bin/python -m pytest tests/unit/hooks` → all green

## Phase 2 — D-191-02 Allowlist wiring

- [ ] T-4 — RED: allowlisted host/path is dropped (no deny, no risk)
  - Agent: build
  - Files: `tests/unit/hooks/test_ioc_eval.py` (extend)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — assert: content citing a host in `allowlist.domains`
    (e.g. `raw.githubusercontent.com`) → `verdict=allow`, and `_apply_risk` is NOT called
    (no risk-score write); a path under `allowlist.paths` (`/tmp/...`) → same.
  - Gate: `.venv/bin/python -m pytest tests/unit/hooks/test_ioc_eval.py` → FAIL

- [ ] T-5 — GREEN: load `allowlist` in `ioc_eval` and drop allowlisted matches (+ twin + manifest)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/ioc_eval.py` (read `allowlist` from the
    catalog; mark `allowlisted=True`; skip deny/warn + risk) → `cp` template twin
  - Principles applied: §10.7 Clean Code (additive drop path), fail-open
  - Patch (deterministic): none — judgment (parse `catalog.get("allowlist")` once; in the
    match loop, if `kind=="host"` and the domain is in `allowlist.domains`, or a
    `sensitive_paths` match is rooted at an `allowlist.paths` entry → set `allowlisted=True`,
    do not append to `deny`/`warn`, do not feed `_apply_risk`). Absent/malformed allowlist →
    current behavior (match stands).
  - Gate: `cp` twin → `regenerate-hooks-manifest.py` → T-4 tests PASS + `pytest tests/unit/hooks` green

## Phase 3 — D-191-01 Read-side PostToolUse hook

- [ ] T-6 — RED: read-side hook warns + flags untrusted, never blocks
  - Agent: build
  - Files: `tests/unit/hooks/test_injection_read_guard.py` (new)
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — assert: a `tool_response` containing a malicious domain OR
    an injection phrase → `control_outcome` `control=content_untrusted`, `outcome=warning`,
    process exit 0; clean content → exit 0, no event; a non-external tool (e.g. `Bash`) →
    pass-through (no scan).
  - Gate: `.venv/bin/python -m pytest tests/unit/hooks/test_injection_read_guard.py` → FAIL

- [ ] T-7 — GREEN: create `injection-read-guard.py` (+ twin)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/injection-read-guard.py` (new) → `cp` to
    `src/ai_engineering/templates/.ai-engineering/scripts/hooks/injection-read-guard.py`
  - Principles applied: §10.8 stdlib-only hot path, §10.4 DRY (reuse `_lib.ioc_eval` +
    `_lib.injection_patterns.PATTERNS`), §10.7 Clean Code
  - Patch (deterministic): none — judgment (`main()`: `ctx = get_hook_context()`;
    `tool_name = ctx.data.get("tool_name")`; if not in external set
    `{Read, WebFetch, WebSearch, mcp__exa__*, mcp__tavily__*}` → passthrough; read
    `tool_response = ctx.data.get("tool_response")`; coerce via `_coerce_text`/`_coerce_mapping`;
    run `evaluate_against_iocs(project_root, text, skip_categories=...)` AND scan
    `injection_patterns.PATTERNS`; on any match emit `emit_control_outcome(category="security",
    control="content_untrusted", outcome="warning", source="hook", metadata={tool, category,
    pattern, finding_id})` + print one-line `additionalContext` banner; `sys.exit(0)` always.
    Never `exit(2)`.)
  - Gate: `cp` twin → `regenerate-hooks-manifest.py` → `pytest tests/unit/hooks/test_injection_read_guard.py` → PASS

- [ ] T-8 — GREEN: register the read-side hook under PostToolUse (+ manifest)
  - Agent: build
  - Files: `.claude/settings.json` (PostToolUse array — add a `matcher: ""` entry invoking
    `run-hook.sh injection-read-guard.py`; internal tool filter does the scoping)
  - Principles applied: §10.1 KISS (register once, filter inside the hook)
  - Patch (deterministic):
    ```diff
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh\" \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/injection-read-guard.py\"",
            "timeout": 10
          }
        ]
      },
    ```
    (append as a new PostToolUse entry, sibling to the existing `runtime-guard.py` `matcher: ""`
    entry)
  - Gate: `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py --check` clean; hook
    listed in manifest; `pytest tests/unit/hooks` green

## Phase 4 — Integration, gates, delivery

- [ ] T-9 — Final manifest regen + spec_lint clean (plan frontmatter present)
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json`, `.ai-engineering/specs/plan.md`
  - Principles applied: §13 Hard Rules (hook integrity)
  - Patch (deterministic): none
  - Gate: `regenerate-hooks-manifest.py --check` clean; `PYTHONPATH=tools .venv/bin/python -m spec_lint --check .ai-engineering/specs/spec.md` → 0 BLOCKERS (plan_frontmatter present)

- [ ] T-10 — Full verification pass
  - Agent: verify
  - Files: whole changeset
  - Principles applied: §10.5 TDD, §13 (gates)
  - Patch (deterministic): none
  - Gate: `.venv/bin/python -m pytest tests/unit tests/integration` green; `ai-eng doctor`
    no new FAIL; gitleaks / ruff / pip-audit clean; no `# noqa`/suppressions introduced (§13.2)

- [ ] T-11 — Byte-twin final audit
  - Agent: verify
  - Files: `prompt-injection-guard.py`, `injection-read-guard.py`, `_lib/ioc_eval.py` vs their
    template twins
  - Principles applied: §13.7 SSOT, §10.4 DRY
  - Patch (deterministic): none
  - Gate: `pytest tests/unit/test_hook_template_parity.py` PASS; manual diff confirms canonical
    == template for all three edited hook files

## Risks & rollback

- **Extraction regression** (write-side guard behavior changes). Mitigated by T-1
  characterization test + the existing write-side guard suite (T-2/T-3 must keep it green).
- **Manifest staleness self-disables hooks** if a twin `cp`/regen is skipped. Mitigated by the
  spec-190 byte-parity guard (green) + a regen gate on every hook edit.
- **Read-side latency per fetched result.** Mitigated by the mtime-LRU IOC cache, bounded
  `_MAX_CONTENT_LEN`, external-tools-only, always exit 0 (warn-only).
- **Allowlist false-negative** (a real malicious host that happens to be allowlisted). Mitigated
  by fail-open: unknown/malformed allowlist keeps current deny behavior; the allowlist is
  operator-curated in `iocs.json`.
- **Rollback**: each phase is independent; revert a phase's commits without touching others.
  No schema break — all new fields/events additive.
