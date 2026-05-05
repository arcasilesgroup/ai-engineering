---
id: sub-001
parent: spec-122
title: "Hygiene + Config + Delete Evals"
status: planning
files:
  # Governance / IDE overlays (D-122-01, D-122-02, D-122-33)
  - CONSTITUTION.md
  - .ai-engineering/CONSTITUTION.md
  - GEMINI.md
  - .github/copilot-instructions.md
  - AGENTS.md
  - CLAUDE.md
  - src/ai_engineering/state/control_plane.py
  - src/ai_engineering/validator/categories/file_existence.py
  - src/ai_engineering/validator/categories/manifest_coherence.py
  - src/ai_engineering/standards.py
  # Security configuration (D-122-03)
  - .semgrep.yml
  - .gitleaks.toml
  - .gitleaksignore
  # IOC catalog (D-122-04)
  - .ai-engineering/references/iocs.json
  - .ai-engineering/references/IOCS_ATTRIBUTION.md
  - .ai-engineering/scripts/hooks/prompt-injection-guard.py
  # Manifest hygiene + telemetry audit (D-122-07, D-122-39)
  - .ai-engineering/manifest.yml
  - README.md
  # Evals subsystem deletion (D-122-08)
  - .ai-engineering/evals/
  - .claude/skills/ai-eval-gate/
  - .claude/skills/ai-eval/
  - .claude/agents/ai-evaluator.md
  - .gemini/skills/ai-eval-gate/
  - .gemini/skills/ai-eval/
  - .gemini/agents/ai-evaluator.md
  - .github/skills/ai-eval-gate/
  - .github/skills/ai-eval/
  - .codex/skills/ai-eval-gate/
  - .codex/skills/ai-eval/
  - .codex/agents/ai-evaluator.md
  - src/ai_engineering/eval/
  - src/ai_engineering/templates/project/.claude/skills/ai-eval-gate/
  - src/ai_engineering/templates/project/.claude/skills/ai-eval/
  - src/ai_engineering/templates/project/.claude/agents/ai-evaluator.md
  - src/ai_engineering/templates/project/.gemini/skills/ai-eval-gate/
  - src/ai_engineering/templates/project/.gemini/skills/ai-eval/
  - src/ai_engineering/templates/project/.gemini/agents/ai-evaluator.md
  - src/ai_engineering/templates/project/.codex/skills/ai-eval-gate/
  - src/ai_engineering/templates/project/.codex/skills/ai-eval/
  - src/ai_engineering/templates/project/.codex/agents/ai-evaluator.md
  - src/ai_engineering/templates/project/.github/skills/ai-eval-gate/
  - src/ai_engineering/templates/project/.github/skills/ai-eval/
  - src/ai_engineering/verify/taxonomy.py
  - tests/unit/eval/
  - .claude/skills/ai-pr/SKILL.md
  - .claude/skills/ai-release-gate/SKILL.md
  - .gemini/skills/ai-pr/SKILL.md
  - .gemini/skills/ai-release-gate/SKILL.md
  - .github/skills/ai-pr/SKILL.md
  - .github/skills/ai-release-gate/SKILL.md
  - .codex/skills/ai-pr/SKILL.md
  - .codex/skills/ai-release-gate/SKILL.md
  - src/ai_engineering/templates/project/.claude/skills/ai-pr/SKILL.md
  - src/ai_engineering/templates/project/.claude/skills/ai-release-gate/SKILL.md
  - src/ai_engineering/templates/project/.gemini/skills/ai-pr/SKILL.md
  - src/ai_engineering/templates/project/.gemini/skills/ai-release-gate/SKILL.md
  - src/ai_engineering/templates/project/.codex/skills/ai-pr/SKILL.md
  - src/ai_engineering/templates/project/.codex/skills/ai-release-gate/SKILL.md
  # Empty runs/ directory (D-122-11)
  - .ai-engineering/runs/consolidate-2026-04-29/
  # Unused JSON schemas (D-122-12)
  - .ai-engineering/schemas/manifest.schema.json
  - .ai-engineering/schemas/skill-frontmatter.schema.json
  # Spec-117 progress relocation + scaffold cleanup (D-122-13)
  - .ai-engineering/specs/spec-117-progress/
  - .ai-engineering/state/archive/delivery-logs/spec-117/
  - .ai-engineering/specs/v2/
  - .ai-engineering/specs/handoffs/
  - .ai-engineering/specs/harness-gap-2026-05-04/
  - .ai-engineering/specs/evidence/
  # Spec-121 frontmatter migration
  - .ai-engineering/specs/spec-121-self-improvement-and-hook-completion.md
  # Wire-memory-hooks deletion (D-122-14)
  - .ai-engineering/scripts/wire-memory-hooks.py
  # Minor state/ cleanup (D-122-15)
  - .ai-engineering/state/strategic-compact.json
  - src/ai_engineering/state/context_packs.py
  - src/ai_engineering/state/control_plane.py
  - .ai-engineering/scripts/hooks/strategic-compact.py
  - src/ai_engineering/templates/project/.gemini/settings.json
  - src/ai_engineering/templates/project/.claude/settings.json
  - src/ai_engineering/templates/project/.codex/hooks.json
  - src/ai_engineering/templates/project/github_templates/hooks/hooks.json
  # History + spec ledger
  - .ai-engineering/specs/_history.md
