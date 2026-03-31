---
name: ai-board-discover
description: "Use to discover and configure project board integration after framework install, when board config is missing or stale, or when the team switches projects. Trigger for 'set up the board', 'board sync isn't working', 'we moved to a new GitHub project', 'configure our ADO board', 'the work item states don't match'. Detects GitHub Projects v2 or Azure DevOps fields and writes atomic config to manifest.yml."
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
- Manual refresh: `/ai-board-discover --refresh`
- Suggested by `/ai-start` when board config is missing

## Process

1. **Read manifest** -- read `.ai-engineering/manifest.yml` `work_items` section. Determine active provider (`github` or `azure_devops`).

2. **Discover board** -- based on provider:

   **GitHub path**:
   a. Detect owner: if `github_project.owner` exists in manifest, use it. Otherwise, detect from git remote: `gh repo view --json owner -q '.owner.login'`
   b. List projects: `gh project list --owner <owner> --format json`
   c. If projects found, select the most relevant one (by name match or ask user if ambiguous)
   d. Discover fields: `gh project field-list <number> --owner <owner> --format json`
   d. Identify the Status field (single-select type) and extract its option IDs and names
   e. Map status options to lifecycle phases: refinement, ready, in_progress, in_review, done
   f. Discover writable custom fields (non-standard fields beyond Title, Status, Labels, Milestone)
   g. If NO Projects v2 found: configure labels fallback (status labels like `status:refinement`, `status:ready`, etc.)

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

## Atomic Write Protocol

1. All discovery steps execute first -- results held in memory
2. If ANY discovery step fails critically (provider CLI not authenticated, no project access):
   - Log the failure with remediation hint
   - Do NOT write partial results to manifest
   - Report what succeeded and what failed
3. Only on full success: write all fields to manifest.yml in a single edit

## Common Mistakes

- Writing partial discovery results to manifest (violates atomic write protocol)
- Guessing state mappings without checking actual field options
- Not handling the case where Projects v2 exists but has no Status field
- Assuming field IDs are stable across projects (they are project-specific)

## Integration

- **Called by**: user directly, `/ai-start` (suggestion when board config missing)
- **Writes**: `.ai-engineering/manifest.yml` (work_items section)
- **Transitions to**: manual -- user reviews discovered config
- **Pair**: `/ai-board-sync` (sync uses config written by discover; run discover first if sync fails)

$ARGUMENTS
