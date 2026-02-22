---
spec: "015"
approach: "serial-phases"
---

# Plan — Spec-015: Multi-Stack Security & Quality Capabilities

## Architecture

The implementation extends three layers:

1. **Standards layer**: new stack contracts, quality profiles, security standards, CI/CD standard.
2. **Skills/Agents layer**: new security skills, CI/CD skill, utility patterns; updated existing agents.
3. **Runtime layer**: `gates.py` stack-aware dispatch, `models.py` new tooling models, `readiness.py` multi-stack detection.

## Phases

### Phase 1 — Multi-Stack Foundation

- Stack contracts: `dotnet.md`, `nextjs.md`.
- Quality profiles: `quality/dotnet.md`, `quality/nextjs.md`.
- Manifest restructuring (backward-compatible).
- `gates.py` stack-aware refactoring.
- `models.py` and `readiness.py` extensions.

### Phase 2 — Security Capabilities Expansion

- OWASP Top 10 2025 standard.
- New skills: DAST, container security, SBOM.
- Updated agents: security-reviewer, platform-auditor.
- Manifest optional tooling.

### Phase 3 — CI/CD Workflow Generation

- CI/CD core standard.
- CI/CD generation skill.

### Phase 4 — Quality Audit Multi-Stack

- Updated `audit-code.md` and `quality-auditor.md`.
- New utility patterns: `dotnet-patterns.md`, `nextjs-patterns.md`.

### Cross-Cutting

- All mirrors synchronized.
- Instruction files updated with new skill/agent counts.
- Product-contract counters updated.
- Tests for runtime changes.

## Mirror Copies

Each new governance file requires a mirror in `src/ai_engineering/templates/`:

| Canonical | Mirror |
|-----------|--------|
| `.ai-engineering/standards/framework/stacks/dotnet.md` | `templates/.ai-engineering/standards/framework/stacks/dotnet.md` |
| `.ai-engineering/standards/framework/stacks/nextjs.md` | `templates/.ai-engineering/standards/framework/stacks/nextjs.md` |
| `.ai-engineering/standards/framework/quality/dotnet.md` | `templates/.ai-engineering/standards/framework/quality/dotnet.md` |
| `.ai-engineering/standards/framework/quality/nextjs.md` | `templates/.ai-engineering/standards/framework/quality/nextjs.md` |
| `.ai-engineering/standards/framework/security/owasp-top10-2025.md` | `templates/.ai-engineering/standards/framework/security/owasp-top10-2025.md` |
| `.ai-engineering/skills/review/dast.md` | `templates/.ai-engineering/skills/review/dast.md` |
| `.ai-engineering/skills/review/container-security.md` | `templates/.ai-engineering/skills/review/container-security.md` |
| `.ai-engineering/skills/quality/sbom.md` | `templates/.ai-engineering/skills/quality/sbom.md` |
| `.ai-engineering/standards/framework/cicd/core.md` | `templates/.ai-engineering/standards/framework/cicd/core.md` |
| `.ai-engineering/skills/dev/cicd-generate.md` | `templates/.ai-engineering/skills/dev/cicd-generate.md` |
| `.ai-engineering/skills/utils/dotnet-patterns.md` | `templates/.ai-engineering/skills/utils/dotnet-patterns.md` |
| `.ai-engineering/skills/utils/nextjs-patterns.md` | `templates/.ai-engineering/skills/utils/nextjs-patterns.md` |

Slash command wrappers also need mirrors in `templates/project/.claude/commands/`.
