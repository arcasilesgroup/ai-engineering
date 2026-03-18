# Framework Ruby Stack Standards

## Update Metadata

- Rationale: establish Ruby patterns for web applications, APIs, and automation scripts.
- Expected gain: consistent Ruby code quality, dependency management, and testing standards.
- Potential impact: Ruby projects get enforceable lint, security, and testing patterns.

## Stack Scope

- Primary language: Ruby 3.2+.
- Supporting formats: YAML, JSON, ERB, Markdown.
- Toolchain baseline: `rbenv` or `asdf`, Bundler, RubyGems.
- Distribution: gem, container image, PaaS deployment.

## Required Tooling

- Package: Bundler (`bundle install`, `bundle exec`).
- Lint/format: `rubocop` (configured via `.rubocop.yml`).
- Type checking: `sorbet` (optional, for typed codebases).
- Test runner: RSpec (preferred) or Minitest.
- Dependency vulnerability scan: `bundler-audit`, `trivy`.
- Security SAST: `brakeman` (Rails), `semgrep`, `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `rubocop --check`, `gitleaks`.
- Pre-push: `semgrep`, `bundler-audit`, `rspec`, `brakeman` (if Rails).

## Quality Baseline

- All public methods documented with YARD doc comments.
- Test coverage target: per `standards/framework/quality/core.md`.
- RuboCop warnings treated as errors in CI.
- No `eval` or `send` with user input.

## Code Patterns

- **Error handling**: custom exception classes inheriting from `StandardError`. Rescue specific exceptions.
- **Framework**: Rails (API-mode for services), Sinatra/Roda for lightweight apps.
- **Serialization**: `ActiveModel::Serializers` or `jsonapi-serializer`.
- **Background jobs**: Sidekiq with Redis. Idempotent job design.
- **Logging**: `Rails.logger` or Ruby `Logger`. Structured JSON in production.
- **Small focused methods**: <30 lines, single responsibility.
- **Project layout**: Rails conventions (`app/`, `lib/`, `spec/`).

## Testing Patterns

- Unit tests: RSpec with `describe`/`context`/`it` structure.
- Integration tests: request specs (`spec/requests/`).
- Factory: `factory_bot` for test data.
- Naming: `it "does X when Y"` — behavior-driven style.
- Mocking: `rspec-mocks`, `webmock` for HTTP.

## Update Contract

This file is framework-managed and may be updated by framework releases.
