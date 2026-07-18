---
title: "Fleet Audit — Simplify + Model-Portability — Execution Plan"
spec: spec-187
status: draft
pipeline: full
execution_route:
  version: 1
  spec: spec-187
  executor: autopilot
  automation: wave-gated
  concern_count: 5
  estimated_files: 450
  reason: "Multi-concern (audit+lints, skills rewrite, agents rewrite, docs+cross-link, portability), full-fleet (54 skills + 19 agents + 6 mirror families), >10 file changes → autopilot decomposition with per-wave gates."
  safe_next_command: "/ai-autopilot"
---

# Fleet Audit — Simplify + Model-Portability — Execution Plan

## Architecture

Single-source generation pipeline — one `.claude/` canonical source + `CANONICAL.md`; `scripts/sync_mirrors/core.py` regenerates all 6 IDE mirror families (`.codex/`, `.agents/`, `.github/`, `.opencode/`, `.cursor/`, and the `src/ai_engineering/templates/` installer twin). Every task edits canonical only; mirrors are regenerated, never hand-edited (D-187-05). Design-routing is N/A here — the deliverable is infra/docs/CLI-lint output (three skill/agent-authoring lints, canonical prose rewrites, reference/runbook reorg, and mirror regeneration); there is no user-facing UI surface, so no design-lens phase applies.

## Invariants (carry into every wave)

- Canonical-only edits, then regenerate mirrors via `scripts/sync_mirrors/core.py` (`ai-eng dev sync`); no mirror file is ever hand-edited (D-187-05).
- Shipping-aware delete gate: hard-delete only when **zero-inbound AND not-consumer-shipped AND not-surface-present**, reconfirmed at delete time (D-187-04).
- D-187-09 surface/OS preservation: all 6 IDE surfaces (Claude Code, Codex, Copilot, OpenCode, Cursor, Antigravity) and all 3 OSes (Windows/macOS/Linux) retain support; the only reductions are the two enumerated bucket-B cuts (reference triad, `ai-analyze-permissions`).
- D-187-10: the portability / structure / token-budget lints (and any new CLI output) emit pure-ASCII findings on non-tty / raw streams; glyphs only via the Rich styled path (mirrors `cli_ui.py` / `session_bootstrap.py`).
- Count/parity/OS-matrix gates are updated to the new **correct** value only — never loosened to admit an un-enumerated reduction.

## Phase W1 — Audit baseline + warn-only lints + dead-surface purge (Bucket A + enumerated Bucket B)

**Wave gate:** All three lints (portability / structure / token-budget) run warn-only green over the live corpus; `grep -r` returns 0 for `--consume`, `AIENG_MODEL_TIER`, `overrides/<stack>/debug.md`, and `deprecated: true` stubs (outside runtime/ + spec); the 5 predecessor drafts, 18 reviewer flat stubs, verifier-deterministic flat stubs, reference triad, and ai-analyze-permissions are hard-deleted with 0 dangling/orphan refs; mirrors regenerate clean from canonical (no hand-edited mirror); count-gates read the corrected 53 skills / 9 agents; full tests/unit/{config,docs} + tests/mirrors + tests/architecture + `ai-eng check` green; token-baseline snapshot committed. No surface/OS/parity gate loosened beyond the two enumerated D-187-04 cuts (D-187-09); all new lint output ASCII-safe on non-tty streams (D-187-10).

