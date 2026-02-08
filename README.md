# ai-engineering

**Context-first AI governance framework for development teams**

## Overview

ai-engineering provides enforceable standards, session management, and security gates for AI-assisted development. Instead of advisory documentation that agents ignore, this framework uses local enforcement, git hooks, and structured context to ensure consistent, secure AI workflows.

## Status

🚧 **Phase 1 MVP in Development**

- ✅ Phase 0: Complete governance and context structure
- 🔨 Phase 1: Core CLI and state management (in progress)
- 📋 Phase 2: Branch governance and remote skills (planned)
- 📋 Phase 3: Agent orchestration and maintenance (planned)

## Quick Start

*Installation instructions will be added when MVP is complete.*

## Documentation

All project context, architecture, and planning lives in `.ai-engineering/context/`:

- [Product Vision](.ai-engineering/context/product/vision.md)
- [Roadmap](.ai-engineering/context/product/roadmap.md)
- [Architecture](.ai-engineering/context/delivery/architecture.md)
- [Planning](.ai-engineering/context/delivery/planning.md)

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run linter
poetry run ruff check src/ tests/

# Run type checker
poetry run mypy src/
```

## License

MIT (see LICENSE file)
