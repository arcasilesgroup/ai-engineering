# Framework Adoption Map (Legacy -> New Contract)

## Purpose

This document maps legacy assets to the new ai-engineering contract.
Each candidate is evaluated as Keep, Adapt, or Drop based on:

- contract compliance,
- simplicity and maintainability,
- security/governance alignment,
- token/context efficiency,
- cross-OS and interoperability relevance.

## Decision Rules

- Keep: can be reused almost as-is without violating the contract.
- Adapt: valuable concept, but requires scope reduction or contract alignment.
- Drop: conflicts with non-negotiables, creates duplication, or adds unnecessary complexity.

## Source Repositories

1. `ai-engineering-dd1a6e55c8281f4a60013345bafbe72445938f5c` (legacy v1)
2. `ai-engineering-e19924c4222cd21fba4ac64fafb367f4ff58833e` (legacy v2)

## Adoption Matrix

| ID  | Legacy Source                                   | Destination (New)                                    | Decision       | Why                                                                                 | Acceptance Check                                                     |
| --- | ----------------------------------------------- | ---------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| A01 | `v1/scripts/install.sh`                         | Python install flow                                  | Adapt          | good readiness logic; convert to minimal Python runtime and ownership-safe behavior | `install` succeeds in empty/existing repo and preserves team/context |
| A02 | `v1/scripts/hooks/pre-commit`                   | `.ai-engineering/hooks/pre-commit` template          | Adapt          | useful baseline; remove any bypass guidance                                         | hook blocks failing checks and contains no skip instructions         |
| A03 | `v1/scripts/hooks/pre-push`                     | `.ai-engineering/hooks/pre-push` template            | Adapt          | keep gate orchestration intent; enforce non-bypass and stack-aware checks           | semgrep + dep-vuln + stack checks run and block on fail              |
| A04 | `v1/standards/quality-gates.md`                 | `standards/framework/quality/core.md`                | Adapt          | strong quality concepts; align to Sonar-like content model                          | quality profile referenced by standards and command workflows        |
| A05 | `v1/.claude/settings.json`                      | Claude template set                                  | Adapt          | keep safe defaults; reduce tool-specific overreach                                  | generated config includes read-safe defaults and governance hooks    |
| A06 | `v1/.claude/skills/validate/SKILL.md`           | `skills/validation/*.md`                             | Adapt          | good validation flow; convert to content-first skill contracts                      | AI can execute validation checklist from content only                |
| A07 | `v1/.claude/skills/utils/platform-detection.md` | `skills/utils/platform-detection.md`                 | Keep           | concise and useful guidance for GitHub/Azure detection                              | install/doctor classify provider correctly in tests                  |
| A08 | `v1/.claude/skills/utils/git-helpers.md`        | `skills/utils/git-helpers.md`                        | Adapt          | useful helpers; trim to high-signal subset                                          | no duplicate commands and only contract-relevant helpers             |
| A09 | `v1/.claude/hooks/block-dangerous.sh`           | runtime safety hook template                         | Adapt          | good safety patterns; simplify and keep cross-OS compatibility                      | destructive commands blocked in smoke tests                          |
| A10 | `v1/.claude/hooks/version-check.sh`             | maintenance report skill + optional doctor extension | Adapt          | useful version/deprecation logic; keep report-first behavior                        | no startup disruption and report-only by default                     |
| A11 | `v1/.claude/skills/ship/SKILL.md`               | N/A                                                  | Drop           | deprecated command model conflicts with `/commit`, `/pr`, `/acho`                   | no `ship` references in standards/templates                          |
| A12 | `v1/context/*.md`                               | `context/product/*` and `context/delivery/*`         | Adapt          | reuse lifecycle ideas and map to canonical structure                                | all lifecycle files exist and are linked                             |
| A13 | `v2/src/updater/merge-strategy.ts`              | `state/ownership-map.json` + Python update policy    | Keep (concept) | strong ownership strategy for safe updates                                          | update modifies framework/system only and preserves team/project     |
| A14 | `v2/src/updater/updater.ts`                     | Python `update` command                              | Adapt          | preserve dry-run/backup/rollback ideas but reduce complexity                        | deterministic dry-run and update report produced                     |
| A15 | `v2/src/installer/platform-check.ts`            | Python doctor + install readiness                    | Adapt          | useful readiness matrix aligned to required tooling                                 | doctor verifies gh/az/hooks/uv/ruff/ty/pip-audit/semgrep/gitleaks    |
| A16 | `v2/src/cli/commands/init.ts`                   | Python install CLI                                   | Adapt          | good sequencing; convert to content-first minimal runtime                           | install creates canonical `.ai-engineering` tree                     |
| A17 | `v2/src/cli/commands/update.ts`                 | Python update CLI                                    | Adapt          | keep UX and dry-run behavior with strict ownership                                  | update never touches `standards/team/**` or `context/**`             |
| A18 | `v2/templates/project/CLAUDE.md.hbs`            | root assistant file template                         | Adapt          | useful but too verbose; compress and reference canonical docs                       | token-lean output with canonical references                          |
| A19 | `v2/templates/project/copilot-instructions.hbs` | `.github/copilot-instructions.md` template           | Adapt          | keep interoperability; remove duplicated policy blocks                              | file points to canonical standards in `.ai-engineering`              |
| A20 | `v2/templates/project/codex.md.hbs`             | `codex.md` template                                  | Adapt          | keep interoperability and command contract                                          | commands match `/commit`, `/pr`, `/acho`                             |
| A21 | `v2/src/compiler/targets/claude-code.ts`        | N/A (heavy compiler)                                 | Drop           | over-engineered for content-first scope                                             | no heavy compile pipeline required                                   |
| A22 | `v2/skills/git/ship.md`                         | N/A                                                  | Drop           | deprecated `ship` semantics                                                         | no ship command in docs/templates/skills                             |
| A23 | `v2/skills/sdlc/plan.md`                        | `skills/sdlc/plan.md`                                | Adapt          | good lifecycle framing; align to canonical phase contract                           | planning skill references canonical context files                    |
| A24 | `v2/agents/_base.md`                            | `agents/base.md` (optional)                          | Adapt          | useful baseline rules; must be concise and platform-agnostic                        | no duplicate standards text and compact size                         |
| A25 | `v2/.ai-engineering/knowledge/*.md`             | `context/learnings.md`                               | Adapt          | keep learning concept but collapse to single file                                   | learnings retained and never overwritten                             |
| A26 | `v2/lefthook.yml`                               | root `lefthook.yml` template (optional)              | Adapt          | practical hook orchestrator; align to non-bypass posture                            | hooks reproducible on Windows/macOS/Linux                            |
| A27 | `v2/.gitleaks.toml`                             | root `.gitleaks.toml` template                       | Keep           | directly aligned with mandatory enforcement                                         | leak fixture blocked in pre-commit test                              |
| A28 | `v2/schemas/config.schema.json`                 | state manifest + ownership schemas                   | Adapt          | strong schema discipline; evolve to provider-agnostic model                         | schema validates GitHub and ADO extension placeholders               |
| A29 | `v2/test/updater/merge-strategy.test.ts`        | Python tests for ownership-safe update               | Adapt          | preserve test intent and rewrite in Python                                          | no-overwrite regression tests pass                                   |
| A30 | `v2/test/installer/platform-check.test.ts`      | Python readiness tests                               | Adapt          | preserve readiness assertions and matrix intent                                     | readiness tests pass in CI matrix                                    |

