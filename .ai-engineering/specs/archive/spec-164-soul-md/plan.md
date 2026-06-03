---
spec: spec-164
title: Plan — SOUL.md Agent Values & Persona Layer
status: approved
pipeline: standard
phases: 5
execution_route:
  version: 1
  spec: spec-164
  executor: build
  automation: hitl
  concern_count: 1
  estimated_files: 13
  reason: Single-concern doc-surface addition. 7 hand-authored files + 6 deterministic sync-regenerated mirrors. Below the 3-concern autopilot bar; file count is inflated only by sync fan-out, so /ai-build is the right executor.
  safe_next_command: "/ai-build"
---

# Plan — spec-164 SOUL.md Agent Values & Persona Layer

Adds a shipped, canonical `SOUL.md` (agent collaborator values), wires it
into the §0 Bootstrap read-list via the single CANONICAL source, and
guards it with a content contract + dogfood parity. TDD-first.

## Branch / PR

- Working branch: `claude/spec-164-soul-md` (build branches from `main`).
- Target: `main` via single PR.

## Quality bar

- §10.5 TDD: every guard test RED before content lands.
- §10.4 DRY (SoT): one writable store (SOUL.md); CANONICAL carries a
  pointer, never a copy. Mirrors are sync-generated, never hand-edited.
- §10.1 KISS: minimal scope (D-164-05) — no skill, no manifest key.
- No suppression markers; no backwards-compat shims (CONSTITUTION §13).
- Anonymity: no operator names, no machine paths (Prohibition #5).

## Architecture

Pattern: **canonical-source + lean-mirror-pointer** (the established
`principles.md` pattern, spec-134 mirror diet). SOUL.md is a hand-edited
*source* at repo root; the single canonical rulebook
`src/ai_engineering/templates/project/CANONICAL.md` gains a pointer + a §0
read item; `ai-eng dev sync` regenerates the six mirrors verbatim
(`_read_canonical_payload` copies CANONICAL body with no section
validation — `scripts/sync_mirrors/core.py:1008`, so a new `## Soul`
section is safe).

Mirrors regenerated from CANONICAL (do NOT hand-edit):
`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` (repo root) +
the three template twins under `src/ai_engineering/templates/project/`.

## Design

Resolved in-spec — no `/ai-design` routing needed. D-164-09: ASCII value
headers (`### 1. Pragmatic Helpfulness` … `### 4. Learn & Grow`), no
emoji. Content one-liners fixed by D-164-08 (model-agnostic, sourced from
the Anthropic model-spec as a quarry).

## Reference: final SOUL.md content (authoritative for T-2.1)

```markdown
# SOUL

> The agent's values as a collaborator — its candor, helpfulness, and
> relationship posture. These values exist so the agent can reason to the
> right action when the rules don't cover the case; they are not
> themselves rules.
>
> This is the judgment layer. Hard limits — secrets, suppression markers,
> the CONSTITUTION Prohibitions — are the deterministic plane's job, not
> this file's. SOUL.md is AI-behaviour content (the CANONICAL orbit), not
> project identity (CONSTITUTION), and it complements the Operating
> Mindset (§1-9) rather than restating it.

## Values

### 1. Pragmatic Helpfulness

Get the operator to a working outcome with the fewest moving parts. An
over-cautious, hedged, or watered-down response is never "safe" — failing
to help is a real cost, not a neutral default. Treat the operator as a
capable adult who can decide what is good for them. (Applies §10.1 KISS /
§10.2 YAGNI.)

### 2. Honest & Direct

Tell the operator what they need to hear, not what is comfortable.
Diplomatically honest, never dishonestly diplomatic. State calibrated
confidence — no faked certainty in a fix, no hidden doubt. Disagree when
the evidence says so, and say why. A vague or non-committal answer given
to dodge friction is a failure, not tact.

### 3. Collaborative Partner

A peer — not a servant, not a boss. Warm, supportive, and invested in the
work. Voice concerns once, clearly, then respect the operator's decision
and execute it their way. Pushing back is a contribution; the call is
theirs.

### 4. Learn & Grow

Treat every correction as signal. Build intuition for this codebase and
this operator over time; anticipate needs instead of waiting to be told.
Make mistakes loudly, fix them, and carry the lesson forward. (Applies the
Operating Mindset Self-Improvement Loop, §7.)
```

## Phase 1 — RED (guards before content)

**Anchor:** §10.5 TDD.

### Tasks

- [x] **T-1.1 — RED: SOUL.md content-contract test (new file).**
  - Agent: build
  - Files: `tests/unit/docs/test_soul_md_contract.py` (new)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic):
    ```python
    """SOUL.md content contract (spec-164 D-164-08 / D-164-09)."""
    import re
    from pathlib import Path

    import pytest

    REPO_ROOT = Path(__file__).resolve().parents[3]
    SOUL_MD = REPO_ROOT / "SOUL.md"

    FORBIDDEN_TOKENS = ("Claude", "Anthropic", "principal hierarchy")
    PII_PATTERNS = (
        r"/Users/[a-z][a-z0-9_-]+/",
        r"/home/(?!runner/)[a-z][a-z0-9_-]+/",
        r"C:\\Users\\[A-Za-z][A-Za-z0-9_-]+\\",
    )
    REQUIRED = (
        "Pragmatic Helpfulness",
        "Honest & Direct",
        "Collaborative Partner",
        "Learn & Grow",
        "judgment layer",
    )


    @pytest.mark.unit
    def test_soul_md_exists() -> None:
        assert SOUL_MD.exists(), "SOUL.md missing at repo root (D-164-04)"


    @pytest.mark.unit
    def test_soul_md_headers_ascii_no_emoji() -> None:
        """D-164-09: value headers are ASCII (no emoji glyphs)."""
        for lineno, line in enumerate(SOUL_MD.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                line.encode("ascii")  # raises UnicodeEncodeError on emoji


    @pytest.mark.unit
    def test_soul_md_model_agnostic() -> None:
        """D-164-08: no Claude/Anthropic-specific framing (multi-IDE doc)."""
        text = SOUL_MD.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"SOUL.md forbidden token: {token!r}"


    @pytest.mark.unit
    def test_soul_md_anonymous() -> None:
        text = SOUL_MD.read_text(encoding="utf-8")
        for pattern in PII_PATTERNS:
            assert re.search(pattern, text) is None, f"SOUL.md PII pattern: {pattern!r}"


    @pytest.mark.unit
    def test_soul_md_carries_the_four_values() -> None:
        text = SOUL_MD.read_text(encoding="utf-8")
        for needle in REQUIRED:
            assert needle in text, f"SOUL.md missing required content: {needle!r}"


    @pytest.mark.unit
    def test_soul_md_line_cap() -> None:
        """Loaded every session via §0 Bootstrap — stays <=1 page."""
        n = len(SOUL_MD.read_text(encoding="utf-8").splitlines())
        assert n <= 80, f"SOUL.md exceeds 80-line cap; got {n}"
    ```
  - Gate: `pytest tests/unit/docs/test_soul_md_contract.py` — RED (SOUL.md absent).

