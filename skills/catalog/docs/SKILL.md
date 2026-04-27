---
name: docs
description: Use when documentation needs to be written, regenerated, or kept in sync — changelogs, release notes, API docs, migration guides. Trigger for "update changelog", "generate release notes", "regenerate API docs", "where are the docs". Has handlers for changelog, release-notes, api-docs.
effort: high
tier: core
capabilities: [tool_use]
handlers: [changelog, release-notes, api-docs]
---

# /ai-docs

Documentation authoring and synchronization. Three handlers:
**changelog** (release-please style), **release-notes** (human-readable),
**api-docs** (OpenAPI / typedoc auto-gen). Optional Mintlify portal sync.

## When to use

- PR adds a public API change → changelog handler
- Release tag cut → release-notes handler
- API surface or schema changed → api-docs handler
- "Where is X documented?" — find or stub
- Quarterly docs audit — coverage check

## Handlers

### changelog (release-please style)

1. Parse Conventional Commits since last release.
2. Group by `feat:`, `fix:`, `perf:`, `breaking change:`.
3. Update `CHANGELOG.md` under the next `## [Unreleased]` heading.
4. On release, promote `[Unreleased]` to `[<version>] - <date>`.
5. Validate semver bump matches commit types (breaking → major,
   feat → minor, fix → patch).

### release-notes

1. Read promoted CHANGELOG block.
2. Re-author for human audience: "what's new for users", "breaking
   changes you must act on", "credits".
3. Cross-reference to migration guide (if breaking).
4. Optionally publish to GitHub Release / Mintlify portal.

### api-docs

1. **OpenAPI** — regenerate from source; diff against previous version
   to surface unintentional breaking changes.
2. **typedoc** — for TS public APIs.
3. **`pdoc`** — for Python public APIs.
4. Push to docs site (`docs/api/`) and Mintlify if configured.
5. Validate examples are runnable (smoke-test code blocks).

## Process

1. **Detect change scope** — diff vs main; classify (internal /
   public API / breaking).
2. **Pick handler(s)** — multiple may run in parallel.
3. **Generate / update** docs artifacts.
4. **Validate** — link checker, code-block runner, schema validator.
5. **Open PR** if not already in one; tag `docs` label.
6. **Optional Mintlify sync** — push to portal under release tag.

## Hard rules

- NEVER hand-edit generated docs (typedoc, OpenAPI clients, etc.).
- NEVER ship a breaking change without a migration guide.
- CHANGELOG is the source of truth for release notes; never let them
  drift.
- Code blocks in docs must be executable / verifiable; broken
  examples are bug reports.
- Mintlify push is optional and gated on portal credential present.

## Common mistakes

- Letting CHANGELOG drift behind commits ("we'll catch up later")
- Treating release notes as identical to changelog (different audiences)
- Forgetting migration guides for breaking changes
- Hand-editing OpenAPI YAML instead of regenerating
- Broken code examples — runnable docs are testable docs
