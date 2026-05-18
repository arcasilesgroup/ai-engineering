---
spec: spec-142
slug: surface-aware-dashboard
title: plan — surface-aware /ai-start dashboard header
pipeline: standard
files_touched: 4
tdd_pairs: 4
---

# Plan — spec-142 surface-aware-dashboard

> Pre-flight: `design-routing: skipped (apparent false-positive — "dashboard"
> in spec refers to the markdown emitted by `session_bootstrap.py`, not a
> visual UI). Rationale logged per `handlers/design-routing.md` §Output
> Behavior. Re-invoke `/ai-plan --skip-design` to suppress on future runs.

## Architecture

`ad-hoc` — small procedural script change in `session_bootstrap.py` (stdlib,
no internal abstractions) plus a CLI post-install step in
`cli_commands/core.py`. No layered/hexagonal/CQRS framing applies. Justified
by the four-file scope and absence of new domain boundaries: the change is
behavioural completeness inside an existing entry point, not architectural
restructuring.

## Phases

**Phase 1 — Mini-parser fallback** (D-142-01, D-142-07). Stdlib reader for
`name` and `surfaces.enabled` when pyyaml is absent. Unblocks `(unnamed)`
and surface resolution in installs without pyproject.toml.

**Phase 2 — Surface-aware counts** (D-142-02, D-142-03). Inline
`_SURFACE_DIRS` map + CI paridad test against the pip package
`_PROVIDER_TREE_MAPS`. Rewires `_count_skills` / `_count_agents` to
dispatch on `surfaces.enabled[0]`.

**Phase 3 — Hooks unverified state** (D-142-04). Distinguish "install
incomplete" from "filesystem corrupt"; markdown surfaces an actionable
hint.

**Phase 4 — Installer auto-regenerate** (D-142-05). `ai-eng install`
finalizes by invoking `regenerate-hooks-manifest.py`, warn-and-continue
on failure.

**Phase 5 — JSON contract surface_resolved** (D-142-06). Optional
top-level field so tooling can detect unknown surfaces.

**Phase 6 — Quality loop**. Final single-round fail-loud verify+review
on the changeset.

---

## Phase 1 — Mini-parser fallback

- [x] T-1 — RED: stdlib mini-parser contract test @ai-build — DONE (real)
- Agent: build
- Files: tests/unit/scripts/test_minimal_manifest_parse.py:1 (NEW)
- Principles applied: §10.5 TDD (RED before GREEN), §10.1 KISS (2-field grammar)
- Patch (deterministic): omit — synthesis required (test design).
- Gate: pytest -q tests/unit/scripts/test_minimal_manifest_parse.py exits 1 with `ModuleNotFoundError` / `AttributeError` on `_read_manifest_minimal`. Test cases must cover: (a) flow list `surfaces.enabled: [github-copilot]`, (b) block list `surfaces:\n  enabled:\n  - github-copilot`, (c) unquoted `name: ai-engineering`, (d) double-quoted `name: "ai-engineering"`, (e) equality with `yaml.safe_load` on the real `.ai-engineering/manifest.yml`, (f) missing field returns `{}`, (g) malformed file returns `{}` not raises.

- [x] T-2 — GREEN: implement `_read_manifest_minimal` @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:115 (add helper)
- Principles applied: §10.5 TDD (make RED pass), §10.1 KISS, §10.2 YAGNI (only 2 fields)
- Patch (deterministic): omit — function is regex-driven; small but not mechanical (handles 4 grammars per D-142-07).
- Gate: pytest -q tests/unit/scripts/test_minimal_manifest_parse.py exits 0. Function ≤ 30 LOC.

- [x] T-3 — GREEN: wire fallback into `_read_manifest` @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:282
- Principles applied: §10.4 DRY (single fallback path), §10.5 TDD
- Patch (deterministic):
  ```diff
  @@ def _read_manifest(root: Path) -> dict:
  -    return _read_yaml(root / ".ai-engineering" / "manifest.yml") or {}
  +    path = root / ".ai-engineering" / "manifest.yml"
  +    data = _read_yaml(path)
  +    if data is not None:
  +        return data
  +    return _read_manifest_minimal(path)
  ```
- Gate: existing test_session_bootstrap.py suite still passes; `/ai-start` on a venv without pyyaml resolves `project_name` to `"ai-engineering"` instead of `"(unnamed)"`.

---

## Phase 2 — Surface-aware counts

- [x] T-4 — RED: `_SURFACE_DIRS` paridad test @ai-build — DONE (real)
- Agent: build
- Files: tests/unit/scripts/test_session_bootstrap.py (extend with new test class `TestSurfaceDirs`)
- Principles applied: §10.5 TDD, §10.3 SOLID (DI of canonical enum), §10.7 Clean Code
- Patch (deterministic): omit — test reads canonical enum from `src/ai_engineering/config/mirror_inventory.py` `_PROVIDER_TREE_MAPS` keys (4 mirror-bearing surfaces) UNION with `{"opencode", "cursor", "antigravity"}` (the 3 enum members without mirror trees in `_PROVIDER_TREE_MAPS` but with `templates/project/.<surface>/skills/` directories). Assert `_SURFACE_DIRS.keys() == {7-surface set}`. Second assertion: each value pair `(skills_dir, agents_dir)` matches the templates/project/ layout.
- Gate: pytest -q tests/unit/scripts/test_session_bootstrap.py::TestSurfaceDirs exits 1 with `AttributeError` (no `_SURFACE_DIRS` yet).

- [x] T-5 — GREEN: add `_SURFACE_DIRS` constant @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:97 (insert constant block)
- Principles applied: §10.5 TDD, §10.1 KISS
- Patch (deterministic):
  ```diff
  @@
   _REPO_ROOT = Path(__file__).resolve().parents[2]
  +
  +# spec-142 D-142-02: surface→(skills, agents) directory map. Keys MUST stay
  +# in sync with the closed 7-surface enum at
  +# src/ai_engineering/config/mirror_inventory.py (`_PROVIDER_TREE_MAPS` keys
  +# plus the no-mirror-tree surfaces). CI test in
  +# tests/unit/scripts/test_session_bootstrap.py::TestSurfaceDirs enforces parity.
  +_SURFACE_DIRS: dict[str, tuple[str, str]] = {
  +    "claude-code":    (".claude/skills",   ".claude/agents"),
  +    "codex":          (".codex/skills",    ".codex/agents"),
  +    "gemini-cli":     (".gemini/skills",   ".gemini/agents"),
  +    "github-copilot": (".github/skills",   ".github/agents"),
  +    "opencode":       (".opencode/skills", ".opencode/agents"),
  +    "cursor":         (".cursor/skills",   ".cursor/agents"),
  +    "antigravity":    (".agent/skills",    ".agent/agents"),
  +}
  +_DEFAULT_SURFACE = "claude-code"  # spec-133 D-133-16 fallback when surfaces.enabled is empty
  ```
- Gate: pytest -q tests/unit/scripts/test_session_bootstrap.py::TestSurfaceDirs exits 0.

- [x] T-6 — RED: surface-aware count test @ai-build — DONE (real)
- Agent: build
- Files: tests/unit/scripts/test_session_bootstrap.py (add `TestSurfaceAwareCounts`)
- Principles applied: §10.5 TDD, §10.7 Clean Code (descriptive tmp fixtures)
- Patch (deterministic): omit — test scaffolds a tmp root with `.ai-engineering/manifest.yml` declaring `surfaces.enabled: [github-copilot]` and 3 stub skill dirs under `.github/skills/`, asserts `_count_skills(tmp) == 3`. Repeat for claude-code (default) and codex. Edge: empty `surfaces.enabled` → fallback to `_DEFAULT_SURFACE`.
- Gate: pytest exits 1 — `_count_skills` still hardcodes `.claude/`.

- [x] T-7 — GREEN: rewire `_count_skills` and `_count_agents` @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:335-346
- Principles applied: §10.5 TDD, §10.4 DRY (extract `_primary_surface(manifest)`)
- Patch (deterministic):
  ```diff
  @@
  -def _count_skills(root: Path) -> int:
  -    base = root / ".claude" / "skills"
  -    if not base.is_dir():
  -        return 0
  -    return sum(1 for p in base.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
  -
  -
  -def _count_agents(root: Path) -> int:
  -    base = root / ".claude" / "agents"
  -    if not base.is_dir():
  -        return 0
  -    return sum(1 for p in base.glob("ai-*.md") if p.is_file())
  +def _primary_surface(manifest: dict) -> str:
  +    surfaces = manifest.get("surfaces") or {}
  +    enabled = surfaces.get("enabled") if isinstance(surfaces, dict) else None
  +    if isinstance(enabled, list) and enabled:
  +        first = enabled[0]
  +        if isinstance(first, str) and first in _SURFACE_DIRS:
  +            return first
  +    return _DEFAULT_SURFACE
  +
  +
  +def _count_skills(root: Path, manifest: dict) -> int:
  +    skills_rel, _ = _SURFACE_DIRS.get(_primary_surface(manifest), _SURFACE_DIRS[_DEFAULT_SURFACE])
  +    base = root / skills_rel
  +    if not base.is_dir():
  +        return 0
  +    return sum(1 for p in base.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
  +
  +
  +def _count_agents(root: Path, manifest: dict) -> int:
  +    _, agents_rel = _SURFACE_DIRS.get(_primary_surface(manifest), _SURFACE_DIRS[_DEFAULT_SURFACE])
  +    base = root / agents_rel
  +    if not base.is_dir():
  +        return 0
  +    return sum(1 for p in base.glob("ai-*.md") if p.is_file())
  ```
- Gate: pytest test_session_bootstrap.py::TestSurfaceAwareCounts exits 0. Update all call sites (lines ~985-986 in `main`) to pass manifest. Pre-T-7 sanity: `grep -n "_count_skills\|_count_agents" .ai-engineering/scripts/ tests/ | grep -v __pycache__` to confirm `main()` is the sole caller; if any other test calls these helpers directly, update its fixture before T-7 lands.

- [x] T-8 — GREEN: update call sites in `main()` @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:985-986
- Principles applied: §10.5 TDD, §10.3 SOLID (single responsibility kept)
- Patch (deterministic):
  ```diff
  @@
  -        "skills_total": _count_skills(root),
  -        "agents_total": _count_agents(root),
  +        "skills_total": _count_skills(root, manifest),
  +        "agents_total": _count_agents(root, manifest),
  ```
- Gate: full session_bootstrap test module passes; manual run on `/Users/soydachi/repos/test/` shows skills/agents counts non-zero.

---

## Phase 3 — Hooks unverified state

- [x] T-9 — RED: `_hooks_health` unverified test @ai-build — DONE (real)
- Agent: build
- Files: tests/unit/scripts/test_session_bootstrap.py (extend `TestHooksHealth` or add)
- Principles applied: §10.5 TDD
- Patch (deterministic): omit — three cases: (a) manifest exists + matches → `"ok"`, (b) manifest exists + drift → `"drift(N)"`, (c) manifest MISSING + `scripts/hooks/` has files → `"unverified"`, (d) manifest MISSING + `scripts/hooks/` missing → `"unknown"`, (e) manifest exists but `hooks` key empty/non-dict → `"unknown"`.
- Gate: pytest exits 1 on case (c) — current logic returns `"unknown"`.

- [x] T-10 — GREEN: update `_hooks_health` branching @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:291-327
- Principles applied: §10.5 TDD, §10.7 Clean Code (guard clause early)
- Patch (deterministic):
  ```diff
  @@ def _hooks_health(root: Path) -> str:
  -    manifest_path = root / ".ai-engineering" / "state" / "hooks-manifest.json"
  -    if not manifest_path.is_file():
  -        return "unknown"
  +    manifest_path = root / ".ai-engineering" / "state" / "hooks-manifest.json"
  +    scripts_dir = root / ".ai-engineering" / "scripts" / "hooks"
  +    if not manifest_path.is_file():
  +        if scripts_dir.is_dir() and any(scripts_dir.iterdir()):
  +            return "unverified"
  +        return "unknown"
  ```
- Gate: pytest test_session_bootstrap.py::TestHooksHealth exits 0.

- [x] T-11 — GREEN: markdown rendering hint for `unverified` @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:840 (state line builder)
- Principles applied: §10.5 TDD, §10.7 Clean Code (string literal explicit)
- Patch (deterministic):
  ```diff
  @@
  -    state.append(f"hooks: {d.get('hooks_health', 'unknown')}")
  +    hh = d.get("hooks_health", "unknown")
  +    if hh == "unverified":
  +        state.append("hooks: unverified — run `regenerate-hooks-manifest.py`")
  +    else:
  +        state.append(f"hooks: {hh}")
  ```
- Gate: snapshot test or string-contains assertion on the rendered markdown when `hooks_health == "unverified"`.

---

## Phase 4 — Installer auto-regenerate

- [x] T-12 — RED: install_cmd calls regenerate-hooks-manifest @ai-build — DONE (real)
- Agent: build
- Files: tests/unit/cli_commands/test_install_cmd_hooks_manifest.py:1 (NEW) — locate the cli_commands test dir first; if absent fall back to tests/unit/test_install_cmd_hooks_manifest.py
- Principles applied: §10.5 TDD, §10.3 SOLID (mock subprocess)
- Patch (deterministic): omit — synthesis: invoke `install_cmd` against a tmp target, assert that `.ai-engineering/state/hooks-manifest.json` exists after the call with at least one entry. Second case: monkeypatch the regenerate script to fail and assert install_cmd emits a stderr warning but exits 0.
- Gate: pytest exits 1 — install_cmd does not yet call the regenerate script.

- [x] T-13 — GREEN: append regenerate-hooks-manifest call to install_cmd @ai-build — DONE (real)
- Agent: build
- Files: src/ai_engineering/cli_commands/core.py:95 (end of `install_cmd` body, before return)
- Principles applied: §10.5 TDD, §10.2 YAGNI (no new flags), warn-don't-abort
- Patch (deterministic): omit — must locate the install_cmd's "finalization" block (after manifest write, before returning); use `subprocess.run([sys.executable, str(regen_script), "--check"], check=False)` with explicit timeout (e.g. 30 s) and stderr-routed warning on non-zero exit. Reuse `console.print` if available in scope.
- Gate: T-12 test exits 0. Manual install into a tmp dir → `hooks-manifest.json` present.

---

## Phase 5 — JSON contract surface_resolved

- [x] T-14 — RED: JSON output includes `surface_resolved` @ai-build — DONE (real)
- Agent: build
- Files: tests/unit/scripts/test_session_bootstrap.py (extend)
- Principles applied: §10.5 TDD, §10.2 YAGNI (field is optional)
- Patch (deterministic): omit — assert the JSON output of `--format=json` mode contains key `surface_resolved` matching `_primary_surface(manifest)` when that surface is in `_SURFACE_DIRS`, and `null` when it is not (R-142-06 future-surface case).
- Gate: pytest exits 1.

- [x] T-15 — GREEN: emit `surface_resolved` in main() @ai-build — DONE (real)
- Agent: build
- Files: .ai-engineering/scripts/session_bootstrap.py:966 (payload assembly)
- Principles applied: §10.5 TDD, §10.6 SDD (additive schema)
- Patch (deterministic):
  ```diff
  @@ payload = {
           "skills_total": _count_skills(root, manifest),
  +        "surface_resolved": _primary_surface(manifest) if _primary_surface(manifest) in _SURFACE_DIRS else None,
  ```
  (additive — inserted alongside existing fields; field order in JSON is not part of the contract per `schema_version: 1`.)
- Gate: T-14 test passes; schema_version stays `1`.

---

## Phase 6 — Quality loop

- [x] T-16 — verify: full test suite + integration run @ai-verify — DONE_WITH_CONCERNS (blocker: ruff format on 2 test files)
- Agent: verify
- Files: (read-only) tests/unit/scripts/test_session_bootstrap.py, tests/unit/scripts/test_minimal_manifest_parse.py, tests/unit/cli_commands/test_install_cmd_hooks_manifest.py
- Principles applied: §10.4 Verification Before Done
- Patch (deterministic): n/a — read-only.
- Gate: `uv run pytest tests/unit/scripts/ tests/unit/cli_commands/ -q` exits 0. End-to-end run: `cp` updated `session_bootstrap.py` to `/Users/soydachi/repos/test/`, run `uv run --no-project --isolated python .ai-engineering/scripts/session_bootstrap.py --format=markdown`, assert output contains `name: ai-engineering` (not `(unnamed)`), `skills, ` count > 0, and `hooks: unverified`.

- [x] T-17 — review: spec-reviewer pass @ai-review — BLOCKED (B-1 template parity drift; H-1/H-2/H-3 test rigor)
- Agent: guard (advisory)
- Files: .ai-engineering/specs/spec.md, .ai-engineering/specs/plan.md, session_bootstrap.py diff
- Principles applied: §10.7 Clean Code (final pass)
- Patch (deterministic): n/a — advisory.
- Gate: max 2 iterations of inline-fix; if reviewer flags blockers, return to relevant phase. Otherwise mark plan complete.

---

## Cross-cutting notes

- **`_count_skills` / `_count_agents` signature change.** Both functions
  gain a `manifest` parameter. The only existing caller is `main()` so
  the change is local. No mirror files reference them by signature.
- **No mirror sync needed.** Changes are to source-of-truth scripts and
  tests only. `.codex/`, `.gemini/`, `.github/`, etc. mirror trees carry
  skill SKILL.md content, not script source — those are regenerated
  separately if needed.
- **pyyaml fallback is the GATE for everything downstream.** Without
  Phase 1 done, `surfaces.enabled` cannot be read and Phase 2+ silently
  defaults to `_DEFAULT_SURFACE`. T-1 → T-3 must land first.
- **Install command is opaque from outside.** T-12 should
  intentionally NOT mock subprocess.run unless absolutely necessary —
  prefer a real `regenerate-hooks-manifest.py` invocation on a tmp
  target so the integration shape is exercised. Subprocess timeout 30 s
  caps blast radius.

## Time budget

Phase 1: ~15 min. Phase 2: ~20 min (most LOC). Phase 3: ~10 min.
Phase 4: ~20 min (cross-module). Phase 5: ~5 min. Phase 6: ~15 min.
Total: ~85 min wall-clock at single-agent dispatch. /ai-build can
parallelize Phases 1-3 (no inter-dependencies once T-3 lands).

---

## Quality Outcome

### Round 1 (initial)

Final: 2 blockers, 0 criticals, 3 highs -> STOP (escalated to operator under `/ai-build --no-hitl`)

### Blockers

1. **B-verify (deterministic)** — `uv run ruff format --check` fails on:
   - `tests/unit/cli_commands/test_install_cmd_hooks_manifest.py:24-26` (over-wrapped `REGEN_SCRIPT_SRC` assignment)
   - `tests/unit/scripts/test_session_bootstrap.py:703-705` (over-wrapped test method signature)
   - Remediation: `uv run ruff format <those-two-files>`. Mechanical.

2. **B-1 (review, compatibility, corroborated)** — Install template drift: `src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py` was NOT updated alongside the live `.ai-engineering/scripts/session_bootstrap.py`. `installer/phases/scripts.py` deploys the template verbatim on `ai-eng install`, so fresh installs ship the pre-spec-142 script. Spec goals #1–#3 (mini-parser fallback, surface-aware counts, `unverified` state) are silently undelivered for net-new projects — exactly the population spec-142 targets per spec.md:48-66.
   - Remediation: mirror the live `session_bootstrap.py` into the template path + add a parity test modeled after `tests/unit/test_hook_template_parity.py`.

### High-severity (non-blocking but should be fixed before merge)

3. **H-1 (correctness)** — `_read_manifest_minimal` `name:` regex extracts `\r` and inline `# comment` text into the returned value. Hardens on Windows checkouts. Fix: `r'^name:\s+"?([^"\r\n]+?)"?\s*(?:#.*)?$'`.
4. **H-2 (testing)** — `test_parity_with_yaml_safe_load_on_real_manifest` uses `if "name" in mini` guard, so a future schema break is silently accepted instead of being a red CI build (R-142-01 mitigation is non-load-bearing as written).
5. **H-3 (testing)** — `test_malformed_file_returns_empty_dict` assertion `assert result == {} or isinstance(result, dict)` is tautological; should be `assert result == {}`.

### Medium / low (advisory)

- M-1: `_finalize_hooks_manifest` swallows child `result.stderr` — operator loses diagnostics on failure.
- L-1, L-2, L-3: maintainability + test-symmetry concerns; not blocking.

### Recommendation

Operator re-invokes `/ai-build` (or applies fixes manually then re-invokes) after addressing B-verify and B-1 minimum. H-1/H-2/H-3 ride in the same pass.

---

### Round 2 (post-remediation)

Final: 0 blockers, 0 criticals, 0 highs -> **PASS**

Verify score: 86/100. Review verdict: CONCERNS (no blocker). Proceeding to Deliver.

#### Remediation evidence

- **B-verify** — `uv run ruff format --check` passes on all 7 spec-142 files.
- **B-1** — live `session_bootstrap.py` byte-identical to install template; new test [tests/unit/test_session_bootstrap_template_parity.py](tests/unit/test_session_bootstrap_template_parity.py) guards future drift.
- **H-1** — regex tightened to `r'^name:\s+"?([^"\r\n]+?)"?\s*(?:#.*)?$'`; new tests `test_name_strips_carriage_return`, `test_name_ignores_inline_comment` exercise CRLF + inline-comment.
- **H-2** — parity test now uses hard `assert "name" in mini`, `assert "surfaces" in mini`, `assert "enabled" in mini["surfaces"]` — R-142-01 mitigation is load-bearing.
- **H-3** — `assert result == {} or isinstance(result, dict)` → `assert result == {}, f"…"`.
- **A1** — additional inline fix: removed two `# type: ignore` lines added during T-4 build by refactoring `_load_session_bootstrap_module` (return annotation `-> types.ModuleType`, reused existing `assert spec.loader is not None`).

Test posture: **155 passed, 3 skipped** across `tests/unit/scripts/`, `tests/unit/cli_commands/`, and `tests/unit/test_session_bootstrap_template_parity.py`. Ruff check + format clean across all 7 in-scope files.

#### Residual non-blocking advisories (carried into PR body)

- **N-1** (low, regex edge case): mini-parser strips trailing `#` even inside double-quoted scalars (`name: "foo # not a comment"` → `"foo"`; yaml.safe_load → `"foo # not a comment"`). Scope is the pyyaml-uninstalled fallback path only; the real repo manifest doesn't trigger this. Deferred as documented limitation per D-142-07 (mini-parser scope is intentionally narrow).
- **M-1** (low, observability): `_finalize_hooks_manifest` discards `result.stderr` from the regen script. Dashboard `unverified` state already provides a recovery path. Optional one-line improvement deferred.