depends_on: []
source_spec: .ai-engineering/specs/spec-122-a-hygiene-and-evals-removal.md
---

# Sub-Spec 001: Hygiene + Config + Delete Evals

## Scope

Zero-behavior-change hygiene pass over the framework: dedupe dual `CONSTITUTION.md`,
slim `GEMINI.md` + `.github/copilot-instructions.md` to delta against `AGENTS.md`,
expand `.semgrep.yml` Tier-1 with version-pinned community packs, tighten
`.gitleaks.toml`, dedupe `iocs.json`, remove `manifest.yml` orphan sections,
**delete the `evals/` subsystem entirely** (false `enforcement: blocking` signal),
drop empty `runs/` dir + unused JSON schemas, relocate `spec-117-progress/` (197 files),
fix `spec-121` non-conformant frontmatter, delete `wire-memory-hooks.py`, minor `state/`
housekeeping.

## Source

Full spec: `.ai-engineering/specs/spec-122-a-hygiene-and-evals-removal.md`.

Decisions imported: D-122-01..04, D-122-07, D-122-08, D-122-11..15, D-122-33, D-122-39.

## Exploration

### Existing Files

**Governance / IDE overlays (D-122-01, D-122-02, D-122-33):**

- `CONSTITUTION.md` (187 LOC) — authoritative root governance contract; Articles I-XII (TDD, spec-gating, ownership, observability, operating-behaviour). Sole runtime constitutional source.
- `.ai-engineering/CONSTITUTION.md` (65 LOC) — workspace-charter compatibility stub. Self-described as subordinate to root and "not loaded at Step 0". Already non-authoritative.
- `GEMINI.md` (133 LOC) — Gemini CLI overlay. ~40% duplicates AGENTS.md content (Skills(53), Source-of-Truth, Quality Gates, Observability, Hard-Rules sections all restate AGENTS.md).
- `.github/copilot-instructions.md` (60 LOC) — Copilot overlay. Subagent-Orchestration table + Quick-Reference duplicate AGENTS.md / CLAUDE.md.
- `AGENTS.md` (73 LOC) — canonical cross-IDE rulebook. Already minimal; needs no slim. May need annotations `[IDE: gemini|copilot]` for content pulled in from overlays.
- `CLAUDE.md` (217 LOC) — Claude Code overlay; 0% duplication per master spec. **Untouched** by this sub-spec.
- `src/ai_engineering/state/control_plane.py:20` — `_CONSTITUTIONAL_ALIASES = (".ai-engineering/CONSTITUTION.md",)`. Aliased path consumed by ownership/manifest contract validation. Must be reduced to `()` after stub deletion.
- `src/ai_engineering/validator/categories/file_existence.py:20-26` — `_SOURCE_REPO_CONTROL_PLANE_PATHS` lists `.ai-engineering/CONSTITUTION.md` and `src/ai_engineering/templates/.ai-engineering/CONSTITUTION.md` as expected paths; remove both entries.
- `src/ai_engineering/validator/categories/manifest_coherence.py:50-58, 196-203, 231-243` — workspace-charter validation logic; `_EXPECTED_CONTROL_PLANE.constitutional_authority.workspace_charter` and `compatibility_aliases` reference the stub. Logic must be deleted (block: lines ~55-60 and ~195-244 the workspace-charter checks).
- `src/ai_engineering/standards.py:227` — legacy-retirement family `current_surfaces=("CONSTITUTION.md", ".ai-engineering/CONSTITUTION.md")` — drop the second entry; family's status flips from PRESERVED to RETIRED with `replacement_refs=(CONSTITUTION.md,)`.

