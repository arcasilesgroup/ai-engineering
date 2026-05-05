---
spec: spec-122-a
title: Framework Cleanup Phase 1-A — Hygiene + Config + Delete Evals
status: approved
effort: medium
---

# Spec 122-a — Hygiene + Config + Delete Evals

> Sub-spec of [spec-122 master](./spec-122-framework-cleanup-phase-1.md).
> Implements decisions D-122-01..04, D-122-07, D-122-08, D-122-11..15,
> D-122-33, D-122-39. **No dependencies** — this is the entry point of the
> Phase 1 dependency DAG (A → B/C parallel → D).

## Summary

Zero-behavior-change hygiene pass over the framework's source repo:
deduplicate the dual `CONSTITUTION.md` files, slim the per-IDE overlay
files (`GEMINI.md`, `.github/copilot-instructions.md`) to pure delta
against `AGENTS.md`, expand `.semgrep.yml` Tier-1 rules with version-pinned
community packs, tighten the `.gitleaks.toml` allowlist, deduplicate
`iocs.json` aliases, remove orphan `manifest.yml` sections, **delete the
`evals/` subsystem entirely** (no scenario packs were ever authored;
`enforcement: blocking` was a false signal), drop empty `runs/`
directories, drop unused JSON schemas, relocate the 197-file
`spec-117-progress/` archive, fix `spec-121` non-conformant frontmatter,
delete the one-shot `wire-memory-hooks.py` install helper, and minor
`state/` housekeeping.

This sub-spec ships **first** because every change is reversible, the
risk profile is low, and downstream sub-specs (b, c, d) reference the
cleaned configuration surfaces.

## Goals

- Single canonical `CONSTITUTION.md` at repo root; stub at
  `.ai-engineering/CONSTITUTION.md` deleted; `observability.py:161-165`
  fallback resolution removed.
- `GEMINI.md` reduced to ≤ 50 LOC delta (today 133 LOC, ~40% duplicated
  with `AGENTS.md`).
- `.github/copilot-instructions.md` reduced to ≤ 30 LOC delta (today 60
  LOC, ~30% duplicated).
- No `CODEX.md` created at repo root; Codex reads `AGENTS.md` natively
  via `.codex/config.toml` wiring.
- `.semgrep.yml` extends `p/python`, `p/bash`, `p/owasp-top-ten`,
  `p/security-audit` with version pins, plus custom prompt-injection
  rules, weak-crypto coverage, and SSRF rules for `urllib`, `httpx`,
  `aiohttp`.
- `.gitleaks.toml` allowlist tightened — `\.ai-engineering/state/.*\.json$`
  wildcard removed; specific safe paths enumerated.
- `iocs.json` aliases deduplicated (~40 LOC reduction); `last_updated`
  bumped to `2026-05`; `IOCS_ATTRIBUTION.md` documents the alias contract.
- `manifest.yml` orphan sections removed (`tooling:` flat list,
  `artifact_feeds:`, `cicd.standards_url: null`, `contexts.precedence:`).
  `prereqs:` and `required_tools:` are repositioned adjacent.
- `evals/` subsystem fully deleted: directory, `/ai-eval-gate` skill,
  `/ai-eval` skill, `ai-evaluator` agent, `manifest.yml evaluation:`
  block, `/ai-pr` step 9b, `/ai-release-gate` 9th dimension,
  `src/ai_engineering/eval/` module. Re-add path documented in
  `_history.md`.
- `runs/consolidate-2026-04-29/` empty directory deleted.
- `manifest.schema.json` and `skill-frontmatter.schema.json` deleted.
- `spec-117-progress/` (197 files) relocated to
  `state/archive/delivery-logs/spec-117/`. Empty gitkeep scaffolds
  (`v2/adr/`, `harness-gap-2026-05-04/`, `evidence/spec-116/`,
  `handoffs/`) deleted.
- `spec-121-self-improvement-and-hook-completion.md` frontmatter
  migrated from bold-prose form to canonical YAML schema.
- `wire-memory-hooks.py` deleted after `--check` confirms idempotency.
- `instinct-observations.ndjson.repair-backup` deleted; `spec-116-t31`
  and `spec-116-t41` audit JSON moved to `state/archive/spec-116/`;
  `gate-cache/` retention policy 7 days; `strategic-compact.json`
  deleted unconditionally.
- `manifest.yml telemetry:` consent posture verified (strict-opt-in,
  default disabled) and documented consistently in CLAUDE.md / AGENTS.md
  / README.md.

## Non-Goals

- Memory.db deletion or Engram delegation (sub-spec b).
- state.db unified schema (sub-spec b).
- OPA proper switch (sub-spec c).
- sync_command_mirrors.py refactor or docs/ audit (sub-spec d).
- Multi-language Tier-2 `.semgrep.yml` for consumer projects (separate
  spec, deferred).
- Re-authoring eval scenario packs (decision is to delete the gate).