- [ ] T-1 — Capture canonical token-baseline snapshot (foundation for the >=25% D-187-02 target)
  - Agent: build
  - Files: .ai-engineering/runtime/research/spec-187-token-baseline.json (new); inputs = .claude/skills/**/SKILL.md, .claude/agents/*.md, CLAUDE.md/AGENTS.md/CONSTITUTION.md, .ai-engineering/reference/*.md
  - Principles applied: §10.6 SDD, §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: A committed baseline artifact records per-file + total token counts (tiktoken) over the CANONICAL surface only (54 .claude/skills + 9 .claude/agents + top-level rulebook + .ai-engineering/reference). Note BOTH candidate tools in the artifact header (external `token-baseline` CLI vs a thin in-repo tiktoken counter) and mark the final choice as deferred to the Open Question; W1 just needs a reproducible number. Re-running the counter prints the same total.

- [ ] T-2 — RED: failing test for the portability lint (no un-gated Claude-only tool literal in canonical prose) [TDD:RED]
  - Agent: build
  - Files: tests/unit/skill_lint/test_portability.py (new); target module tools/skill_lint/checks/portability.py
  - Principles applied: §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: New test imports `from skill_lint.checks.portability import check_portability`, asserts it returns findings for a fixture skill body containing a bare Claude tool literal / ungated `/ai-*` dispatch, and asserts an empty-findings result for a neutral fixture. Test FAILS (ModuleNotFoundError) — RED confirmed. Assert lint output is pure ASCII on a non-tty stream (D-187-10).

- [ ] T-3 — GREEN: portability lint module, warn-only, wired into the skill_lint CLI (ASCII-safe) [TDD:GREEN]
  - Agent: build
  - Files: tools/skill_lint/checks/portability.py (new), tools/skill_lint/cli.py:26-32 (import+register alongside existing checks)
  - Principles applied: §10.5 TDD, §10.1 KISS, §10.7 Clean Code
  - Note: judgment task (no deterministic patch).
  - Gate: `check_portability` flags un-gated Claude-only tool literals in canonical `.claude/skills`/`.claude/agents` prose; registered advisory-grade (warn-only, non-blocking exit) in cli.py next to check_naming/check_principles. Emits pure-ASCII findings on non-tty/raw streams, Rich glyphs only on the styled path (D-187-10, mirror cli_ui.py posture). test_portability.py GREEN.

- [ ] T-4 — RED: failing test for the structure/procedure lint (Workflow prose-ratio + body<500 + refs one-level) [TDD:RED]
  - Agent: build
  - Files: tests/unit/skill_lint/test_structure.py (new); target tools/skill_lint/checks/structure.py
  - Principles applied: §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: New test imports `check_structure`, asserts findings for a fixture with a >500-line body / free-prose Workflow / two-level ref, and clean result for a numbered-procedure fixture. FAILS (module missing) — RED. Assert ASCII-only output (D-187-10).

- [ ] T-5 — GREEN: structure/procedure lint module, warn-only, CLI-wired (ASCII-safe) [TDD:GREEN]
  - Agent: build
  - Files: tools/skill_lint/checks/structure.py (new), tools/skill_lint/cli.py:26-32
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Note: judgment task (no deterministic patch).
  - Gate: `check_structure` scores `## Workflow` procedure-ratio (numbered/checklist/table vs prose), flags body>500 lines and refs deeper than one level; registered warn-only. ASCII-safe non-tty output. test_structure.py GREEN.

- [ ] T-6 — RED: failing test for the token-budget lint (description<=1024 chars, name<=64/no reserved words) [TDD:RED]
  - Agent: build
  - Files: tests/unit/skill_lint/test_token_budget.py (new); target tools/skill_lint/checks/token_budget.py
  - Principles applied: §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: New test imports `check_token_budget`, asserts a finding for a fixture description >1024 chars and a name containing `claude`/`anthropic`, clean for a compliant fixture. FAILS (module missing) — RED. Assert ASCII-only output.

- [ ] T-7 — GREEN: token-budget lint module, warn-only, CLI-wired (ASCII-safe) [TDD:GREEN]
  - Agent: build
  - Files: tools/skill_lint/checks/token_budget.py (new), tools/skill_lint/cli.py:26-32
  - Principles applied: §10.5 TDD, §10.2 YAGNI
  - Note: judgment task (no deterministic patch).
  - Gate: `check_token_budget` counts description chars (cap 1024), name length (cap 64), and reserved-word presence across all canonical skills/agents; warn-only registration; ASCII-safe non-tty output (D-187-10). test_token_budget.py GREEN. All three lints run green in warn mode over the live corpus.

- [ ] T-8 — Hard-delete the 5 predecessor drafts (Bucket A, zero-inbound + not-shipped + not-surface-present)
  - Agent: build
  - Files: .ai-engineering/specs/drafts/skills-agents-excellence-v2-brief.md, .ai-engineering/specs/drafts/skills-agents-excellence-refactor.md, .ai-engineering/specs/drafts/prune-contexts-docs-research-evals-brief.md, .ai-engineering/specs/drafts/less-is-more-quality-engine-brief.md, .ai-engineering/specs/drafts/framework-simplification-less-is-more-brief.md
  - Principles applied: §10.1 KISS, §10.2 YAGNI
  - Note: judgment task (no deterministic patch).
  - Gate: `git rm` exactly these 5 draft files (NOT skills-agents-excellence-phase-c.md, which is out of scope). Drafts are un-referenced, un-shipped, non-surface; no test or manifest points at them. `ls .ai-engineering/specs/drafts/` shows all 5 gone; repo greps for their basenames return 0 (outside runtime/ and this spec).

- [ ] T-9 — Purge dead --consume flag in canonical ai-spec-draft (mechanical, canonical-only)
  - Agent: build
  - Files: .claude/skills/ai-spec-draft/SKILL.md:35,90
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    --- a/.claude/skills/ai-spec-draft/SKILL.md
    +++ b/.claude/skills/ai-spec-draft/SKILL.md
    @@
    -5. **Emit handoff token.** Print the relative file path plus the command `/ai-brainstorm --consume <topic>-brief.md` so the operator can advance to the spec phase with a single invocation.
    +5. **Emit handoff token.** Print the relative file path plus the command `/ai-brainstorm` so the operator can advance to the spec phase; brainstorm reads the drafted brief as its problem statement.
    @@
    -| Hand off to spec | `/ai-brainstorm --consume <topic>-brief.md` |
    +| Hand off to spec | `/ai-brainstorm` |
    ```
  - Gate: Canonical edit only (mirrors regenerated later). `--consume` is fictional: ai-brainstorm's only flag is `--consolidate-spec` (a spec-slot verb, NOT brief ingestion), so the flag is dropped, not aliased. `grep -n consume .claude/skills/ai-spec-draft/SKILL.md` returns 0.

- [ ] T-10 — Purge dead overrides/<stack>/debug.md + AIENG_MODEL_TIER prose in canonical (judgment)
  - Agent: build
  - Files: .claude/skills/ai-debug/SKILL.md:108-117, .claude/skills/ai-build/SKILL.md:32
  - Principles applied: §10.4 DRY, §10.7 Clean Code
  - Note: judgment task (no deterministic patch).
  - Gate: Canonical-only. In ai-debug remove the entire fictional `## Stack-specific guidance` block (overrides/<stack>/debug.md never existed — spec-135 hard-deleted it), keeping a neutral one-line 'run `ai-eng doctor --fix`' hint if useful. In ai-build:32 strike the clause `Pass the resolved tier to the build agent via env var \`AIENG_MODEL_TIER\`.` (0 Python readers) while preserving the tier-decision emit_agent_dispatched logging. `grep -rn 'overrides/<stack>/debug.md\|AIENG_MODEL_TIER' .claude` returns 0.

- [ ] T-11 — Delete the 6 reviewer-* flat forwarder stubs per surface + stop regenerating them (Bucket A)
  - Agent: build
  - Files: .codex/agents/reviewer-{compatibility,correctness,frontend,performance,security,testing}.md, .github/agents/reviewer-*.md (6), src/ai_engineering/templates/project/.codex/agents/reviewer-*.md (6), scripts/sync_mirrors/core.py:2252-2270 (_is_legacy_alias)
  - Principles applied: §10.1 KISS, §10.4 DRY
  - Note: judgment task (no deterministic patch).
  - Gate: These flat stubs carry `deprecated: true` (CLAUDE.md §13.3 self-violation) and are NOT canonical (canonical reviewer-* live at .claude/agents/*.md and stay). `git rm` all 18 committed reviewer flat stubs, then narrow/remove the `_is_legacy_alias` exemption in core.py so a re-sync orphan-deletes them instead of preserving them (drop the `reviewer-`/`review-` prefixes; verifier handled in the Bucket-B task). Regeneration (later task) leaves them gone. `grep -rl 'deprecated: true' .codex/agents .github/agents` returns only the verifier stubs pending Bucket B.

- [ ] T-12 — Bucket B step 1: retarget ai-verify refs + translate_refs to internal/verifier-deterministic.md (canonical)
  - Agent: build
  - Files: .claude/agents/ai-verify.md:23, .claude/skills/ai-verify/SKILL.md:48,124, .claude/skills/ai-verify/handlers/verify.md:15,33,37, scripts/sync_mirrors/core.py:461 (translate_refs)
  - Principles applied: §10.6 SDD, §10.7 Clean Code
  - Note: judgment task (no deterministic patch).
  - Gate: MUST run BEFORE deleting any verifier flat stub (D-187-04). Repoint every canonical ai-verify reference from `verifier-deterministic.md` / `.claude/agents/verifier-deterministic.md` to the `internal/verifier-deterministic.md` path, and confirm `translate_refs` maps that path correctly per surface so regeneration yields no dangling ref. tests/unit/test_sync_mirrors.py + tests/integration/test_shared_handler_mirror.py stay green.

- [ ] T-13 — Bucket B step 2: delete verifier-deterministic flat stubs + update naming/roster tests
  - Agent: build
  - Files: .codex/agents/verifier-deterministic.md, .github/agents/verifier-deterministic.md, src/ai_engineering/templates/project/.codex/agents/verifier-deterministic.md, scripts/sync_mirrors/core.py (_is_legacy_alias verifier prefix), tests/architecture/test_naming_clarity.py:71, tests/architecture/test_verifier_roster_count.py:54
  - Principles applied: §10.1 KISS
  - Note: judgment task (no deterministic patch).
  - Gate: Only after step 1. `git rm` the flat verifier-deterministic stubs (the internal/ copies and canonical .claude/agents/verifier-deterministic.md stay — verifier-deterministic.md at .claude/agents is the real agent, referenced via internal path now). Remove the `verifier-`/`verify-` exemption from _is_legacy_alias. Update test_naming_clarity.py:71 and confirm test_verifier_roster_count.py:54 (==2) still holds. `grep -rl 'deprecated: true' .codex .github src/ai_engineering/templates` returns 0.

- [ ] T-14 — Bucket B: delete the reference triad + its installer-contract test + fix test_phases assertion
  - Agent: build
  - Files: .ai-engineering/reference/{engineering-standards,harness-adoption,harness-engineering}.md, src/ai_engineering/templates/.ai-engineering/reference/{engineering-standards,harness-adoption,harness-engineering}.md, tests/unit/test_engineering_standards.py, tests/unit/installer/test_phases.py:175
  - Principles applied: §10.2 YAGNI, §10.1 KISS
  - Note: judgment task (no deterministic patch).
  - Gate: Enumerated live cut (D-187-04 bucket B). `git rm` all 6 triad files (canonical + template) and `git rm tests/unit/test_engineering_standards.py`. In test_phases.py delete the line `assert (ai_dir / "reference" / "engineering-standards.md").is_file()` (currently :175) — keep the principles.md assertion. Grep for the three basenames returns 0 outside CHANGELOG/spec/drafts.

- [ ] T-15 — Bucket B: delete ai-analyze-permissions across all install surfaces + guard tests + Python registrations
  - Agent: build
  - Files: .claude/skills/ai-analyze-permissions/ (dir), .opencode/commands/ai-analyze-permissions.md, src/ai_engineering/templates/project/{.claude,.codex,.opencode,.agents,.cursor}/skills/ai-analyze-permissions/, src/ai_engineering/templates/project/.opencode/commands/ai-analyze-permissions.md, src/ai_engineering/state/capabilities.py, src/ai_engineering/config/framework_defaults.py, src/ai_engineering/validator/_shared.py, tests/unit/test_capabilities.py:34,62,131, tests/unit/skill_lint/test_effort.py:223-243, tests/conformance/test_skills_rubric.py:95, tests/mirrors/test_count_parity.py:44
  - Principles applied: §10.2 YAGNI, §10.1 KISS
  - Note: judgment task (no deterministic patch).
  - Gate: Enumerated live cut (D-187-04 bucket B). `git rm` the canonical skill dir (mirrors orphan-cleaned on regen) + all template/mirror copies + the opencode command. Remove ai-analyze-permissions from capabilities.py/framework_defaults.py/_shared.py registrations and drop the github-skip allowlist entry at test_count_parity.py:44 and the effort/rubric exclusions. Skill count drops 54->53 (handled in the count-gate task). `grep -rl analyze-permissions .` returns 0 outside runtime/ and this spec.

- [ ] T-16 — Update every count-gate to the NEW correct value (53 skills) — never loosen a surface/OS/parity gate
  - Agent: build
  - Files: tests/unit/config/test_manifest.py:331, tests/unit/docs/test_inventory_count_consistency.py:21,38, README.md:23,29,58,81, .ai-engineering/README.md:12,56, src/ai_engineering/templates/.ai-engineering/README.md
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Note: judgment task (no deterministic patch).
  - Gate: Sole skill-count change this wave is ai-analyze-permissions (54->53); agents stay 9 (reviewer/verifier stubs are not ai-*.md and never counted). Set test_manifest.py:331 `== 53`; test_inventory_count_consistency.py:21 `== 53`, rotate the stale-guard at :38 (was `assert '53 skills' not in text`) to guard the old `54 skills`; update all README twins from `54 skills` to `53 skills` (stat line + demo/toolkit alt-text). Regenerate the capability catalog (`ai-eng dev sync`). D-187-09: values corrected to the real count, NO surface/OS/parity gate relaxed to admit an un-enumerated reduction.

- [ ] T-17 — Regenerate all mirror families from canonical via sync_mirrors (never hand-edit a mirror)
  - Agent: build
  - Files: scripts/sync_mirrors/core.py (run), .ai-engineering/state/hooks-manifest.json (re-pin if touched)
  - Principles applied: §10.4 DRY, §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: Runs LAST, after every canonical/core.py edit and Bucket A/B deletion. Execute the mirror regeneration (`ai-eng dev sync` / scripts/sync_mirrors/core.py) so all 5-6 mirror trees + templates reflect the dead-ref purges, stub removals, verifier retarget, and analyze-permissions/triad deletions. `git status` shows only regenerated derivatives; tests/mirrors/test_count_parity.py + surface-parity + hooks-manifest tests green; no orphan/dangling ref remains.

- [ ] T-18 — Advisory: confirm D-187-09 surface/OS preservation and D-187-10 ASCII-safety hold
  - Agent: guard
  - Files: tests/mirrors/test_count_parity.py, tests/architecture/*, tools/skill_lint/checks/{portability,structure,token_budget}.py
  - Principles applied: §10.7 Clean Code
  - Note: judgment task (no deterministic patch).
  - Gate: Advisory-only (never blocks). Verify all 6 IDE surfaces (Claude/Codex/Copilot/OpenCode/Cursor/Antigravity) and 3 OSes still supported — the ONLY reductions are the two enumerated bucket-B cuts (reference triad, ai-analyze-permissions); no parity/OS-matrix gate was loosened to permit an un-enumerated drop. Confirm each new lint prints pure ASCII on a simulated non-tty stream (no raw glyphs) so Windows cp1252 install-smoke cannot crash.

- [ ] T-19 — Wave-1 exit verification (read-only gate)
  - Agent: verify
  - Files: tests/unit/config, tests/unit/docs, tests/mirrors, tests/architecture, tests/unit/skill_lint, tests/unit/installer/test_phases.py
  - Principles applied: §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: Green gate: (1) 3 lints run green warn-only over the live corpus; (2) `grep -r` returns 0 for `--consume`, `AIENG_MODEL_TIER`, `overrides/<stack>/debug.md`, and `deprecated: true` stubs anywhere outside runtime/ + this spec; (3) the 5 drafts, reviewer/verifier flat stubs, reference triad, and ai-analyze-permissions are gone with 0 dangling refs; (4) full tests/unit/{config,docs} + tests/mirrors + tests/architecture + `ai-eng check` pass; (5) token-baseline artifact committed. No blocker/critical/high finding remains.

## Phase W2 — Skills rewrite (all 54 canonical .claude/skills/ai-*/SKILL.md): description contract + Examples collapse + prose→procedure, canonical-only then regenerate mirrors