**Security configuration (D-122-03):**

- `.semgrep.yml` (138 LOC, 9 in-house rules, last update 2026-03-15) — Python-only coverage: subprocess shell, eval, path traversal, hardcoded secrets, pickle, yaml unsafe load, tempfile mktemp, requests SSRF. Missing: `extends:` for community packs, prompt-injection patterns, weak-crypto (md5/sha1/random), urllib/httpx/aiohttp SSRF, bash hooks coverage.
- `.gitleaks.toml` (20 LOC) — wildcard `\.ai-engineering/state/.*\.json$` + `.*\.ndjson$` allow patterns mask any future secret leak in checkpoint or runtime files. `useDefault = true` retains the upstream rule pack.
- `.gitleaksignore` (4 LOC) — empty fingerprint allowlist (only header comment).

**IOC catalog (D-122-04):**

- `.ai-engineering/references/iocs.json` (192 LOC, schema_version 1.0) — duplicates `suspicious_network ≡ malicious_domains` (full payload, ~38 LOC) and `dangerous_commands ≡ shell_patterns` (full payload, ~16 LOC). Total payload duplication ~54 LOC; loaded by `prompt-injection-guard.py` via `_IOC_CATEGORIES` (canonical names only).
- `.ai-engineering/references/IOCS_ATTRIBUTION.md` (56 LOC) — already documents the alias contract (lines 32-41); needs no body changes, only `last_updated` reference and (optional) note about `spec107_aliases:` map mechanism.
- `.ai-engineering/scripts/hooks/prompt-injection-guard.py:159-163, 388-424` — already aware of alias contract; consumes canonical keys (`malicious_domains`, `shell_patterns`) directly. Switch to `spec107_aliases:` pointer requires `_load_iocs()` to read the pointer map first, then dereference.

**Manifest hygiene + telemetry audit (D-122-07, D-122-39):**

- `.ai-engineering/manifest.yml` (458 LOC). Orphan sections to delete:
  - `artifact_feeds:` (line 24, no live consumer)
  - `cicd:` (lines 136-137, `standards_url: null` placeholder)
  - `contexts.precedence:` (lines 142-143, no runtime resolver)
  - `tooling:` (line 334, `[uv, ruff, gitleaks, pytest, ty, pip-audit]` — superset already in `required_tools.baseline` + `required_tools.python`)
  - `evaluation:` block (lines 99-116, deleted under D-122-08)
  - `control_plane.manifest_field_roles.canonical_input` entries `artifact_feeds`, `cicd`, `contexts.precedence` removed in lockstep.
  - `python_env:` section (lines 393-394) repositioned adjacent to `prereqs:` (lines 362-388) so `prereqs:` and `required_tools:` sit adjacent at end-of-file. `python_env` block moves to before `prereqs:`.
- `telemetry:` section (lines 337-339): `consent: strict-opt-in`, `default: disabled`. Audit consists of: (1) confirm value matches CONSTITUTION's privacy posture (Article XII or equivalent), (2) confirm hooks check `default == 'enabled'` before external emission, (3) confirm OTLP exporter honours consent, (4) document in CLAUDE.md / AGENTS.md / README.md before-install.
- `README.md` — top-level project README; needs telemetry posture stanza if missing.

