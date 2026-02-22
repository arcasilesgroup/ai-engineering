---
id: "015"
slug: "multi-stack-security-quality"
status: "in-progress"
created: "2026-02-22"
---

# Spec-015: Multi-Stack Security & Quality Capabilities

## Problem

The ai-engineering framework currently supports only Python as a stack. Projects using .NET, Next.js, or other stacks cannot leverage the framework's quality gates, readiness detection, or security enforcement. Additionally, several security capabilities (DAST, container scanning, SBOM generation, OWASP Top 10 2025 mapping) are missing entirely.

## Solution

Extend the framework with:

1. **Multi-stack foundation**: stack contracts, quality profiles, and stack-aware gate dispatch for .NET and Next.js.
2. **Security capabilities expansion**: OWASP Top 10 2025 standard, DAST, container security, and SBOM skills.
3. **CI/CD workflow generation**: standard and skill for generating stack-aware CI/CD workflows.
4. **Quality audit multi-stack**: update existing quality skills and agents to detect and operate across stacks.

## Scope

### In Scope

- Stack contracts: `dotnet.md`, `nextjs.md` (standards + quality profiles).
- Manifest restructuring for per-stack enforcement checks.
- `gates.py` refactoring for stack-aware dispatch with Python-only fallback.
- State models: `DotnetTooling`, `NextjsTooling` in `models.py`.
- Readiness detection: parametrized by active stacks.
- OWASP Top 10 2025 mapping standard.
- New skills: DAST, container security, SBOM, CI/CD generation.
- Updated agents: security-reviewer, platform-auditor, quality-auditor.
- Utility patterns: `dotnet-patterns.md`, `nextjs-patterns.md`.

### Out of Scope

- Actual CI/CD pipeline execution (skill generates, project maintains).
- Runtime tool installation for .NET/Node.js (readiness detection only).
- Stack add/remove CLI implementation changes (covered by existing commands).

## Acceptance Criteria

1. `ai-eng gate pre-commit` and `ai-eng gate pre-push` execute only checks for installed stacks.
2. Python-only projects exhibit no behavior change (backward compatible).
3. New skills pass `integrity-check` with zero violations.
4. All mirrors synchronized between canonical and template.
5. Instruction file counters match product-contract.
6. All new standards follow existing template structure.

## Decisions

Decisions will be recorded in `decision-store.json` as they arise.
