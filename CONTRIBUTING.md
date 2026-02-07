# Contributing to ai-engineering

Thank you for your interest in contributing to ai-engineering! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites
- Node.js 20+
- pnpm 9+
- Git

### Getting Started

```bash
git clone https://github.com/your-org/ai-engineering.git
cd ai-engineering
pnpm install
pnpm build
```

### Development Commands

```bash
pnpm dev          # Watch mode build
pnpm test         # Run tests
pnpm test:watch   # Watch mode tests
pnpm lint         # Lint code
pnpm typecheck    # Type check
pnpm format       # Format code
```

## Project Structure

- `src/cli/` — CLI entry point and commands
- `src/compiler/` — Standards assembler and IDE target compilers
- `src/installer/` — Installation orchestration (hooks, gates, knowledge)
- `src/updater/` — Version check and safe update system
- `src/hooks/` — Runtime and git hook scripts
- `src/utils/` — Shared utilities
- `stacks/` — Technology stack standards (markdown)
- `agents/` — AI agent definitions (markdown)
- `skills/` — Interactive workflow definitions (markdown)
- `templates/` — Handlebars templates for output files
- `schemas/` — JSON schemas for validation
- `test/` — Test files mirroring src/ structure

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
```

Examples:
- `feat(compiler): add multi-stack assembly`
- `fix(hooks): correct blocklist regex for Windows paths`
- `docs(stacks): update Python security standards`

## Adding a New Stack

1. Create a directory under `stacks/<stack-name>/`
2. Add these files: `standards.md`, `patterns.md`, `anti-patterns.md`, `testing.md`, `security.md`
3. Add the stack name to `src/utils/config.ts` Stack type
4. Add detection logic in `src/utils/detect.ts`
5. Update `schemas/config.schema.json`
6. Add tests in `test/`

## Adding a New IDE Target

1. Create `src/compiler/targets/<ide-name>.ts`
2. Create `templates/project/<ide-name>.hbs`
3. Add the IDE to `src/utils/config.ts` IDE type
4. Add detection logic in `src/utils/detect.ts`
5. Update `schemas/config.schema.json`
6. Add tests in `test/compiler/targets/`

## Testing

- Write tests for all new functionality
- Place tests in `test/` mirroring the `src/` structure
- Use fixtures in `test/fixtures/` for integration tests
- Aim for >80% coverage

## Code Standards

- TypeScript strict mode
- ESM modules (no CommonJS)
- Explicit return types on exported functions
- No `any` types
- Prefer `const` over `let`
- Use descriptive variable names