**Evals subsystem deletion (D-122-08):**

- `.ai-engineering/evals/` — `README.md`, `baseline.json`, `.gitignore`, `scenarios/.gitkeep`, `runs/.gitkeep`. Zero scenario packs authored.
- IDE-canonical surfaces: `.claude/skills/ai-eval-gate/{SKILL.md, run.sh, _entry.py}`, `.claude/skills/ai-eval/SKILL.md`, `.claude/agents/ai-evaluator.md` (~8.4K).
- IDE mirrors (full delete): `.gemini/skills/ai-eval{,-gate}/`, `.gemini/agents/ai-evaluator.md`, `.github/skills/ai-eval{,-gate}/`, `.codex/skills/ai-eval{,-gate}/`, `.codex/agents/ai-evaluator.md`.
- Templates (delete): same paths under `src/ai_engineering/templates/project/.{claude,gemini,codex,github}/`.
- `src/ai_engineering/eval/` (8 modules: `__init__.py`, `gate.py` 8.9K, `pass_at_k.py`, `regression.py`, `replay.py`, `runner.py`, `scorecard.py`, `thresholds.py`). All public exports listed in `__init__.py:33-47`.
- `src/ai_engineering/verify/taxonomy.py:414` — `provenanceRefs=(".github/skills/ai-eval/SKILL.md",)`. Reference to be removed (or taxonomy entry rewritten to drop the eval node entirely).
- `tests/unit/eval/` — 7 active tests + 1 conftest + 2 helpers. Delete entire directory.
- `tests/unit/test_skill_line_budget_post_cleanup.py` — references `ai-eval`/`ai-eval-gate` skills; trim entries (already-cleanup test, will fail after deletion until updated).
- `tests/unit/test_agent_schema_validation.py` — may enumerate `ai-evaluator`; verify and trim.
- `.claude/skills/ai-pr/SKILL.md:53-65` (step 9b "Eval gate") — delete the whole 9b section.
- `.claude/skills/ai-release-gate/SKILL.md:69-73` (9th dimension "Evals") — delete; phase-2 aggregate verdict logic (10) does not need re-numbering since it lives below dimension list.
- Mirror copies of `ai-pr/SKILL.md` and `ai-release-gate/SKILL.md` across `.gemini/`, `.github/`, `.codex/`, and templates.
- `manifest.yml evaluation:` block (lines 99-116) deleted in concert with the surfaces above.
- `_history.md` — append a "spec-122-a delete + re-add path" entry documenting the removal rationale + future re-add hook.

**Empty runs/ directory (D-122-11):**

- `.ai-engineering/runs/consolidate-2026-04-29/` — empty, zero greppable references; safe to remove with `rmdir`. (Note: `runs/` parent contains other dated runs; only this child is targeted.)

**Unused JSON schemas (D-122-12):**

- `.ai-engineering/schemas/manifest.schema.json` (11.1K) — zero runtime callers; Pydantic models in `manifest_coherence.py` are de-facto contract.
- `.ai-engineering/schemas/skill-frontmatter.schema.json` (2.1K) — zero references in code or docs.
- Test reference: `tests/unit/eval/test_manifest_evaluation_section.py:24` reads `manifest.schema.json` — but this test is being deleted under D-122-08, so the reference vanishes naturally.
- Surviving schemas (kept): `audit-event.schema.json`, `decision-store.schema.json`, `hooks.schema.json`, `lint-violation.schema.json`.

**Spec-117 progress relocation + scaffold cleanup (D-122-13):**