**Wave gate:** Canonical skill (description+body) token footprint reduced ≥25% vs the W1 `token-baseline` snapshot (skills subset); tests/conformance/test_skills_rubric.py (with inverted rule_6), tests/conformance/test_description_budget.py, tests/conformance/test_surface_scoping_preserved.py all GREEN; W1 structure lint reports 0 warnings on .claude/skills/; `python -m scripts.sync_mirrors --check` exits 0 (mirrors regenerated clean, never hand-edited); tests/architecture/test_surface_parity.py + tests/conformance/test_md_mirror.py + tests/unit/{config,docs} + `ai-eng check` green; grep for surface-scoping clauses ("Claude Code only") shows none stripped from any surviving skill (D-187-09). All new/edited lint reason strings ASCII-only (D-187-10).

- [ ] T-20 — RED: invert rubric rule_6 to the ≤1-canonical-example contract (engine + test comment) [TDD:RED]
  - Agent: build
  - Files: tools/skill_domain/rubric.py:437-455, tests/conformance/test_skills_rubric.py:156-175
  - Principles applied: §10.5 TDD, §10.4 DRY, D-187-06, D-187-10
  - Patch (deterministic):
    ```diff
    --- a/tools/skill_domain/rubric.py
    +++ b/tools/skill_domain/rubric.py
    @@ -437,19 +437,19 @@
     def _rule_6_examples_count(skill: Skill) -> RubricResult:
    -    if skill.examples_count >= 2:
    -        return RubricResult(
    -            "rule_6_examples_count",
    -            "OK",
    -            f"{skill.examples_count} examples",
    -        )
    -    if skill.examples_count == 1:
    -        return RubricResult(
    -            "rule_6_examples_count",
    -            "MINOR",
    -            "only 1 example (need ≥2)",
    -        )
    -    # Universal §2.1 gap — visible (INFO), not penalised at M1 baseline.
    -    return RubricResult(
    -        "rule_6_examples_count",
    -        "INFO",
    -        "no ## Examples section — universal §2.1 gap",
    -    )
    +    if skill.examples_count == 1:
    +        return RubricResult(
    +            "rule_6_examples_count",
    +            "OK",
    +            "1 canonical example",
    +        )
    +    if skill.examples_count == 0:
    +        return RubricResult(
    +            "rule_6_examples_count",
    +            "INFO",
    +            "examples moved to references/ (progressive disclosure)",
    +        )
    +    # spec-187 D-187-06: 2+ examples is bloat; collapse to <=1 canonical.
    +    return RubricResult(
    +        "rule_6_examples_count",
    +        "MINOR",
    +        f"{skill.examples_count} examples - collapse to <=1 (spec-187)",
    +    )
    ```
  - Gate: After patch, `pytest tests/conformance/test_skills_rubric.py::test_rule_6_examples_count` goes RED (≈50 skills now flag MINOR for 2 examples, exceeding the ≤5 allowance) — this is the intended RED that the Examples-collapse tasks turn GREEN. Reason strings are ASCII-only (D-187-10). Do NOT loosen the ≤5 threshold.