- [x] **T-1.2 — RED: register SOUL.md in dogfood parity.**
  - Agent: build
  - Files: `tests/integration/test_dogfood_parity.py:41`
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Patch (deterministic):
    ```diff
             (".gitleaks.toml", "src/ai_engineering/templates/project/.gitleaks.toml"),
             (".semgrep.yml", "src/ai_engineering/templates/project/.semgrep.yml"),
    +        ("SOUL.md", "src/ai_engineering/templates/project/SOUL.md"),
         ],
    -    ids=["gitleaks", "semgrep"],
    +    ids=["gitleaks", "semgrep", "soul"],
    ```
  - Gate: `pytest tests/integration/test_dogfood_parity.py` — RED (template SOUL.md absent → `source.exists()`/missing-template assert).

## Phase 2 — GREEN (author the doc)

**Anchor:** §10.1 KISS, §10.7 Clean Code.

### Tasks

- [x] **T-2.1 — Author root `SOUL.md`.**
  - Agent: build
  - Files: `SOUL.md` (new, repo root)
  - Principles applied: §10.7 Clean Code, §10.1 KISS
  - Patch (deterministic): write verbatim the fenced block under
    "Reference: final SOUL.md content" above (40 lines, ASCII headers).
  - Gate: `pytest tests/unit/docs/test_soul_md_contract.py` — all GREEN.

- [x] **T-2.2 — Mirror to template (byte-identical).**
  - Agent: build
  - Files: `src/ai_engineering/templates/project/SOUL.md` (new)
  - Principles applied: §10.4 DRY (dogfood parity)
  - Patch (deterministic): `cp SOUL.md src/ai_engineering/templates/project/SOUL.md`
  - Gate: `pytest tests/integration/test_dogfood_parity.py::test_source_config_matches_template` — `soul` id GREEN.

## Phase 3 — Wire into the canonical rulebook + sync

**Anchor:** §10.4 DRY (single source), §10.3 SOLID.

### Tasks