- `.ai-engineering/specs/spec-117-progress/` — 197 build/verify/explore log files. Use `git mv` to relocate to `.ai-engineering/state/archive/delivery-logs/spec-117/`.
- `.ai-engineering/specs/v2/` (contains only `adr/.gitkeep` 54 B). Delete subtree.
- `.ai-engineering/specs/handoffs/` (empty). Delete.
- `.ai-engineering/specs/harness-gap-2026-05-04/` (empty). Delete.
- `.ai-engineering/specs/evidence/` (contains `spec-116/.gitkeep` 54 B). Delete subtree.
- `.ai-engineering/specs/spec-117-progress/` references in `src/ai_engineering/standards.py:230,247,260,273,286,299` — the `LegacyRetirementFamily.parity_proofs` paths need `state/archive/delivery-logs/spec-117/` substitution **OR** updates flagged blocked-on-relocation. Cleanest fix: rewrite the 6 path strings to the new archive location.
- `tests/unit/test_validator.py:1852, 2619` write/reference `spec-117-progress/`. Both are constructive (synthesize a fixture path); update to use a synthetic non-spec dir name to avoid coupling to the deleted directory's location.

**Spec-121 frontmatter migration:**

- `.ai-engineering/specs/spec-121-self-improvement-and-hook-completion.md:1-7` — currently bold-prose form (`**Status**: approved (autonomous)` etc.). Migrate to YAML frontmatter (`---\nspec: spec-121\ntitle: ...\nstatus: approved\neffort: medium\n---`).

**Wire-memory-hooks deletion (D-122-14):**

- `.ai-engineering/scripts/wire-memory-hooks.py` (92 LOC) — spec-118 one-shot helper. Zero callers (`grep -rn wire-memory` returns only the file itself + this spec). Run `python3 .ai-engineering/scripts/wire-memory-hooks.py --check` first to confirm idempotency, then delete.

**Minor state/ cleanup (D-122-15):**

- `.ai-engineering/state/instinct-observations.ndjson.repair-backup` — **already absent** (verified via `ls`); no action needed.
- `.ai-engineering/state/spec-116-t31-audit-classification.json` — **already absent**.
- `.ai-engineering/state/spec-116-t41-audit-findings.json` — **already absent**.
- `.ai-engineering/state/gate-cache/` — **already empty** (zero files); 7-day retention policy + `ai-eng cache prune` subcommand are master-spec-defined but the cache itself is clean. Implementation of the prune subcommand is **out of sub-001 scope** (operational follow-up).
- `.ai-engineering/state/strategic-compact.json` (43 B) — **delete unconditionally** per D-122-15. Live readers: `src/ai_engineering/state/context_packs.py:46` (entry in `_EXCLUDED_RESIDUE` tuple — passive listing, no functional dependency) and `src/ai_engineering/state/control_plane.py:179` (likewise listed in residue exclusions). Also wired as a Claude/Gemini/Codex/Copilot hook entry pointing at `.ai-engineering/scripts/hooks/strategic-compact.py`. The hook script itself produces the file. Decision: delete the writer script + remove the residue-tuple entries + remove the IDE settings hook entries in both live `.claude/.gemini/.codex` config trees AND in `src/ai_engineering/templates/project/` mirrors.

### Patterns to Follow

**Pattern A — Cross-IDE mirror cleanup (mirrors-as-projection):**
The framework follows a "canonical-source + projected mirrors" pattern. `.claude/` is canonical; `.gemini/`, `.github/`, `.codex/` are generated mirrors (via `scripts/sync_command_mirrors.py`). When deleting a skill or agent, delete from canonical first, then ensure mirrors are removed in lockstep (mirror sync may not garbage-collect). For `evals/` deletion: delete `.claude/skills/ai-eval{,-gate}/` first, then run mirror sync OR explicitly `git rm -r` each mirror copy. Same applies to template-tree copies under `src/ai_engineering/templates/project/`.

**Pattern B — Manifest field deletion via `manifest_field_roles` lockstep:**
Each top-level manifest section deleted (`artifact_feeds`, `cicd`, `contexts.precedence`, `evaluation`) must also be removed from `control_plane.manifest_field_roles.canonical_input` (manifest.yml lines 159-183). The validator (`manifest_coherence.py:_EXPECTED_CONTROL_PLANE.manifest_field_roles.canonical_input`) enforces that the listed roles match the lived manifest sections, so the two must move together.

