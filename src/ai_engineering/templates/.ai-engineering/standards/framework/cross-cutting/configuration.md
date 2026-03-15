# Cross-Cutting Standard: Configuration

## Scope

Applies to all stacks. Governs how applications consume configuration and manage environment-specific settings.

## Principles

1. **12-Factor Config**: configuration lives in the environment, not in code.
2. **Layered precedence**: defaults < config files < environment variables < CLI flags.
3. **Typed access**: parse configuration into typed structures at startup, not stringly-typed lookups at usage sites.
4. **Fail-fast validation**: validate all required configuration at startup. Don't discover missing config at runtime.
5. **Secrets separation**: secrets are never in config files. Use secret managers (Key Vault, Secrets Manager, Vault).

## Patterns

- **Config schema**: define a schema/model for all configuration (Pydantic, Zod, struct, interface).
- **Defaults**: every optional config key has a sensible default documented alongside its declaration.
- **Environment mapping**: `APP_DATABASE_URL` → `database.url`. Consistent prefix per application.
- **Feature flags**: boolean flags with defaults. Managed via config, not code branches.
- **Config documentation**: all configuration keys documented with type, default, description, and example.

## Anti-patterns

- Hardcoded values that should be configurable.
- Reading environment variables deep in business logic instead of at the configuration boundary.
- Mixing secrets with non-secret configuration in the same file/source.
- Config files committed to version control that contain environment-specific values.
- No validation — silently using wrong config until runtime failure.

## Update Contract

This file is framework-managed and may be updated by framework releases.