## Decisions

This sub-spec **imports** the following master decisions verbatim — see
`spec-122-framework-cleanup-phase-1.md` for the full rationale:

| ID | Decision title |
|---|---|
| D-122-01 | Single CONSTITUTION at repo root, stub deleted |
| D-122-02 | AGENTS.md as cross-IDE SSOT; per-IDE files become pure delta |
| D-122-03 | `.semgrep.yml` Tier-1 expansion with version-pinned community packs |
| D-122-04 | `iocs.json` aliases deduplicated |
| D-122-07 | `manifest.yml` orphan sections removed |
| D-122-08 | `evals/` subsystem deleted |
| D-122-11 | Empty `runs/consolidate-2026-04-29/` deleted |
| D-122-12 | Unused JSON schemas deleted |
| D-122-13 | `spec-117-progress/` relocated and gitkeep scaffolds removed |
| D-122-14 | One-off install helper `wire-memory-hooks.py` deleted |
| D-122-15 | Minor `state/` cleanup |
| D-122-33 | No `CODEX.md` overlay; Codex reads `AGENTS.md` natively |
| D-122-39 | Telemetry section audit (`manifest.yml telemetry:`) |

## Acceptance Criteria

- `wc -l GEMINI.md` ≤ 50; `wc -l .github/copilot-instructions.md` ≤ 30.
- `find . -name '.ai-engineering/CONSTITUTION.md'` returns empty.
- `grep -rn '\.ai-engineering/CONSTITUTION\.md' src/ scripts/` returns
  empty (no fallback path).
- `find .ai-engineering/evals -type f` returns empty after deletion.
- `find .ai-engineering/specs/v2/adr .ai-engineering/specs/handoffs
  .ai-engineering/specs/harness-gap-2026-05-04 .ai-engineering/specs/evidence`
  returns empty.
- `find .ai-engineering/specs/spec-117-progress` returns empty;
  `find .ai-engineering/state/archive/delivery-logs/spec-117 -type f | wc -l`
  ≥ 197.
- `head -5 .ai-engineering/specs/spec-121-self-improvement-and-hook-completion.md`
  shows YAML frontmatter (`---` delimiters + `spec:`, `title:`, `status:`,
  `effort:` keys).
- `ai-eng spec verify --all` passes (all specs conform to schema).
- `semgrep --config .semgrep.yml src/ scripts/` runs cleanly with new rules.
- `gitleaks protect --staged` succeeds with tightened allowlist.
- Full test suite passes; `ai-eng doctor` returns no findings.

## Risks

- **`manifest.yml` orphan removal breaking unknown reflective consumer**:
  a greppable-zero section may still be loaded reflectively. **Mitigation**:
  remove section, run full test suite + `ai-eng doctor` + `ai-eng audit
  index` end-to-end; if anything fails, restore section + document the
  reflective reader.
- **`evals/` deletion regret**: a future regulatory inquiry may ask "show
  me your eval coverage." **Mitigation**: `_history.md` records the
  delete + re-add path; `specs/_proposed/spec-119-v2-stub.md` outlines
  acceptance criteria for re-introduction.
- **GEMINI.md / copilot-instructions.md slim-down stranding non-duplicated
  content**: a Gemini-only or Copilot-only pattern may exist that wasn't
  in AGENTS.md. **Mitigation**: line-by-line audit before deletion;
  non-duplicated content gets pulled into AGENTS.md with `[IDE: gemini |
  copilot]` annotation; behavioural smoke test invokes a known skill in
  each IDE post-merge.
- **`semgrep` version-pin causing CI breakage**: pinning to a specific
  community-pack version may fail to fetch in air-gapped CI. **Mitigation**:
  packs cached under `.semgrep_rules_cache/` and committed; refresh via
  quarterly PR documented in `.ai-engineering/contexts/`.
- **`spec-117-progress` relocation breaking historical references**:
  decision-store.json or skill bodies may reference the old path.
  **Mitigation**: full repo grep before move; symlink at old path to new
  path for one release as fallback.

## References

- doc: spec-122-framework-cleanup-phase-1.md (master)
- doc: AGENTS.md
- doc: CLAUDE.md
- doc: GEMINI.md
- doc: CONSTITUTION.md
- doc: .github/copilot-instructions.md
- doc: .ai-engineering/CONSTITUTION.md
- doc: .ai-engineering/manifest.yml
- doc: .ai-engineering/contexts/spec-schema.md
- doc: .ai-engineering/references/iocs.json
- doc: .ai-engineering/references/IOCS_ATTRIBUTION.md
- doc: .ai-engineering/specs/_history.md
- doc: .ai-engineering/specs/spec-121-self-improvement-and-hook-completion.md
- doc: .semgrep.yml
- doc: .gitleaks.toml
- doc: .gitleaksignore
- ext: https://semgrep.dev/explore
- ext: https://github.com/gitleaks/gitleaks