**Pattern C — Path-relocation + caller-update:**
For `spec-117-progress/` relocation, use `git mv` to preserve history. Then `grep -rln "spec-117-progress"` to find all callers; update string literals in `src/ai_engineering/standards.py` (6 paths) and test fixtures in `tests/unit/test_validator.py` to point at the new archive location. Tests should `pytest -k spec_117` to confirm.

**Pattern D — Dead-stub deletion:**
For `.ai-engineering/CONSTITUTION.md` deletion, follow the same procedure used historically for legacy CONSTITUTION migrations: (1) confirm zero functional readers (already true — file is self-described as compatibility-only); (2) update `_CONSTITUTIONAL_ALIASES` to `()`; (3) update `file_existence.py` source-repo path list; (4) update `manifest_coherence.py` workspace-charter expectation block; (5) update `standards.py` legacy-retirement family; (6) update `_EXPECTED_CONTROL_PLANE` manifest payload; (7) `git rm` the file; (8) run `pytest tests/unit/test_validator.py -x` and `ai-eng doctor` to confirm clean.

**Pattern E — Spec frontmatter migration:**
Existing canonical specs (e.g., spec-122-a, spec-118, spec-119, spec-120) all use the YAML schema:
```yaml
---
spec: spec-NNN
title: <title>
status: approved
effort: medium|large
---
```
spec-121 uses bold-prose; rewrite the first 7 lines to match. Any in-spec references to `**Status**`/`**Branch**` body lines stay (they are body, not frontmatter), only the head block is migrated.

### Dependencies Map

**This sub-spec exports** (consumed by sub-002/003/004):
- Cleaned `.semgrep.yml` (sub-002, 003, 004 each commit-push under expanded rules)
- Cleaned `.gitleaks.toml` (same)
- Single canonical `CONSTITUTION.md` (master path used by every later sub-spec)
- Slimmed `GEMINI.md` and `.github/copilot-instructions.md` (sub-002 et al. read consistent IDE overlays)
- Deduped `iocs.json` + IOCS_ATTRIBUTION.md (sub-002+ continue using the alias contract via prompt-injection-guard.py)
- Cleaned `manifest.yml` (no `evaluation:`, no orphans) — sub-002 (Engram + state.db) and sub-003 (OPA) both edit `manifest.yml`; this sub-spec's edits land first to avoid merge conflicts
- Relocated archive at `.ai-engineering/state/archive/delivery-logs/spec-117/` (informational; no downstream code consumer)

**This sub-spec imports** (depends on no earlier sub-spec):
- None. Sub-001 is the entry point of the dependency DAG (A → B/C parallel → D).

**External dependencies (already present):**
- `git` (mv operations for relocation)
- `python3` (idempotency check on `wire-memory-hooks.py --check`)
- `semgrep ≥ 1.x` (validation of expanded `.semgrep.yml` syntax)
- `gitleaks 8.x` (validation of tightened `.gitleaks.toml` allowlist; user memory confirms `gitleaks protect --staged` is the correct command)
- `ruff` + `pytest` (test suite + lint after edits)

**Internal callers of touched code:**
- `prompt-injection-guard.py` reads `iocs.json` at every PreToolUse hook invocation (Bash/Write/Edit/MultiEdit) — alias-map refactor must not regress IOC detection.
- `manifest_coherence.py` and `file_existence.py` validators run on every `ai-eng spec verify`, `ai-eng doctor`, and CI `ai-eng validate` invocation — control-plane authority shape changes must keep these green.
- `standards.py` `LegacyRetirementFamily` validation runs at framework boot — path-string changes must be syntactically valid Python.
- `context_packs.py` and `control_plane.py` `_EXCLUDED_RESIDUE` tuple entries — `strategic-compact.json` removal is just tuple-element deletion, not a behavioural change.

### Risks