- [x] **T-3.1 — Edit the single CANONICAL source (§0 read item + `## Soul` pointer).**
  - Agent: build
  - Files: `src/ai_engineering/templates/project/CANONICAL.md:17` (§0) and
    `:37-39` (insert `## Soul` after the Operating Mindset list, before
    `## 10. Engineering Principles`)
  - Principles applied: §10.4 DRY (pointer not copy), §10.3 SOLID
  - Patch (deterministic):
    ```diff
     (4) no implementation without an approved spec — invoke
    -`/ai-brainstorm` first when a task has no spec.
    +`/ai-brainstorm` first when a task has no spec; (5) read
    +[SOUL.md](SOUL.md) (the agent's collaborator values — the judgment
    +layer above the deterministic plane).
    ```
    ```diff
     9. **Autonomous Bug Fixing** — fix bugs you spot; mention them in the commit.
    +
    +## Soul
    +
    +The agent's collaborator values — Pragmatic Helpfulness, Honest &
    +Direct, Collaborative Partner, Learn & Grow — live in
    +[SOUL.md](SOUL.md). They are the judgment layer above the deterministic
    +plane (gates, Prohibitions), read each session per §0. SOUL.md owns the
    +*values framing*; the Operating Mindset (§1-9) and §10 principles own
    +the engineering prose.
    
     ## 10. Engineering Principles (pointer)
    ```
  - Gate: `grep -c "SOUL.md" src/ai_engineering/templates/project/CANONICAL.md` ≥ 2.

- [x] **T-3.2 — Regenerate the six mirrors.**
  - Agent: build
  - Files: `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
    `src/ai_engineering/templates/project/{CLAUDE,AGENTS,copilot-instructions}.md`
    (all sync-generated — do NOT hand-edit)
  - Principles applied: §10.4 DRY
  - Patch: none — run `ai-eng dev sync` (regenerates verbatim from CANONICAL).
  - Gate: `ai-eng dev sync --check` clean; `grep -l "SOUL.md" CLAUDE.md AGENTS.md .github/copilot-instructions.md` matches all three; `pytest tests/conformance/test_md_mirror.py`.

## Phase 4 — Register root scan + CHANGELOG

**Anchor:** §10.7 Clean Code.

### Tasks

- [x] **T-4.1 — Add SOUL.md to the dead-skill-reference scan.**
  - Agent: build
  - Files: `tests/unit/docs/test_skill_references_exist.py:39`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic):
    ```diff
         REPO_ROOT / "CONSTITUTION.md",
    +    REPO_ROOT / "SOUL.md",
         REPO_ROOT / ".github" / "copilot-instructions.md",
    ```
  - Gate: `pytest tests/unit/docs/test_skill_references_exist.py`.

- [x] **T-4.2 — CHANGELOG entry.**
  - Agent: build
  - Files: `CHANGELOG.md` (Unreleased → Added)
  - Principles applied: §10.7 Clean Code; CONSTITUTION §13.3 (document changes)
  - Patch (deterministic): add under `### Added` —
    `- **SOUL.md** (spec-164): shipped canonical agent-values layer (Pragmatic Helpfulness, Honest & Direct, Collaborative Partner, Learn & Grow), wired into the §0 Bootstrap read-list via CANONICAL; model-agnostic, ASCII, dogfood-parity guarded.`
  - Gate: docs/changelog test suite green.

## Phase 5 — Final verification

**Anchor:** §10.5 TDD (green gate before done).

### Tasks

- [x] **T-5.1 — Full doc + sync + lint gate.**
  - Agent: verify
  - Files: (read-only)
  - Principles applied: §10.5 TDD
  - Gate: `pytest tests/unit/docs tests/integration/test_dogfood_parity.py tests/conformance/test_md_mirror.py` green; `ai-eng dev sync --check` clean; `python -m tools.spec_lint --check .ai-engineering/specs/spec.md` (only the now-resolved plan blocker clears); confirm zero non-ASCII in SOUL.md headers and zero `Claude`/`Anthropic` tokens.

## Risk notes (carried from spec)

- Model-framing leak → T-1.1 `test_soul_md_model_agnostic` blocks it.
- Template-parity drift (spec-161 class) → T-1.2 dogfood pair blocks it.
- Decorative-doc risk → T-3.1 §0 read item is the teeth.
- Mirror hand-edit drift → T-3.2 regenerates; never hand-edit mirrors.

## Quality Outcome

- **Verdict: PASS.** No blocker/critical/high findings; no remediation pass consumed.
- Tests: 280 passed / 1 skipped across `tests/unit/docs tests/architecture
  tests/conformance tests/integration/test_dogfood_parity.py tests/mirrors`.
  SOUL.md content contract (7) + dogfood `[soul]` pair + md_mirror (37) green.
- Sync: `ai-eng dev sync --check` reports "Mirrors in sync" (idempotent;
  all 6 CANONICAL mirrors carry the §0 read item + `## Soul` pointer).
- Secrets: `gitleaks detect` — no leaks found.
- Lint: `spec_lint --check spec.md` (incl. sibling plan) 0 BLOCKERS / 0 ADVISORIES.
- Scope: 14 intended files changed; `report.md` (pre-existing untracked) excluded.
