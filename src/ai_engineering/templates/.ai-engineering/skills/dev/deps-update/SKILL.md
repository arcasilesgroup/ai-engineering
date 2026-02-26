---
name: deps-update
description: "Audit, update, and validate project dependencies for security and compatibility; use when addressing vulnerabilities, outdated packages, or version bumps."
version: 1.0.0
category: dev
tags: [dependencies, security, vulnerabilities, updates]
metadata:
  ai-engineering:
    scope: read-write
    token_estimate: 750
---

# Dependency Update

## Purpose

Structured dependency update skill: audit current dependencies, update safely, test compatibility, and validate security posture. Ensures updates don't introduce vulnerabilities or breaking changes.

## Trigger

- Command: agent invokes deps-update skill or user requests dependency updates.
- Context: security advisory, outdated packages, version bump, vulnerability scan findings.

## Procedure

1. **Detect stack** — identify active stacks from project files.
   - Python: `pyproject.toml` or `requirements.txt` → use `pip-audit` + `uv`.
   - TypeScript/Node.js: `package.json` → use `npm audit` (or `pnpm audit` / `bun audit`).
   - .NET: `*.csproj` or `*.sln` → use `dotnet list package --vulnerable`.
   - Rust: `Cargo.toml` → use `cargo audit`.
   - Run detection in parallel for multi-stack projects.

2. **Audit** — assess current dependency state per stack.
   - Python: `pip-audit` for CVEs, `uv pip list --outdated` for updates.
   - TypeScript: `npm audit` for advisories, `npm outdated` for updates.
   - .NET: `dotnet list package --vulnerable`, `dotnet list package --outdated`.
   - Rust: `cargo audit` for advisories, `cargo outdated` for updates.
   - Categorize: security-critical, feature updates, patch updates.

3. **Plan updates** — prioritize and sequence.
   - Security vulnerabilities first (critical → high → medium).
   - One dependency at a time for major version bumps.
   - Batch minor/patch updates that are low-risk.
   - Check changelogs for breaking changes.

4. **Update** — apply changes per stack.
   - Python: update `pyproject.toml`, run `uv sync`.
   - TypeScript: update `package.json`, run `npm install` (or `pnpm install`/`bun install`).
   - .NET: `dotnet add package <name> --version <ver>`, `dotnet restore`.
   - Rust: update `Cargo.toml`, run `cargo update`.
   - For major version changes: review migration guide.

5. **Test** — verify compatibility with stack-appropriate tools.
   - Python: `pytest tests/ -v`, `ty check src/`, `ruff check src/`.
   - TypeScript: `vitest run`, `tsc --noEmit`, `eslint .`.
   - .NET: `dotnet test`, `dotnet build`.
   - Rust: `cargo test`, `cargo clippy`.

6. **Validate security** — re-audit after updates.
   - Re-run the stack-appropriate audit tool to confirm vulnerabilities resolved.
   - Run `semgrep` to check for new security patterns.
   - Verify no new advisories introduced by updates.

## Output Contract

- List of dependencies updated with before/after versions (per stack).
- Vulnerability resolution summary.
- Test results confirming compatibility.
- Updated dependency files (`pyproject.toml`, `package.json`, `*.csproj`, `Cargo.toml`) and lock files.

## Governance Notes

- Security-critical updates should not be deferred without explicit risk acceptance in `state/decision-store.json`.
- Never downgrade a dependency to resolve a conflict without documented justification.
- Pin exact versions in lockfile, use compatible ranges in `pyproject.toml`.
- `pip-audit` must pass before push (pre-push gate).

### Iteration Limits

- Max 3 attempts to resolve the same dependency issue. After 3 failures, escalate to user with evidence of attempts.
- Each attempt must try a different approach — repeating the same action is not a valid retry.

### Post-Action Validation

- After updating dependencies, run `ruff check` and `ruff format --check` on modified files.
- Run `pip-audit` to verify no new vulnerabilities introduced.
- If validation fails, fix issues and re-validate (max 3 attempts per iteration limits).

## References

- `standards/framework/stacks/python.md` — Python tooling and patterns.
- `standards/framework/stacks/typescript.md` — TypeScript/Node.js tooling.
- `standards/framework/stacks/dotnet.md` — .NET tooling.
- `standards/framework/stacks/rust.md` — Rust tooling.
- `standards/framework/quality/core.md` — security gate.
- `standards/framework/core.md` — risk acceptance policy.
- `agents/security-reviewer.md` — agent that assesses dependency security.