- **Eval-system test footprint mid-deletion**: 7 eval tests live under `tests/unit/eval/`. Deleting them mid-edit risks an intermediate `pytest` failure window if the surviving tests reference helpers (`conftest.py`, `__init__.py`). Mitigation: delete the entire `tests/unit/eval/` directory in one commit; verify `pytest --collect-only` lists no orphaned test references.
- **Mirror staleness after delete**: deleting `.claude/skills/ai-eval{,-gate}/` without re-running mirror sync can leave `.gemini/.github/.codex/` mirrors holding stale copies. Mitigation: explicitly delete each mirror in the same commit as the canonical, AND run `python3 scripts/sync_command_mirrors.py --check` (or equivalent diff verification) before push.
- **`evaluation:` removal breaking unknown reflective consumer**: even though greppable consumers all live in eval surfaces being deleted, an unknown reflective YAML reader could index into `evaluation:`. Mitigation: full `pytest` + `ai-eng doctor` + `ai-eng audit index` smoke after deletion; if any failure surfaces a hidden consumer, restore section + document the consumer.
- **`spec-117-progress/` relocation breaks 6 path-literal callers in `standards.py`**: each path is a string literal in a `LegacyRetirementFamily.parity_proofs` tuple. A typo during rewrite produces a runtime KeyError or validation failure. Mitigation: scripted rewrite (`sed -i 's|specs/spec-117-progress|state/archive/delivery-logs/spec-117|g' src/ai_engineering/standards.py`), then `python -c "import ai_engineering.standards"` to confirm parses, then `pytest tests/unit/test_validator.py -k legacy_retirement -x`.
- **Strategic-compact hook deletion side-effects**: `strategic-compact.py` is wired into 4 IDEs' settings.json/hooks.json AND has copies under `src/ai_engineering/templates/project/`. Failing to delete in lockstep can leave a hook reference pointing at a missing script — soft failure (hook entries that fail-open) but produces noise. Mitigation: enumerate every `strategic-compact` reference (`grep -rn strategic-compact .claude .gemini .codex .github src/ai_engineering/templates`) before delete, remove each entry, and re-run `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` to pin the new manifest.
- **`semgrep` community-pack version pinning**: `extends:` to `p/python@<version>` may fail in air-gapped CI (no internet). Master-spec mitigation is to cache packs under `.semgrep_rules_cache/`. This sub-spec **defers cache materialization** if the framework's CI has internet access (the repo currently does); if pinning + cache become a blocker, fall back to unpinned `extends:` with a documented CI bound — flag for user input only if that fallback fails.
- **`gitleaks` allowlist tightening regressions**: removing `\.ai-engineering/state/.*\.json$` may newly flag legitimate state JSON files (e.g., `decision-store.json` describing past CVE accepts). Mitigation: enumerate specific safe paths (`.ai-engineering/state/decision-store.json`, `.ai-engineering/state/ownership-map.json`, `.ai-engineering/state/install-state.json`, `.ai-engineering/state/hooks-manifest.json`, `.ai-engineering/state/framework-capabilities.json`, `.ai-engineering/state/gate-findings.json`, `.ai-engineering/state/runtime/checkpoint.json`, `.ai-engineering/state/runtime/skills-index.json`) and add each as a discrete allowlist path. Run `gitleaks protect --staged` against a synthetic-secret stage to confirm no regression on the typical hot path.
- **Workspace-charter validator block deletion**: `manifest_coherence.py` may have ~50+ LOC of workspace-charter validation that returns to a no-op once the stub is gone. Care needed to delete the whole block (and the test fixtures referencing it) atomically.

## Acceptance

See source spec section "Acceptance Criteria". Summary:
- `wc -l GEMINI.md` ≤ 50; `wc -l .github/copilot-instructions.md` ≤ 30
- `find .ai-engineering/CONSTITUTION.md` → empty
- `find .ai-engineering/evals -type f` → empty
- `find .ai-engineering/specs/spec-117-progress` → empty; relocated to archive (197 files)
- `head -5 spec-121-*.md` shows YAML frontmatter
- `ai-eng spec verify --all` passes
- `semgrep --config .semgrep.yml src/ scripts/` clean
- `gitleaks protect --staged` clean
- Full test suite + `ai-eng doctor` clean