## Content to Explicitly Exclude

The following must not be imported unchanged:

- any `ship` command artifacts,
- any bypass or skip-hook recommendation,
- large duplicated instruction blocks across assistant files,
- heavy runtime/compiler logic that can be replaced by static templates + minimal installer.

## Required New Artifacts (Not Reused Directly)

These are mandatory in the new contract even if not present in legacy form:

- `state/decision-store.json`,
- `state/audit-log.ndjson`,
- strict ownership map and migration contract,
- compact command contract docs for `/commit`, `/pr`, `/acho`,
- Sonar-like and SonarLint-like quality profiles (content-driven).

## Migration Sequence (Adoption Workstream)

1. Import and normalize high-value content templates.
2. Implement ownership-safe update contract and schemas.
3. Wire minimal Python install/update/doctor/add-remove runtime.
4. Harden hooks and enforce local mandatory checks.
5. Add assistant file templates (Claude/Codex/Copilot) with canonical references only.
6. Dogfood in this repo and run full E2E matrix.
7. Freeze v1 contract and release.

## Exit Criteria for Adoption Completion

Adoption is complete when:

- all Keep/Adapt items are mapped and validated,
- all Drop items are absent from generated outputs,
- update safety is proven (no team/context overwrite),
- mandatory local gates run and block correctly,
- command contract is consistent across assistant targets,
- documentation remains concise and high-signal.
