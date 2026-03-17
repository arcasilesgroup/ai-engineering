---
name: ai-contract
version: 1.0.0
description: "Manage product contract lifecycle: init (scaffold from template), sync (auto-update from specs/KPIs/roadmap), validate (check completeness and freshness)."
argument-hint: "init|sync|validate"
tags: [product, contract, solution-intent, governance, planning]
---


# Product Contract

## Purpose

Manage the product contract (`context/product/product-contract.md`) lifecycle. The product contract is the Solution Intent -- it defines **what you are building** (complementing the framework contract which defines **how you operate**). Three modes ensure the contract stays accurate, complete, and fresh.

## Trigger

- Command: `/ai-product-contract init`, `/ai-product-contract sync`, `/ai-product-contract validate`
- Context: product contract needs initialization, synchronization after changes, or completeness validation.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"product-contract"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Framework contract changes** -- use `framework-contract.md` directly (framework-managed).
- **Spec creation** -- use `/ai-spec` for individual spec lifecycle.
- **Release notes** -- use `/ai-changelog` for changelog updates.

## Preconditions

- `.ai-engineering/` governance root must exist.
- `manifest.yml` must be present and valid.

## Modes

### Mode 1: init

For new projects or projects without a product contract.

#### Procedure

1. **Read template** -- load `templates/.ai-engineering/context/product/product-contract.md`.
2. **Gather data** -- ask user for:
   - Project name, org/repo, version, status, license.
   - Primary objective (1 paragraph).
   - Problem statement (1 paragraph).
   - Key personas (at least 2).
3. **Auto-detect** -- from repo context:
   - Stack from `manifest.yml` tooling.
   - VCS provider from `manifest.yml` providers.
   - Existing skills/agents count from `manifest.yml` governance surface.
4. **Scaffold** -- replace template placeholders with gathered + detected data.
5. **Write** -- save to `context/product/product-contract.md`.
6. **Report** -- show sections populated vs sections needing manual input.

### Mode 2: sync

Auto-update specific sections based on project changes. Surgical updates only -- never rewrite the entire contract. Never delete user-authored content.

#### Procedure

1. **Read current contract** -- load `context/product/product-contract.md`.
2. **Detect changes** -- check triggers:

| Trigger | Sections Affected | Source |
|---------|-------------------|--------|
| Spec closure (`done.md` created) | 7.2 epic status, 7.4 active spec | spec skill |
| Release completion | 7.1 roadmap, 7.3 KPIs | release skill |
| Stack add/remove | 3.1 stack & architecture | `manifest.yml` |
| Security scan delta | 5.4 hardening checklist, 7.3 KPIs | verify agent |
| Decision store update | 2.2 if domain-relevant | `decision-store.json` |
| Skill/agent add/remove | 2.2 AI Ecosystem row, 6.4 scalability | `manifest.yml` |

3. **Apply updates** -- for each affected section:
   - Read existing section content.
   - Merge new data (update tables, status fields, counts).
   - Preserve all user-authored text and custom content.
4. **Update header** -- set `Last Review: <today>`.
5. **Stage** -- `git add context/product/product-contract.md`.

### Mode 3: validate

Read-only completeness and freshness check. Produces a scorecard.

#### Procedure

1. **Read contract** -- load `context/product/product-contract.md`.
2. **Check completeness** -- for each of the 7 sections:
   - Verify section header exists.
   - Verify at least one table or Mermaid diagram per section.
   - Verify no placeholder markers (`<...>`) remain.
   - Verify subsections are populated (not empty).
3. **Check freshness** -- parse `Last Review` date.
   - If > 30 days ago: WARNING (stale).
   - If > 60 days ago: CRITICAL (very stale).
4. **Check consistency** -- cross-reference with:
   - `manifest.yml` skill/agent counts vs contract Section 2.2.
   - `manifest.yml` tooling vs contract Section 3.1.
   - Active spec pointer vs `context/specs/_active.md`.
5. **Produce scorecard**:

```
| Section | Status | Notes |
|---------|--------|-------|
| 1. Introduction | COMPLETE | |
| 2. Requirements | COMPLETE | |
| 3. Technical Design | COMPLETE | |
| 4. Observability Plan | COMPLETE | |
| 5. Security | PARTIAL | Missing NFR thresholds |
| 6. Quality | COMPLETE | |
| 7. Next Objectives | COMPLETE | |
| --- | --- | --- |
| Freshness | OK | Last review: 5 days ago |
| Consistency | OK | Counts match manifest |
```

## Output Contract

- **init**: product-contract.md file created with populated sections + report of remaining TODOs.
- **sync**: updated sections listed with before/after summary.
- **validate**: scorecard table with COMPLETE/PARTIAL/MISSING per section + freshness + consistency.

## Governance Notes

**Visual priority**: diagrams > tables > text. Every section MUST have at least one Mermaid diagram or table. Text accompanies but does not substitute visual representation.

**Ownership**: product-contract.md is project-managed. The sync mode updates data fields but never removes user-authored content. The framework updater (`ai-eng update`) does not touch this file.

**Owner agent**: plan.

## References

- `context/product/product-contract.md` -- the contract instance.
- `context/product/framework-contract.md` -- the companion "how you operate" contract.
- `manifest.yml` -- governance surface counts, tooling, providers.
- `standards/framework/core.md` -- quality and security thresholds.
$ARGUMENTS
