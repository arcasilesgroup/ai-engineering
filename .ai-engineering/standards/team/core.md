# Team Core Standards

## Update Metadata

- Rationale: provide safe team-level extension surface.
- Expected gain: customization without policy drift.
- Potential impact: team docs must follow non-negotiable constraints.

## Purpose

Team-specific standards that extend framework defaults without weakening non-negotiables.

## Allowed Customizations

- Naming and style conventions.
- Additional quality gates.
- Team workflows for review and planning.

## Forbidden Customizations

- Disabling mandatory local enforcement.
- Removing required security checks.
- Allowing direct commits to protected branches.

## GitHub MCP Tooling

When interacting with GitHub remotely (create PRs, branches, push files, etc.):

- **Use**: `mcp_io_github_git_*` tools — authenticated as **soydachi** (personal account with repo access).
- **Never use**: `mcp_github_*` tools — authenticated as Enterprise Managed User (returns 403 on this repository).

This applies to all GitHub operations: PR creation, branch creation, file operations, reviews.

## Ownership Contract

This file is team-managed and is never overwritten by framework updates.