- [ ] T-21 — RED: add deterministic description char-budget lint (≤500 chars, third-person, ≥3 triggers, keeps 'Not for') [TDD:RED]
  - Agent: verify
  - Files: tests/conformance/test_description_budget.py (new), reads .claude/skills/ai-*/SKILL.md:3
  - Principles applied: §10.5 TDD, D-187-06, D-187-10
  - Note: judgment task (no deterministic patch).
  - Gate: New test asserts every skill `description:` is ≤500 chars, first token is third-person (not 'Use ...'/imperative-you), contains ≥3 'Trigger for' phrases, and retains a negative-scoping 'Not for'/'Claude Code only' clause when the W1 baseline had one. RED now: ai-autopilot(699), ai-verify(679), ai-build(648), ai-board(633), ai-research(622), ai-skill-improve(615), ai-visual(528), ai-issue(519), ai-simplify(508), ai-design(508), ai-prose(507), ai-sprint(496) and ~8 more exceed 500. ASCII-only output.

- [ ] T-22 — RED (guard): freeze surface-scoping clause allowlist so the char-cap rewrite cannot strip non-Claude routing [TDD:RED]
  - Agent: guard
  - Files: tests/conformance/test_surface_scoping_preserved.py (new), .claude/skills/ai-analyze-permissions/SKILL.md:3
  - Principles applied: §10.5 TDD, D-187-09, D-187-10
  - Note: judgment task (no deterministic patch).
  - Gate: Test holds a frozen dict {skill_dir: required_substring} of every description carrying a surface-scoping clause (today: ai-analyze-permissions → 'Claude Code only — not available in'); asserts the substring still appears verbatim in the current description for every skill still on the surface. CRITICAL: protects cross-model routing (D-187-09) against the description-rewrite tasks. ai-analyze-permissions is scope-cut in a delete wave — if absent, it is dropped from the frozen map, never silently stripped while present.

