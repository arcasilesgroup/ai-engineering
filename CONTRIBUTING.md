# Contributing to ai-engineering

Thank you for considering a contribution. This document captures the
non-negotiable practices and the friction-free workflow.

## Code of Conduct

By participating you agree to abide by [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

## Discipline (non-negotiable)

1. **TDD** — every domain change starts with a failing test. Pull
   requests with new code and zero tests will be asked to add them.
2. **SDD** — non-trivial features start with a spec under
   `.ai-engineering/specs/`. Use `/ai-specify` if you have the framework
   installed; otherwise hand-author against the schema.
3. **Hexagonal** — domain code does not import `node:fs`, `bun:*`,
   `node:net`. All I/O goes through a port.
4. **Conventional Commits** — `feat`, `fix`, `chore`, `docs`, `test`,
   `refactor`, `perf`, `build`, `ci`. Subject in imperative mood.
5. **No `--no-verify`** — git hooks run for a reason. If a hook is
   wrong, fix the hook.
6. **No suppression comments** (`# noqa`, `# nosec`, `// nolint`,
   `// @ts-ignore`) without an open issue justifying the exception.

## Branching

- `main` is always green and shippable.
- Feature branches: `feat/<scope>-<short-description>`.
- Fix branches: `fix/<scope>-<short-description>`.
- Spec-driven: `feat/spec-NNN-<slug>` to keep the spec id traceable.

## Workflow

1. Open or claim an issue (good first issues are labeled).
2. Branch from `main`.
3. Write the failing test. Confirm it fails for the right reason.
4. Implement the minimum to make it pass. Refactor with all tests
   still green.
5. Run `bun run lint && bun run typecheck && bun test` and `uv run
   pytest python/`.
6. Push. CI runs the matrix.
7. Open a PR with the [PR template](./.github/PULL_REQUEST_TEMPLATE.md)
   filled in.

## Code style

- TypeScript: Biome handles format + lint. `bun run lint:fix`.
- Python: ruff handles format + lint. `uvx ruff format` and `uvx ruff
  check --fix`.
- No emojis in code or comments unless the test asserts on the literal.
- No comments restating what the code does. Comments explain *why* —
  the non-obvious constraint, the workaround source, the historical
  decision.

## Adding a new skill

1. Create `skills/catalog/<name>/SKILL.md` with the frontmatter schema
   from `docs/skill-spec.md` (or copy an existing skill).
2. Add an eval golden set under `tests/evals/<name>/`.
3. Run `ai-eng skill audit <name>` (CLI command lands in Phase 4 — for
   now, manually verify the YAML frontmatter validates against the
   JSON schema in `shared/schemas/skill.schema.json`).

## Adding an agent

Agents live in `agents/<name>/AGENT.md` with explicit tool restrictions.
Only the `builder` agent has write permissions — see [ADR-0001](./docs/adr/0001-hexagonal-architecture.md).

## Adding a plugin

Read [ADR-0006](./docs/adr/0006-plugin-3-tier-distribution.md). Plugin
authors:

- COMMUNITY tier: any GitHub repo with the `ai-engineering-plugin`
  topic, valid `.ai-engineering/plugin.toml`, signed releases.
- VERIFIED tier: open a PR to the registry repo. Bots verify Sigstore
  + SLSA + SBOM + Scorecard. Humans review SECURITY.md, hook usage,
  and `network: true` justifications.

## Decisions that need an ADR

If your PR changes a framework-level choice (architecture, security,
naming, distribution), open a new ADR under `docs/adr/`. Use existing
ADRs as templates.

## Help

- Architecture questions: open a `discussion`, not an issue.
- Bugs: please reproduce first; describe expected vs actual.
- Security: see [SECURITY.md](./SECURITY.md). Do not open public issues.
