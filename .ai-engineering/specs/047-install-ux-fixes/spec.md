---
id: "047"
slug: "install-ux-fixes"
status: "in-progress"
created: "2026-03-10"
size: "M"
tags: ["cli", "install", "ux", "bug-fix", "sonar", "vcs"]
branch: "bug/047-install-ux-fixes"
pipeline: "standard"
decisions: []
---

# Spec 047 — Fix `ai-eng install` UX: VCS Alias, Output Clarity, Platform Filtering, Sonar URL

## Problem

Four UX issues found during `ai-eng install` testing in an empty directory:

1. **VCS prompt shows `azure_devops`** — too verbose for a prompt choice; should show `azdo`.
2. **Install output is cluttered** — branch policy guide text printed inline contaminates the summary; hard to distinguish sections.
3. **Platform setup asks about wrong VCS** — if user chose `github`, still asks "Configure azure_devops?". Also, Sonar token validation fails silently with `Expecting value: line 1 column 1 (char 0)` because user entered a full URL with path (`https://sonarcloud.io/organizations/.../projects`) instead of just the base URL.
4. **Template integrity** — changes must work across all AI providers and be reflected in templates for integrity checks.

## Solution

### T1: VCS alias `azdo`
- Change prompt choices from `["github", "azure_devops"]` to `["github", "azdo"]`.
- Map `azdo` → `azure_devops` internally after prompt (canonical form stays `azure_devops` in manifests/models).
- Accept both `--vcs azdo` and `--vcs azure_devops` for backwards compatibility.
- Display `azdo` in user-facing output.

### T2: Clean install output
- Remove the inline branch policy guide text block (`header("Branch Policy Setup Guide")` + `print_stdout(result.guide_text)`). The guide is accessible via `ai-eng guide`.
- Keep warning about manual configuration.
- Add blank lines between summary KV block, "Manual steps required", and "Next steps" sections.

### T3a: Platform filtering by VCS
- Pass VCS provider to `setup_platforms_cmd`.
- Filter undetected platforms: if VCS is `github`, exclude `azure_devops` from prompts (and vice versa). Sonar is always offered.

### T3b: Sonar URL normalization
- Extract `scheme + netloc` from user URL before building API endpoint. Prevents `urljoin` from producing wrong paths when user pastes a page URL.
- Add error message for JSON parse failure: guide user to provide base URL.
- Update prompt hint to clarify "base URL" expectation.

### T4: Verify template integrity
- Confirm changes are in CLI/platform code only, not in templates.
- No template structural changes needed.

## Scope

### In Scope
- VCS alias normalization in CLI prompt and flag
- Install output formatting
- VCS-aware platform filtering in `setup_platforms_cmd`
- Sonar URL normalization in `validate_token`
- Unit tests for all changes

### Out of Scope
- Template file content changes
- New platform support
- CI/CD pipeline changes
- PlatformKind enum changes (canonical form stays `azure_devops`)

## Acceptance Criteria

1. `ai-eng install --vcs azdo /tmp/test` completes successfully with `azdo` shown in output.
2. `ai-eng install --vcs azure_devops /tmp/test` still works (backwards compat).
3. Install output does NOT contain the branch policy guide text block.
4. Install output has clear visual separation between summary, manual steps, and next steps.
5. After choosing `--vcs github`, platform setup does NOT prompt for `azure_devops`.
6. Sonar validation with `https://sonarcloud.io/organizations/foo/projects` normalizes to `https://sonarcloud.io` before API call.
7. Sonar prompt shows "base URL" hint.
8. All existing tests pass; new tests cover the 4 fixes.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Accept both `azdo` and `azure_devops` at CLI | Backwards compatibility; normalize at entry point |
| D2 | Keep canonical `azure_devops` internally | Avoids breaking manifests, Pydantic models, state files |
| D3 | Remove inline guide, keep `ai-eng guide` pointer | Separation of concerns; guide is long, clutters install output |
