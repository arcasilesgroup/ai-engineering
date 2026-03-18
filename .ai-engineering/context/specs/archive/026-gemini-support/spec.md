---
id: "026"
slug: "gemini-support"
status: "in-progress"
created: "2026-02-27"
---

# Spec 026 — Gemini Support

## Problem
The project currently supports Claude and GitHub Copilot with dedicated configuration files (`CLAUDE.md`, `.github/prompts/`, etc.). However, there is no standardized support for Gemini, which limits the ability of Gemini-based agents to interact effectively with the repository and follow its governance.

## Solution
Introduce comprehensive support for Gemini by:
1.  Creating a `GEMINI.md` file that mirrors `CLAUDE.md` but tailored for Gemini CLI.
2.  Ensuring Gemini agents can access and utilize the project's skills and governance structures.
3.  Registering Gemini as a supported platform in the documentation/governance.

## Scope
### In Scope
- Creation of `GEMINI.md`.
- Validation that Gemini CLI can read and respect the governance rules.
- Updates to `README.md` or other documentation to mention Gemini support.

### Out of Scope
- Creating new skills exclusively for Gemini (we will reuse existing ones where possible).
- Implementing a full Gemini-specific MCP server (unless required).

## Acceptance Criteria
1.  `GEMINI.md` exists and contains relevant context, governance rules, and skill references.
2.  Gemini CLI can successfully execute key workflows (e.g., `govern:create-spec`, `commit`, `pr`) using the instructions in `GEMINI.md`.
3.  The project's governance documentation reflects Gemini support.

## Decisions
| ID | Decision | Rationale |
|---|---|---|
| D-001 | Use `GEMINI.md` as the entry point | Matches the pattern established by `CLAUDE.md`. |