- [ ] T-23 — GREEN: rewrite the 6 over-budget descriptions to third-person what+when trigger-triad under 500 chars [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-autopilot/SKILL.md:3, ai-verify/SKILL.md:3, ai-build/SKILL.md:3, ai-board/SKILL.md:3, ai-research/SKILL.md:3, ai-skill-improve/SKILL.md:3
  - Principles applied: §10.7 Clean Code, §10.1 KISS, D-187-06, D-187-05
  - Note: judgment task (no deterministic patch).
  - Gate: Each rewritten description ≤500 chars, third-person capability + trigger-triad (capability/trigger/user-vocab), preserves ≥3 'Trigger for' phrases and existing 'Not for … use /ai-X instead' negative-scoping. test_description_budget + test_rule_2 + test_rule_3 GREEN for these 6. Canonical edit only.

- [ ] T-24 — GREEN: trim the next-tier descriptions (480–530 chars) to the trigger-triad budget [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-visual/SKILL.md:3, ai-issue/SKILL.md:3, ai-simplify/SKILL.md:3, ai-design/SKILL.md:3, ai-prose/SKILL.md:3, ai-sprint/SKILL.md:3, ai-constitution/SKILL.md:3, ai-reliability-eval/SKILL.md:3, ai-engineering-issue/SKILL.md:3, ai-prompt-tune/SKILL.md:3, ai-marketing/SKILL.md:3, ai-code/SKILL.md:3, ai-schema/SKILL.md:3, ai-mcp-audit/SKILL.md:3
  - Principles applied: §10.7 Clean Code, §10.1 KISS, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: All listed descriptions ≤500 chars, still third-person with ≥3 triggers and negative-scoping intact; test_description_budget GREEN across the whole fleet after this + the previous task.

- [ ] T-25 — GREEN: Examples collapse — chain + ops family (keep 1 canonical example each) [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-brainstorm/SKILL.md, ai-plan/SKILL.md:96, ai-build/SKILL.md, ai-pr/SKILL.md, ai-autopilot/SKILL.md, ai-commit/SKILL.md, ai-branch-cleanup/SKILL.md, ai-board/SKILL.md, ai-issue/SKILL.md, ai-engineering-issue/SKILL.md, ai-constitution/SKILL.md, ai-docs/SKILL.md, ai-sprint/SKILL.md, ai-standup/SKILL.md
  - Principles applied: §10.4 DRY, §10.2 YAGNI, D-187-06, D-187-05
  - Note: judgment task (no deterministic patch).
  - Gate: Each `## Examples` reduced to exactly one canonical example (delete Example 2+); overflow variants moved to references/ only if capability-bearing. examples_count==1 per skill; rubric rule_6 OK. ~22→~8 lines each. Capability preserved (the retained example is the highest-signal invocation).

- [ ] T-26 — GREEN: Examples collapse — dev + quality family [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-code/SKILL.md, ai-test/SKILL.md, ai-debug/SKILL.md, ai-explain/SKILL.md, ai-explore/SKILL.md, ai-schema/SKILL.md, ai-scaffold/SKILL.md, ai-pipeline/SKILL.md, ai-resolve-conflicts/SKILL.md, ai-review/SKILL.md, ai-verify/SKILL.md, ai-security/SKILL.md, ai-simplify/SKILL.md
  - Principles applied: §10.4 DRY, §10.2 YAGNI, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: One canonical example per skill (ai-verify's 32-line block is the largest cut here); examples_count==1; rubric rule_6 OK; capability preserved.

- [ ] T-27 — GREEN: Examples collapse — governance + meta family [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-advise/SKILL.md, ai-governance/SKILL.md, ai-mcp-audit/SKILL.md, ai-reliability-eval/SKILL.md, ai-ide-audit/SKILL.md, ai-simplify-sweep/SKILL.md, ai-session-watch/SKILL.md, ai-session-watch-sweep/SKILL.md, ai-skill-improve/SKILL.md, ai-prompt-tune/SKILL.md, ai-learn/SKILL.md, ai-note/SKILL.md
  - Principles applied: §10.4 DRY, §10.2 YAGNI, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: One canonical example per skill (ai-session-watch-sweep's 24-line block cut); examples_count==1; rubric rule_6 OK; capability preserved.

- [ ] T-28 — GREEN: Examples collapse — creative + session family [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-animation/SKILL.md, ai-design/SKILL.md, ai-visual/SKILL.md, ai-media/SKILL.md, ai-slides/SKILL.md, ai-marketing/SKILL.md, ai-prose/SKILL.md, ai-video-editing/SKILL.md, ai-onboard/SKILL.md, ai-postmortem/SKILL.md, ai-start/SKILL.md, ai-support/SKILL.md, ai-research/SKILL.md, ai-spec-draft/SKILL.md
  - Principles applied: §10.4 DRY, §10.2 YAGNI, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: One canonical example per skill (ai-research 32-line, ai-design 23-line blocks cut); examples_count==1; rubric rule_6 OK across all 52 example-bearing skills → test_skills_rubric::test_rule_6_examples_count GREEN; ai-analyze-permissions excluded (delete-wave scope cut).

- [ ] T-29 — RED: skills-scoped structure/procedure gate (W1 structure lint must report 0 skill warnings) [TDD:RED]
  - Agent: verify
  - Files: tests/conformance/test_workflow_procedure.py (new), .claude/skills/ai-*/SKILL.md
  - Principles applied: §10.5 TDD, §10.7 Clean Code, D-187-06, D-187-10
  - Note: judgment task (no deterministic patch).
  - Gate: New test invokes the W1 structure lint over .claude/skills/ and asserts 0 prose-ratio warnings. RED now for the prose-heavy procedure sections in skills lacking a numbered `## Workflow` (ai-build, ai-brainstorm, ai-autopilot, ai-pr, ai-code, ai-debug, ai-test, ai-security, ai-explain, ai-design, ai-media, ai-slides) — their step content is free prose. ASCII-only output (D-187-10).

- [ ] T-30 — GREEN: convert prose procedure to numbered/checklist/table in the flagged skills [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-build/SKILL.md, ai-brainstorm/SKILL.md, ai-autopilot/SKILL.md, ai-pr/SKILL.md, ai-code/SKILL.md, ai-debug/SKILL.md, ai-test/SKILL.md, ai-security/SKILL.md, ai-explain/SKILL.md, ai-design/SKILL.md, ai-media/SKILL.md, ai-slides/SKILL.md
  - Principles applied: §10.7 Clean Code, §10.5 TDD, D-187-06, D-187-05
  - Note: judgment task (no deterministic patch).
  - Gate: Each skill's procedure section becomes numbered steps / checklists / tables (no free-prose step blocks); W1 structure lint reports 0 skill warnings → test_workflow_procedure GREEN. No capability or gate wording lost; bodies stay <500 lines (rubric rule_4). Canonical edit only.

- [ ] T-31 — Regenerate all mirror families from canonical and verify parity (never hand-edit a mirror)
  - Agent: build
  - Files: scripts/sync_mirrors/core.py (invoke sync_all), src/ai_engineering/templates/.ai-engineering/** (regenerated), .codex/ .agents/ .github/ .opencode/ .cursor/ (regenerated)
  - Principles applied: §10.4 DRY, D-187-05, D-187-09
  - Note: judgment task (no deterministic patch).
  - Gate: Run `python -m scripts.sync_mirrors` (or `ai-eng dev sync`) to regenerate every mirror from the edited `.claude/` canonical; then `python -m scripts.sync_mirrors --check` exits 0. tests/architecture/test_surface_parity.py + tests/conformance/test_md_mirror.py GREEN; hooks-manifest untouched (no hook bytes changed). No mirror edited by hand (D-187-05).

- [ ] T-32 — Verify token reduction ≥25% vs W1 baseline + full count/conformance gates green
  - Agent: verify
  - Files: W1 `token-baseline` snapshot (canonical skills subset), tests/unit/config/**, tests/unit/docs/**, tests/conformance/**
  - Principles applied: §10.5 TDD, §10.4 DRY, D-187-02, D-187-09
  - Note: judgment task (no deterministic patch).
  - Gate: Recompute canonical skill (description+body) tokens and assert ≥25% reduction vs the W1 `token-baseline` snapshot (D-187-02 target). Then `pytest tests/conformance tests/unit/config tests/unit/docs` + `ai-eng check` (7/7) all GREEN — test_rule_3 skill-count stays 52 (W2 deletes no skills, D-187-09), rule_6/rule_5/description-budget/surface-scoping/workflow-procedure all pass. 0 count-gate regressions.

## Phase W3 — Agents rewrite (19 canonical agents) + portability tool-name family-map extraction

**Wave gate:** All agent parity/count/surface tests green (tests/mirrors/test_count_parity.py, tests/architecture/test_reviewer_roster_count.py, test_verifier_roster_count.py, test_surface_counts.py, test_agent_description_contract.py, tests/unit/sync/test_surface_drift.py, tests/unit/test_sync_mirrors.py); new tests/architecture/test_agent_tool_family_map.py green; `python -m scripts.sync_mirrors --check` reports mirrors clean (0 drift, 0 orphans, no dangling ref to any deleted flat reviewer-*/verifier-deterministic stub — D-187-04/09); portability + token-budget lints (warn-only) show every agent body <500L and canonical agent token footprint reduced vs the W1 token-baseline snapshot; all lint/CLI output ASCII on non-tty (D-187-10). No agent lost from any of the 6 surfaces (D-187-09).

- [ ] T-33 — RED: add family tool-name-map coverage test (portability-map deliverable) [TDD:RED]
  - Agent: build
  - Files: tests/architecture/test_agent_tool_family_map.py:1
  - Principles applied: §10.5 TDD, §10.6 SDD, D-187-03
  - Patch (deterministic):
    ```diff
    --- /dev/null
    +++ b/tests/architecture/test_agent_tool_family_map.py
    @@
    +"""spec-187 W3 (D-187-03) — open-weight tool-name family map coverage.
    +
    +The canonical agent `tools:` frontmatter uses Claude-native tool names
    +(Read/Write/Edit/Bash/Glob/Grep/Agent). A Copilot mapping already exists
    +(`AgentMeta.copilot_tools`). This test pins a documented family-keyed
    +map covering the open-weight harnesses (Kimi/GLM/DeepSeek/Qwen/MiMo) so
    +portability neutrality cannot silently regress. Structural coverage only
    +-- no live-model runs (spec-187 Non-Goals). ASCII-safe per D-187-10.
    +"""
    +
    +from __future__ import annotations
    +
    +from scripts.sync_mirrors.core import AGENT_METADATA, FAMILY_TOOL_MAP
    +
    +OPEN_WEIGHT_FAMILIES = frozenset({"kimi", "glm", "deepseek", "qwen", "mimo"})
    +
    +
    +def _canonical_tools() -> frozenset[str]:
    +    tools: set[str] = set()
    +    for meta in AGENT_METADATA.values():
    +        tools.update(meta.claude_tools)
    +    return frozenset(tools)
    +
    +
    +def test_map_covers_open_weight_families() -> None:
    +    assert OPEN_WEIGHT_FAMILIES.issubset(FAMILY_TOOL_MAP.keys())
    +
    +
    +def test_every_canonical_tool_mapped_per_family() -> None:
    +    for family in OPEN_WEIGHT_FAMILIES:
    +        mapped = FAMILY_TOOL_MAP[family]
    +        for tool in _canonical_tools():
    +            assert tool in mapped, f"{family} missing map for {tool}"
    +            assert mapped[tool] and mapped[tool].strip()
    +
    +
    +def test_map_values_are_ascii_safe() -> None:
    +    for family, mapped in FAMILY_TOOL_MAP.items():
    +        assert family.isascii()
    +        for canonical, translated in mapped.items():
    +            assert canonical.isascii() and translated.isascii()
    ```
  - Gate: pytest tests/architecture/test_agent_tool_family_map.py fails at import (FAMILY_TOOL_MAP undefined) — RED confirmed

- [ ] T-34 — GREEN: add documented FAMILY_TOOL_MAP (Kimi/GLM/DeepSeek/Qwen/MiMo) to sync_mirrors/core.py [TDD:GREEN]
  - Agent: build
  - Files: scripts/sync_mirrors/core.py:118, scripts/sync_mirrors/core.py:335
  - Principles applied: §10.4 DRY, §10.2 YAGNI, D-187-03, D-187-08
  - Note: judgment task (no deterministic patch).
  - Gate: tests/architecture/test_agent_tool_family_map.py green; module-level FAMILY_TOOL_MAP dict maps the 7 canonical tools (Read/Write/Edit/Bash/Glob/Grep/Agent) to each open-weight family's function-calling equivalent, with a docstring citing the research map; MiMo entry annotated untested (D-187-08); no new mirror dirs written (D-187-03) — verify `git status` shows no new .kimi/.glm tree

- [ ] T-35 — Reduce reviewer-correctness.md (432L, largest agent): move 8 per-focus-area Example blocks to references/, keep numbered focus areas + red-flags inline
  - Agent: build
  - Files: .claude/agents/reviewer-correctness.md:44, .claude/agents/reviewer-correctness.md:332
  - Principles applied: §10.7 Clean Code, §10.1 KISS, D-187-05, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: reviewer-correctness.md body <500L (target ~250L); 8 `**Example:**` blocks relocated to .claude/agents/references/reviewer-correctness-examples.md (one level deep) OR collapsed to at most one canonical example inline; the 'Absorbed from reviewer-architecture/maintainability' section condensed to a checklist; canonical-only edit (no mirror touched); pytest tests/architecture/test_reviewer_roster_count.py green (reviewer-correctness still present)

- [ ] T-36 — Reduce verifier-acceptance.md (202L): collapse the 11 verification-scope items to a numbered checklist table; strip spec-140-merge meta-prose
  - Agent: build
  - Files: .claude/agents/verifier-acceptance.md:15, .claude/agents/verifier-acceptance.md:23
  - Principles applied: §10.7 Clean Code, §10.1 KISS, D-187-05, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: verifier-acceptance.md prose→procedure (numbered/checklist/tabular scope), body trimmed; canonical-only edit; pytest tests/architecture/test_verifier_roster_count.py green (verifier-acceptance still present)

- [ ] T-37 — Reduce reviewer-frontend.md (203L): merge the two Forms sections (#7 + #13 dup), tabularize review-scope, move Example Finding to references/
  - Agent: build
  - Files: .claude/agents/reviewer-frontend.md:67, .claude/agents/reviewer-frontend.md:131
  - Principles applied: §10.4 DRY, §10.7 Clean Code, D-187-05, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: reviewer-frontend.md body trimmed, duplicate Forms sections (§7 and §13) merged; Example Finding relocated to references/; canonical-only edit; pytest tests/architecture/test_reviewer_roster_count.py green

- [ ] T-38 — Apply description contract to agent frontmatter: rewrite meta-laden descriptions to third-person what+when <1024 chars, no reserved words
  - Agent: build
  - Files: .claude/agents/reviewer-frontend.md:3, .claude/agents/verifier-acceptance.md:3, .claude/agents/reviewer-correctness.md:3
  - Principles applied: §10.7 Clean Code, D-187-06, D-187-05
  - Note: judgment task (no deterministic patch).
  - Gate: Every `.claude/agents/*.md` `description:` is third-person what+when: strip provenance meta ('Absorbs...(D-127-10)', 'Merged from...(spec-140 W3)') from the description field (move to body if load-bearing); each ≤1024 chars, `name` ≤64 chars with no reserved word (anthropic/claude); AGENT_METADATA descriptions in core.py kept in sync for the 9 user-facing agents; canonical-only edits

- [ ] T-39 — Regenerate all agent mirrors from canonical via sync_mirrors
  - Agent: build
  - Files: scripts/sync_mirrors/core.py:1768, .codex/agents, .github/agents, .agents/agents
  - Principles applied: §10.4 DRY, D-187-05, D-187-09
  - Note: judgment task (no deterministic patch).
  - Gate: run `python -m scripts.sync_mirrors` (or `ai-eng dev sync`) to regenerate .codex/.github/.agents/.opencode/.cursor + src/.../templates agent trees plus references/ from canonical; NO mirror hand-edited; `python -m scripts.sync_mirrors --check` returns clean (0 drift/0 orphans); regenerated internal specialist mirrors contain no dangling ref to any W1-deleted flat stub (translate_refs resolves to internal/*)

- [ ] T-40 — VERIFY: agent parity/count/surface tests + family-map + mirror-drift all green
  - Agent: verify
  - Files: tests/mirrors/test_count_parity.py, tests/architecture/test_surface_counts.py, tests/architecture/test_agent_description_contract.py, tests/unit/sync/test_surface_drift.py, tests/unit/test_sync_mirrors.py, tests/architecture/test_agent_tool_family_map.py
  - Principles applied: §10.5 TDD, D-187-09
  - Note: judgment task (no deterministic patch).
  - Gate: pytest tests/mirrors tests/architecture tests/unit/sync/test_surface_drift.py tests/unit/test_sync_mirrors.py tests/architecture/test_agent_tool_family_map.py all green; `ai-eng check` 7/7; confirms the W1 flat-stub deletion + this wave's regen leave every surface's agent count consistent (no .codex/.github divergence)

- [ ] T-41 — GUARD: confirm D-187-09 surface/OS preservation + D-187-10 ASCII-safe output + warn-lint deltas
  - Agent: guard
  - Files: .claude/agents, scripts/sync_mirrors/core.py:118
  - Principles applied: D-187-09, D-187-10, §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: advisory: all 19 canonical agents still resolve on all 6 surfaces (no agent dropped); FAMILY_TOOL_MAP + any new CLI/lint output is pure ASCII on non-tty streams (D-187-10); portability + token-budget lints (warn-only) report agent-body reduction vs W1 baseline and zero new un-gated Claude-only tool literal in canonical agent prose; no un-enumerated surface/OS reduction (count-gates changed only to reflect enumerated W1 deletions, never loosened)

## Phase W4 — Docs + cross-link + reference/runbook reorg

**Wave gate:** All canonical edits land in `.claude/` + `src/.../templates/` then mirrors regenerate via `python scripts/sync_mirrors/core.py` (D-187-05, no hand-edited mirror); `python scripts/sync_mirrors/core.py --check` reports zero drift; new link+orphan checker green (0 broken relative-.md links, 0 orphan reference files); ai-schema ↔ ai-security reciprocal; runbook-index lists all 14 survivors and `pytest tests/unit/test_runbook_contracts.py` green; AGENTS.md portable fence populated (ASCII-only per D-187-10); `pytest tests/unit/docs tests/conformance tests/unit/test_sync_mirrors.py` + `ai-eng check` green; all 6 IDE surfaces + 3 OSes preserved (D-187-09).

- [ ] T-42 — RED: add Integration-reciprocity conformance test for the ai-schema/ai-security pair [TDD:RED]
  - Agent: verify
  - Files: tests/conformance/test_integration_reciprocity.py (new)
  - Principles applied: §10.5 TDD, D-187-06
  - Note: judgment task (no deterministic patch).
  - Gate: New test asserts .claude/skills/ai-schema/SKILL.md '## Integration' names /ai-security AND .claude/skills/ai-security/SKILL.md '## Integration' names /ai-schema. Fails RED now (ai-security:156 omits /ai-schema). Run: pytest tests/conformance/test_integration_reciprocity.py -x

- [ ] T-43 — GREEN: add reciprocal /ai-schema cross-ref to ai-security Integration (canonical edit) [TDD:GREEN]
  - Agent: build
  - Files: .claude/skills/ai-security/SKILL.md:156
  - Principles applied: §10.4 DRY, §10.5 TDD, D-187-05
  - Patch (deterministic):
    ```diff
    --- a/.claude/skills/ai-security/SKILL.md
    +++ b/.claude/skills/ai-security/SKILL.md
    @@ -156 +156 @@
    -Called by: `/ai-verify` (security mode delegation), `/ai-verify --release` (aggregates results), pre-commit hooks (gitleaks protect --staged), pre-push hooks (semgrep, pip-audit). Risk acceptances go to: `decision-store.json` via `/ai-governance risk`. See also: `/ai-governance`, `/ai-mcp-audit` (skill behavior), `/ai-pipeline` (CI security).
    +Called by: `/ai-verify` (security mode delegation), `/ai-verify --release` (aggregates results), pre-commit hooks (gitleaks protect --staged), pre-push hooks (semgrep, pip-audit). Risk acceptances go to: `decision-store.json` via `/ai-governance risk`. See also: `/ai-governance`, `/ai-mcp-audit` (skill behavior), `/ai-pipeline` (CI security), `/ai-schema` (DB schema/injection review).
    ```
  - Gate: pytest tests/conformance/test_integration_reciprocity.py green; mirror regen happens in the later regen task, not by hand-editing .codex/.github copies.

- [ ] T-44 — RED: add runbook-index completeness test (index must list exactly the 14 ALL_RUNBOOKS) [TDD:RED]
  - Agent: verify
  - Files: tests/unit/test_runbook_contracts.py
  - Principles applied: §10.5 TDD, §10.1 KISS
  - Note: judgment task (no deterministic patch).
  - Gate: Add test_runbook_index_lists_all_survivors: parse .ai-engineering/reference/runbook-index.md, assert the set of linked runbook stems == set(ALL_RUNBOOKS) (14) and no extras. Fails RED (index file does not yet exist). Run: pytest tests/unit/test_runbook_contracts.py::test_runbook_index_lists_all_survivors -x

- [ ] T-45 — GREEN: create runbook discovery index (canonical + template twin) linking all 14 survivors [TDD:GREEN]
  - Agent: build
  - Files: .ai-engineering/reference/runbook-index.md (new), src/ai_engineering/templates/.ai-engineering/reference/runbook-index.md (new)
  - Principles applied: §10.4 DRY, §10.5 TDD, D-187-04 (survivors kept), D-187-05
  - Note: judgment task (no deterministic patch).
  - Gate: Both files byte-identical; a markdown table with columns Runbook | Type | Cadence | Link, one row per top-level file in .ai-engineering/runbooks/ (triage, refine, feature-scanner, stale-issues, dependency-health, code-quality, consolidate, security-scan, docs-freshness, performance, governance-drift, architecture-drift, wiring-scanner, work-item-audit), each Link a relative [name](../runbooks/name.md). MUST NOT be placed inside runbooks/ (test_runbook_count globs runbooks/*.md == 14). ASCII-only (D-187-10). Gate: pytest tests/unit/test_runbook_contracts.py green.

- [ ] T-46 — Wire runbook-index into CANONICAL Source-of-Truth table so each runbook gains an inbound ref (canonical edit)
  - Agent: build
  - Files: src/ai_engineering/templates/project/CANONICAL.md:107
  - Principles applied: §10.4 DRY, D-187-05
  - Patch (deterministic):
    ```diff
    --- a/src/ai_engineering/templates/project/CANONICAL.md
    +++ b/src/ai_engineering/templates/project/CANONICAL.md
    @@
     | Placement contract | `.ai-engineering/reference/knowledge-placement.md` |
    +| Runbooks index | `.ai-engineering/reference/runbook-index.md` |
     | Hook scripts | `.ai-engineering/scripts/hooks/` |
    ```
  - Gate: Row added to CANONICAL.md only; CLAUDE.md/AGENTS.md/copilot rows regenerate in the regen task. Confirms runbook-index.md itself is not a new orphan. Verify in T-linkcheck + pytest tests/unit/docs/test_canonical_docs_consistency.py.

- [ ] T-47 — Fill AGENTS.md empty ide-extras fence with a portable hook/hot-path pointer (D-187-09 portability)
  - Agent: build
  - Files: scripts/sync_mirrors/core.py:1211
  - Principles applied: §10.1 KISS, D-187-09, D-187-10
  - Patch (deterministic):
    ```diff
    --- a/scripts/sync_mirrors/core.py
    +++ b/scripts/sync_mirrors/core.py
    @@
    +_AGENTS_EXTRAS = """\
    +## Hooks & Hot-Path (portable entry point)
    +
    +AGENTS.md is the engine-neutral surface. Claude Code and Copilot carry
    +their own hook wiring in their mirrors; other engines (Codex, OpenCode,
    +Cursor, Antigravity, raw-API hosts) apply the same discipline through
    +whatever lifecycle mechanism they provide:
    +
    +- Keep any pre-commit / pre-save gate under ~1s and any pre-push gate
    +  under ~5s; move the full test suite, dependency audit, and governance
    +  evaluation into CI, never the local hot path.
    +- Canonical hook scripts live under `.ai-engineering/scripts/hooks/` and
    +  are byte-pinned in `.ai-engineering/state/hooks-manifest.json`; invoke
    +  them via `run_hook_safe` (or the engine equivalent) so integrity
    +  enforcement stays intact.
    +- Slash-command idioms (`/ai-*`) and the trailing `$ARGUMENTS` token are
    +  provided by the host agent surface; on a host without a slash layer,
    +  invoke the skill body at `.claude/skills/ai-<name>/SKILL.md` directly.
    +"""
    +
    +
     def generate_agents_md(*, skill_count: int, agent_count: int) -> str:
    @@ def generate_agents_md
         payload = read_canonical_payload()
         return assemble_mirror_payload(
             payload,
    -        ide_extras="",
    +        ide_extras=_AGENTS_EXTRAS,
             skill_count=skill_count,
             agent_count=agent_count,
         )
    ```
  - Gate: Also update the generate_agents_md docstring line 'AGENTS.md is the base mirror — no IDE-extras block' to note it now carries a portable hook/hot-path pointer (fence still stripped for sha parity). All bytes ASCII (D-187-10). Gate: after regen, AGENTS.md:169-170 fence is non-empty; pytest tests/unit/test_sync_mirrors.py + tests/conformance/test_md_mirror.py green (fence stripped before sha).

- [ ] T-48 — Add in-repo link + orphan checker (0 broken relative-.md links, 0 orphan reference files) — the W4 gate
  - Agent: verify
  - Files: tests/unit/docs/test_markdown_link_targets.py (new)
  - Principles applied: §10.5 TDD, §10.1 KISS, D-187-04
  - Note: judgment task (no deterministic patch).
  - Gate: Test 1 (broken links): for each canonical .md (CLAUDE.md, AGENTS.md, README.md, CONSTITUTION.md, SOUL.md, docs/**, .ai-engineering/reference/**) extract relative [text](path.md) links (skip http/anchors), resolve against file dir, assert target exists — catches post-W1 dangling triad refs and the new runbook-index links. Test 2 (orphans): assert every .ai-engineering/reference/*.md has >=1 inbound relative link from a canonical doc (scan set above + .claude/skills/**/SKILL.md), excluding tests/specs/CHANGELOG; green only after W1 triad deletion + runbook-index wiring land. Depends on W1 (triad removed). Prefer this in-repo checker over a lychee GitHub Action (repo Actions allowlist). Run: pytest tests/unit/docs/test_markdown_link_targets.py -x

- [ ] T-49 — Regenerate all mirror families + re-pin hooks-manifest after canonical edits
  - Agent: build
  - Files: scripts/sync_mirrors/core.py, AGENTS.md, CLAUDE.md, .github/copilot-instructions.md, .codex/**, .agents/**, .opencode/**, .cursor/**
  - Principles applied: §10.4 DRY, D-187-05, D-187-09
  - Note: judgment task (no deterministic patch).
  - Gate: Run `python scripts/sync_mirrors/core.py` (regenerates AGENTS.md fence, CANONICAL-sourced CLAUDE.md/copilot rows, and ai-security Integration across every mirror), then re-pin .ai-engineering/state/hooks-manifest.json if touched. Never hand-edit a mirror. Verify: `python scripts/sync_mirrors/core.py --check` reports zero drift.

- [ ] T-50 — Wave gate: full docs/conformance/parity + count-gate + surface/OS preservation check
  - Agent: verify
  - Files: tests/unit/docs, tests/conformance, tests/unit/test_sync_mirrors.py, tests/unit/test_runbook_contracts.py
  - Principles applied: §10.5 TDD, D-187-09, D-187-10
  - Note: judgment task (no deterministic patch).
  - Gate: Run: pytest tests/unit/docs tests/conformance tests/unit/test_sync_mirrors.py tests/unit/test_runbook_contracts.py -q && ai-eng check && python scripts/sync_mirrors/core.py --check. Confirm: 0 broken links / 0 orphans, reciprocity green, runbook-index complete (14), AGENTS.md portable fence present + ASCII, no §14 pointer row references the deleted triad, all 6 surfaces + 3 OS gates unchanged (updated only for enumerated deletions — never loosened).

## Phase W5 — Portability neutrality + flip lints to blocking (DoD gate)

**Wave gate:** All three lints (portability/structure/token-budget) run BLOCKING-green in ci-check.yml; canonical token reduction ≥25% vs W1 token-baseline; grep=0 for --consume / AIENG_MODEL_TIER / overrides/<stack>/debug.md / deprecated:true anywhere in repo; D-187-09 assertion test green (all 6 IDE surfaces + Windows/macOS/Linux preserved); full tests/unit/{config,docs} + `ai-eng check` + mirror-parity + hooks-manifest all green; mirrors regenerated (never hand-edited).

- [ ] T-51 — Document $ARGUMENTS and /ai-* as harness-provided idioms + neutrality contract (canonical)
  - Agent: build
  - Files: .ai-engineering/reference/mirror-authoring.md:1, .ai-engineering/reference/surface-axioms.md:1
  - Principles applied: §10.2 YAGNI, §10.7 Clean Code, §10.6 SDD
  - Note: judgment task (no deterministic patch).
  - Gate: Canonical reference gains a short 'Portability contract' subsection declaring: (a) the trailing $ARGUMENTS token and /ai-* slash-command idioms are harness-provided (resolved by the IDE agent surface, not by canonical prose) and therefore allowlisted by the portability lint; (b) canonical skill/agent PROSE carries no un-gated Claude-only tool literal (tools: frontmatter is remapped by the W3 family map). Edit canonical only. No mirror hand-edit.

- [ ] T-52 — RED: portability-lint neutrality rule test — flags planted Claude-only tool literal, allows harness idioms [TDD:RED]
  - Agent: verify
  - Files: tests/unit/test_portability_lint_neutrality.py:1 (new), scripts/check_portability.py:1 (W1 artifact)
  - Principles applied: §10.5 TDD
  - Note: judgment task (no deterministic patch).
  - Gate: New RED test asserts the portability lint (W1) FLAGS a fixture SKILL.md whose prose says 'use the Bash tool'/'run the Read tool', and does NOT flag $ARGUMENTS or /ai-<name> idioms nor a family-gated tools: line. RED because the neutrality rule + idiom allowlist are not yet implemented. Confirm the lint module path emitted by W1 before finalizing the import.

- [ ] T-53 — GREEN: implement portability-lint neutrality rule + harness-idiom allowlist (ASCII-safe output) [TDD:GREEN]
  - Agent: build
  - Files: scripts/check_portability.py:1 (W1 artifact)
  - Principles applied: §10.5 TDD, §10.1 KISS, §10.8 Hexagonal (per D-187-10 ASCII posture)
  - Note: judgment task (no deterministic patch).
  - Gate: Portability lint (a) flags un-gated Claude-only tool literals in canonical skill/agent prose, (b) allowlists $ARGUMENTS + /ai-* harness idioms, (c) emits pure-ASCII findings on non-tty/raw streams with glyphs only via the Rich styled path (D-187-10, mirrors cli_ui.py/session_bootstrap.py). Test from prior task turns GREEN.

- [ ] T-54 — Confirm/annotate tool-name family map completeness + MiMo-untested (D-187-08)
  - Agent: build
  - Files: scripts/sync_mirrors/tool_family_map.py:1 (W3 artifact), scripts/sync_mirrors/core.py:775
  - Principles applied: §10.4 DRY, §10.2 YAGNI
  - Note: judgment task (no deterministic patch).
  - Gate: Family map (W3, per D-187-03 lives inside scripts/sync_mirrors/) documents tool-name mappings for Kimi/GLM/DeepSeek/Qwen and carries an explicit inline annotation that MiMo is declared UNTESTED (structural neutrality only, no live-behavior claim — D-187-08). Verify the map path W3 actually created; annotate there, not in a new file.

- [ ] T-55 — Test: family-map covers documented open-weight families + MiMo marked untested
  - Agent: verify
  - Files: tests/unit/config/test_tool_family_map.py:1 (new), scripts/sync_mirrors/tool_family_map.py:1
  - Principles applied: §10.5 TDD, §10.4 DRY
  - Note: judgment task (no deterministic patch).
  - Gate: Read-only test asserts the family map exports entries for Kimi, GLM, DeepSeek, Qwen and that MiMo is present but flagged untested (no live-behavior assertion). Green.

- [ ] T-56 — Regenerate all mirror families after canonical neutrality edits
  - Agent: build
  - Files: scripts/sync_mirrors/core.py:1
  - Principles applied: §10.4 DRY, §13.7 SSOT-per-datum, D-187-05
  - Note: judgment task (no deterministic patch).
  - Gate: Run scripts/sync_mirrors/core.py (via `ai-eng dev sync`) so canonical doc/prose edits from this wave propagate to .codex/.agents/.github/.opencode/.cursor + templates; regenerate hooks-manifest. `git diff` shows only generated deltas; no mirror is hand-edited.

- [ ] T-57 — Verify mirror parity + hooks-manifest + template parity green post-regeneration
  - Agent: verify
  - Files: tests/mirrors/test_count_parity.py:1, tests/unit/test_template_skill_parity.py:1, tests/unit/test_hook_template_parity.py:1
  - Principles applied: §10.5 TDD, §16 Surface Axioms
  - Note: judgment task (no deterministic patch).
  - Gate: tests/mirrors + surface/template parity + hooks-manifest tests all green — regeneration produced no drift and no dangling ref.

- [ ] T-58 — Flip all three lints (portability/structure/token-budget) warn-only → BLOCKING in CI
  - Agent: build
  - Files: .github/workflows/ci-check.yml:959, .github/workflows/ci-check.yml:996
  - Principles applied: §10.5 TDD, D-187-07
  - Note: judgment task (no deterministic patch).
  - Gate: In the ci-check.yml lint job, remove the warn-only escape (continue-on-error / `|| true` / `--warn-only` flag introduced in W1) from all three lint invocations so a violation FAILS the job. Locate the exact steps W1 added (they do not exist yet at the referenced lines) and flip them; keep ASCII-safe output. Job stays green on the current clean corpus.

- [ ] T-59 — RED/assertion: D-187-09 surface + tri-OS preservation test [TDD:RED]
  - Agent: verify
  - Files: tests/unit/test_spec_187_surface_os_preservation.py:1 (new), tests/unit/config/test_mirror_inventory.py:18
  - Principles applied: §10.5 TDD, D-187-09
  - Note: judgment task (no deterministic patch).
  - Gate: New test asserts all 6 IDE surfaces (Claude Code, Codex, Copilot, OpenCode, Cursor, Antigravity) are still generated/present in the mirror inventory AND that OS support markers cover Windows/macOS/Linux — i.e. the only reductions are the two enumerated D-187-04 bucket-B cuts, no un-enumerated surface/OS loss. Green (prior waves preserved support).

- [ ] T-60 — Acceptance: dead-token grep=0 conformance test
  - Agent: verify
  - Files: tests/unit/docs/test_spec_187_dead_tokens_absent.py:1 (new)
  - Principles applied: §10.5 TDD, §13.3 hard-delete
  - Note: judgment task (no deterministic patch).
  - Gate: Test greps the whole repo (excluding CHANGELOG history + this spec/test's own literals) and asserts 0 matches for `--consume`, `AIENG_MODEL_TIER`, `overrides/<stack>/debug.md`, and `deprecated: true`. Green only after W1 deletions landed.

- [ ] T-61 — Acceptance: ≥25% canonical token reduction vs W1 token-baseline
  - Agent: verify
  - Files: tests/unit/docs/test_spec_187_token_reduction.py:1 (new), .ai-engineering/state/token-baseline.json:1 (W1 artifact)
  - Principles applied: §10.5 TDD, D-187-02
  - Note: judgment task (no deterministic patch).
  - Gate: Test loads the W1 token-baseline snapshot, recomputes current canonical skill+agent (description+body) token footprint the same way, and asserts reduction ≥25%. Confirm the snapshot path/format W1 emitted before finalizing.

- [ ] T-62 — DoD gate: full tests/unit/{config,docs} + ai-eng check + 3 lints blocking-green
  - Agent: verify
  - Files: tests/unit/config/:1, tests/unit/docs/:1, .github/workflows/ci-check.yml:959
  - Principles applied: §10.5 TDD, §4 Verification-Before-Done
  - Note: judgment task (no deterministic patch).
  - Gate: Run full tests/unit/config + tests/unit/docs, `ai-eng check`, and all three lints in BLOCKING mode locally — every gate green. This is the composite Wave-5 DoD reassessment; any blocker STOPS per Hard Rule 5.

- [ ] T-63 — Advisory: confirm CI blocking-green + no un-enumerated surface/OS regression
  - Agent: guard
  - Files: .github/workflows/ci-check.yml:959, tests/unit/test_spec_187_surface_os_preservation.py:1
  - Principles applied: §10.5 TDD, D-187-09, D-187-10
  - Note: judgment task (no deterministic patch).
  - Gate: Advisory sweep: verify the CI lint job is actually blocking (no residual warn-escape), lint output is ASCII-safe for Windows cp1252 consoles (D-187-10), and no parity/OS/count gate was loosened to permit an un-enumerated reduction (D-187-09) — flag any drift, do not auto-fix.
