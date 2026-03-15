# Framework PHP Stack Standards

## Update Metadata

- Rationale: establish PHP patterns for web applications, APIs, and CMS platforms.
- Expected gain: consistent PHP code quality, dependency management, and testing standards.
- Potential impact: PHP projects get enforceable PSR compliance, security, and testing patterns.

## Stack Scope

- Primary language: PHP 8.2+.
- Supporting formats: JSON, YAML, Markdown, Twig/Blade templates.
- Toolchain baseline: Composer, PHP built-in server (dev), PHP-FPM (prod).
- Distribution: container image, PaaS deployment, shared hosting.

## Required Tooling

- Package: Composer (`composer install`, `composer update`).
- Lint: `phpstan` (level 8+), `psalm`.
- Format: `php-cs-fixer` (PSR-12 ruleset).
- Test runner: PHPUnit 10+.
- Dependency vulnerability scan: `composer audit`, `trivy`.
- Security SAST: `semgrep`, `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: `php-cs-fixer fix --dry-run`, `phpstan analyse`, `gitleaks`.
- Pre-push: `semgrep`, `composer audit`, `phpunit`.

## Quality Baseline

- PSR-12 coding standard enforced.
- All public methods documented with PHPDoc.
- Test coverage target: per `standards/framework/quality/core.md`.
- Strict types declared: `declare(strict_types=1)` in every file.
- No suppression annotations without documented justification.

## Code Patterns

- **Error handling**: custom exception classes. Use typed exceptions, not generic `\Exception`.
- **Framework**: Laravel (preferred) or Symfony. Use framework conventions.
- **Serialization**: Laravel Resources or Symfony Serializer.
- **Queue**: Laravel Queue with Redis/SQS. Idempotent job design.
- **Logging**: Monolog via framework. Structured JSON in production.
- **Typed properties**: use typed properties and return types everywhere.
- **Small focused methods**: <50 lines, single responsibility.
- **Project layout**: PSR-4 autoloading, `src/`, `tests/`.

## Testing Patterns

- Unit tests: PHPUnit with `@test` or `test_` prefix.
- Feature tests: HTTP tests via framework test client.
- Factory: model factories for test data.
- Naming: `test_<unit>_<scenario>_<expected>`.
- Mocking: PHPUnit mocks, Mockery for complex cases.

## Update Contract

This file is framework-managed and may be updated by framework releases.
