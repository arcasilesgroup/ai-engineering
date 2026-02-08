# AI Agent Instructions for ai-engineering

> **Single Source of Truth:** This file provides essential pointers for AI agents. Detailed context lives in `.ai-engineering/context/`.

## Quick Start (3-Step Bootstrap)

1. **Read Strategic Context:**
   - [Product Vision](.ai-engineering/context/product/vision.md) - Why this exists, key differentiators
   - [Roadmap](.ai-engineering/context/product/roadmap.md) - Phases, priorities, current focus

2. **Read Technical Context:**
   - [Architecture](.ai-engineering/context/delivery/architecture.md) - System design, module boundaries
   - [Planning](.ai-engineering/context/delivery/planning.md) - Module specs, acceptance criteria

3. **Read Standards:**
   - [manifest.yml](.ai-engineering/manifest.yml) - Enforced standards (linting, gates, security)

## Product Principles (Critical - Read First)

**Source:** See full principles in `.ai-engineering/context/product/vision.md`

**Non-Negotiables:**
1. **Single Source of Truth:** No duplication. `.ai-engineering/` is canonical governance root.
2. **Token Efficiency:** All files concise, high-signal. Optimize context footprint.
3. **Mandatory Local Enforcement:** Git hooks non-bypassable. Failures fixed locally.
4. **Lifecycle Enforced:** Discovery → Architecture → Planning → Implementation → Review → Verification → Testing → Iteration

## Development Workflow

**For Each Module:**
1. Read `.ai-engineering/context/delivery/planning.md` for module spec
2. Read `.ai-engineering/context/delivery/testing.md` for testing strategy
3. Write tests first (TDD), then implement
4. Follow standards in `manifest.yml` (linting, formatting, type checking)
5. Commit using conventional commits (see manifest.yml)

## Code Standards (Enforced)

**All rules in:** `.ai-engineering/manifest.yml`

**Quick Reference:**
- **Python:** Type hints (mypy --strict), line length 100 (ruff)
- **Testing:** >80% coverage, TDD approach
- **Commits:** `<type>(<scope>): <subject>` (see manifest.yml for pattern)
- **Branches:** `feature/<name>`, `fix/<name>`, `refactor/<name>`

**Pre-Commit (Manual until gate engine exists):**
```bash
poetry run pytest && poetry run ruff check src/ tests/ && poetry run mypy src/
```

## Module Structure

**See:** `.ai-engineering/context/delivery/architecture.md` for complete design

```
src/ai_engineering/
  cli.py              # Typer app and command routing
  state/              # State management (Module 1.2)
  standards/          # Standards resolution (Module 1.3)
  gates/              # Gate engine (Module 2.2)
  installer/          # Installation logic (Module 2.1)
```

## Common Patterns

**Loading manifest.yml:**
```python
from pathlib import Path
import yaml
from pydantic import BaseModel

class ManifestSchema(BaseModel):
    version: str
    metadata: dict
    standards: dict

manifest = ManifestSchema(**yaml.safe_load(Path(".ai-engineering/manifest.yml").read_text()))
```

**Atomic file writes:**
See architecture.md section "State Management" for atomic write pattern.

## Security (Critical)

**Never commit:** `.env`, `*.pem`, `*.key`, `credentials.json` (see manifest.yml security.sensitive_patterns)

**Destructive ops:** Always warn, require confirmation, log (see manifest.yml security.allowed_destructive_ops)

## Context Optimization

**Token Budget:** 8000 tokens default (see manifest.yml context_optimization)

**Priority Files (always include):**
1. manifest.yml
2. CLAUDE.md (this file)
3. README.md
4. context/product/vision.md
5. context/delivery/architecture.md

**Conditional:** Only include tests/ when task.type == 'testing', src/ when task.type == 'implementation'

## When Stuck

1. Check `.ai-engineering/context/delivery/planning.md` for module acceptance criteria
2. Check `.ai-engineering/context/delivery/architecture.md` for design patterns
3. Check `manifest.yml` for standards enforcement rules
4. Ask user for clarification (don't assume)

---

**Remember:** We're building the framework that enforces these practices. Dogfood rigorously.
