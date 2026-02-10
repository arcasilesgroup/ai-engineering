# Spec 002: Cross-Reference Hardening + Skill Registration

## Problem

After Spec 001 (Rewrite v2) delivered 18 skills and 8 agents, these governance gaps remained:

1. **Missing cross-references** — skills did not reference related agents, and agents did not reference all consumed skills. This broke the bidirectional discoverability contract: an agent reading a skill couldn't find related agents, and vice versa.
2. **No lifecycle skills** — the framework had no procedure for creating skills (`create-skill`), creating agents (`create-agent`), documenting changelogs (`changelog-documentation`), or generating user-facing documentation (`doc-writer`). These were tribal knowledge, not governed procedures.
3. **No lifecycle skill category** — `create-skill` and `create-agent` are not SWE skills (they don't produce application code). They are framework lifecycle operations that belong in their own category.
4. **Skill count drift** — product-contract.md reported "18 skills" but the actual target after adding 4 new skills is 22. Counters must match reality.

## Solution

Three-phase approach:

- **Phase 1 (New Skills)**: Author 4 new skills (`changelog-documentation`, `create-skill`, `create-agent`, `doc-writer`) with canonical files, template mirrors, instruction file registration, and changelog entries.
- **Phase 2 (Cross-Reference Hardening)**: Add bidirectional cross-references across all 25+ governance files — skills reference related agents, agents reference consumed skills, utility/validation skills reference their consumers.
- **Phase 3 (Lifecycle Category)**: Create `skills/lifecycle/` as a new skill category. Move `create-skill` and `create-agent` from `swe/` to `lifecycle/`. Update all references to reflect the new paths.

## Scope

### In Scope

- 4 new skills: `changelog-documentation.md`, `create-skill.md`, `create-agent.md`, `doc-writer.md`.
- Cross-reference additions across agents (5 files), SWE skills (8 files), utility skills (2 files), validation skills (1 file), workflow skills (2 files).
- All 6 instruction files updated with new skill references.
- Product-contract counter updates (18 → 21 skills).
- CHANGELOG.md entries for new skills.
- New `skills/lifecycle/` category directory.
- Move `create-skill` and `create-agent` from `swe/` to `lifecycle/` (canonical + mirror).
- Update `create-skill.md` procedure to include `lifecycle/` as a valid category.
- Instruction file restructuring: new `### Lifecycle Skills` subsection.

### Out of Scope

- Governance enforcement rules (Spec 003).
- `delete-skill`, `delete-agent`, `create-spec`, `content-integrity` skills (Spec 003).
- `verify-app` agent expansion (Spec 003).
- Enforcement rules in `core.md` or `framework-contract.md` (Spec 003).
- Any Python code changes (glob-based discovery handles new files automatically).

## Acceptance Criteria

- [ ] All 4 new skills exist as canonical files with byte-identical template mirrors.
- [ ] `create-skill` and `create-agent` are in `skills/lifecycle/`, not `skills/swe/`.
- [ ] `skills/lifecycle/` is referenced in the `create-skill` procedure as a valid category.
- [ ] All 6 instruction files list all 22 skills with correct paths.
- [ ] Product-contract shows "21 skills, 8 agents" in objectives and KPIs.
- [ ] Bidirectional cross-references exist: every agent references its consumed skills, every skill references agents that use it.
- [ ] CHANGELOG.md has entries for all 4 new skills.
- [ ] Template mirrors for moved files reflect the new `lifecycle/` paths.

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **`skills/lifecycle/`** as new category name | Descriptive of purpose (framework lifecycle operations). Alternatives `framework/` and `core/` were rejected — `framework/` conflicts with `standards/framework/`, and `core/` is too generic. |
| D2 | **Move `create-skill`/`create-agent` to `lifecycle/`** | These skills govern framework administration, not application SWE. Keeping them in `swe/` misrepresents their purpose. |
| D3 | **Separate Spec 002 from Spec 003** | Spec 002 formalizes content that is already written (git changes). Spec 003 introduces new governance capabilities. Separating avoids a mega-spec and allows incremental delivery. |
| D4 | **21 skills total** | 14 SWE + 3 workflows + 2 lifecycle + 2 quality = 21. Utility and validation skills (git-helpers, platform-detection, install-readiness) are not counted in the instruction-file listing convention. |
