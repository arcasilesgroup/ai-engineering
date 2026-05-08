---
name: ai-board-discover
description: "Discovers and configures project-board integration (GitHub Projects v2 or Azure DevOps) after install: detects fields, state mappings, process templates, and writes atomic config to manifest.yml. Trigger for 'set up the board', 'board sync is not working', 'configure our ADO board', 'the work item states do not match', 'discover board fields'. Not for routine state transitions; use /ai-board-sync instead. Not for backlog execution; use /ai-run instead."
effort: high
argument-hint: "[--refresh]"
tags: [board, discovery, configuration]
---


# Board Discover

## Purpose

LLM-assisted post-install discovery of board configuration. Detects the team's project board setup, process template, state mappings, writable custom fields, documentation URLs, and CI/CD standards URLs. Writes discovered configuration atomically to manifest.yml.

## When to Use

- After initial framework install (`ai-eng install`)
- When board configuration changes (new project, new fields)
- Manual refresh: `/ai-board-discover --refresh`. `--refresh` forces re-discovery even when board config already exists in manifest, overwriting previous values.
- Suggested by `/ai-start` when board config is missing

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md` (informs field mapping conventions).

## Process

1. **Auth pre-flight + manifest** -- verify authentication (`gh auth status` or `az account show`); if not authenticated, report remediation and abort. Then read `.ai-engineering/manifest.yml` `work_items` to determine active provider (`github` or `azure_devops`).

2. **Discover board** -- based on provider:

   **GitHub path**:
   a. Detect owner: if `github_project.owner` exists in manifest, use it. Otherwise, detect from git remote: `gh repo view --json owner -q '.owner.login'`
   b. List projects: `gh project list --owner <owner> --format json`
   c. If projects found, select the most relevant one (by name match or ask user if ambiguous)
   d. Discover fields: `gh project field-list <number> --owner <owner> --format json`
   e. Identify the Status field (single-select type) and extract its option IDs and names
   f. Map status options to lifecycle phases: refinement, ready, in_progress, in_review, done
   g. Discover writable custom fields (non-standard fields beyond Title, Status, Labels, Milestone)
   h. If NO Projects v2 found: configure labels fallback (see State Mapping Conventions below).

   **Azure DevOps path**:
   a. List process templates: `az boards work-item type list --project <project> -o json`
   b. Detect process template (Basic, Agile, Scrum, CMMI) from available work item types
   c. For each work item type, discover valid states: `az boards work-item type show --type <type> --project <project> -o json`
   d. Map states to lifecycle phases based on process template conventions
   e. Discover custom fields: `az boards work-item show --id <sample-id> --expand all -o json` (use any recent work item)

3. **Discover documentation URL** -- scan repo for docs configuration:
   - Check for: `mkdocs.yml`, `docusaurus.config.js`, `docs/conf.py`, `.readthedocs.yml`, `book.toml`
   - If found, extract the published URL from config or infer from repo name
   - Store in `documentation.external_portal` if not already set

4. **Discover CI/CD standards URL** -- scan for standards references:
   - Check `.github/workflows/*.yml` or `.azure-pipelines/` for comments referencing standards docs
   - Check manifest `cicd.standards_url` -- if null, search for common patterns
   - If found, prepare value for `cicd.standards_url`

5. **Build config atomically** -- assemble complete discovered configuration in memory:
   ```yaml
   state_mapping:
     refinement: "<discovered>"
     ready: "<discovered>"
     in_progress: "<discovered>"
     in_review: "<discovered>"
     done: "<discovered>"
   process_template: "<detected>"
   custom_fields:
     - id: "<field_id>"
       name: "<field_name>"
       type: "<field_type>"
   github_project:
     owner: "<detected_org_or_user>"
     number: <N>
     status_field_id: "<id>"
     status_options:
       refinement: "<option_id>"
       ready: "<option_id>"
       in_progress: "<option_id>"
       in_review: "<option_id>"
       done: "<option_id>"
   ```

6. **Write to manifest** -- ONLY write when all discovery succeeds. Partial failure means no write. Update `.ai-engineering/manifest.yml` `work_items` section with discovered values. This data is later consumed by portable runbooks so they can populate provider-native writable fields without guessing the client's board shape.

7. **Report** -- present structured summary to user:
   ```
   Board Discovery Complete
   Provider: GitHub Projects v2
   Project: #4 "Engineering Board"
   States mapped: 5/5 (Triage -> refinement, Ready -> ready, ...)
   Custom fields: 3 (Priority, Size, Estimate)
   CI/CD standards: not found
   Docs URL: not found
   ```

## State Mapping Conventions

### GitHub Projects v2

| Lifecycle Phase | Common Status Names |
|----------------|-------------------|
| refinement | Triage, Backlog, New, Refinement |
| ready | Ready, To Do, Approved, Planned |
| in_progress | In Progress, Active, Doing, Working |
| in_review | In Review, Review, PR Review |
| done | Done, Closed, Complete, Shipped |

### Azure DevOps

| Lifecycle Phase | Agile | Scrum | CMMI |
|----------------|-------|-------|------|
| refinement | New | New | Proposed |
| ready | Approved | Approved | Active |
| in_progress | Active | Committed | Active |
| in_review | Resolved | Done | Resolved |
| done | Closed | Done | Closed |

### Labels Fallback (GitHub without Projects v2)

Uses labels with `status:` prefix: `status:refinement`, `status:ready`, `status:in-progress`, `status:in-review`, `status:done`.

## Common Mistakes

- Writing partial discovery results to manifest (violates atomic write protocol)
- Guessing state mappings without checking actual field options
- Not handling the case where Projects v2 exists but has no Status field
- Assuming field IDs are stable across projects (they are project-specific)

## Examples

### Example 1 — first-time discovery on GitHub project

User: "configure board sync for our GitHub Projects v2 board"

```
/ai-board-discover
```

Detects the active Projects v2 board, queries Status field options, infers mapping from canonical phases (refinement/ready/in_progress/in_review/done), writes the config block atomically into `manifest.yml`.

### Example 2 — refresh after switching projects

User: "we just moved to a new ADO project — refresh the board config"

```
/ai-board-discover --refresh
```

Forces re-discovery, overwrites the previous `work_items` block, validates writability of the configured fields.

## Integration

Called by: user directly, `/ai-start` (when config missing). Writes: `.ai-engineering/manifest.yml` `work_items` section. Pairs with: `/ai-board-sync` (consumes the config written here). See also: `/ai-run` (board-driven backlog execution).

$ARGUMENTS
