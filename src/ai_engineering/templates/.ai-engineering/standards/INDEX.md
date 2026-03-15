# Standards Index

## Framework Standards

### Core

| Standard | Path | Description |
|----------|------|-------------|
| Core | `framework/core.md` | Governance non-negotiables, lifecycle, ownership |
| Skills Schema | `framework/skills-schema.md` | Skill file structure and validation rules |

### Quality & Security

| Standard | Path | Description |
|----------|------|-------------|
| Quality Core | `framework/quality/core.md` | Coverage, complexity, duplication thresholds |
| SonarLint | `framework/quality/sonarlint.md` | SonarLint IDE integration patterns |
| OWASP Top 10 | `framework/security/owasp-top10-2025.md` | OWASP 2025 security standard |
| CI/CD Core | `framework/cicd/core.md` | CI/CD pipeline standards |

### Stack Standards (21)

| Standard | Path | Languages/Tools |
|----------|------|-----------------|
| Python | `framework/stacks/python.md` | Python 3.11+, uv, ruff, ty |
| TypeScript | `framework/stacks/typescript.md` | TypeScript, ESLint, Prettier |
| .NET | `framework/stacks/dotnet.md` | C#, .NET 8+, dotnet CLI |
| Rust | `framework/stacks/rust.md` | Rust, cargo, clippy, rustfmt |
| Java/Kotlin | `framework/stacks/java-kotlin.md` | Java 21+, Kotlin 2.0+, Gradle |
| Swift | `framework/stacks/swift.md` | Swift 5.9+, Xcode, SPM |
| Ruby | `framework/stacks/ruby.md` | Ruby 3.2+, Bundler, RuboCop |
| PHP | `framework/stacks/php.md` | PHP 8.2+, Composer, PHPStan |
| C/C++ | `framework/stacks/c-cpp.md` | C17, C++20, CMake, clang-tidy |
| Node | `framework/stacks/node.md` | Node.js, npm/pnpm |
| React | `framework/stacks/react.md` | React, JSX/TSX |
| Next.js | `framework/stacks/nextjs.md` | Next.js, App Router |
| NestJS | `framework/stacks/nestjs.md` | NestJS, TypeORM |
| React Native | `framework/stacks/react-native.md` | React Native, Expo |
| Astro | `framework/stacks/astro.md` | Astro, content collections |
| Azure | `framework/stacks/azure.md` | Azure services, Bicep |
| Infrastructure | `framework/stacks/infrastructure.md` | Terraform, Pulumi, Docker, K8s |
| Database | `framework/stacks/database.md` | SQL, PostgreSQL, migrations |
| Bash/PowerShell | `framework/stacks/bash-powershell.md` | Shell scripting |
| Helm | `framework/stacks/helm.md` | Helm 3, Kubernetes charts |
| Ansible | `framework/stacks/ansible.md` | Ansible, playbooks, roles |

### Cross-Cutting Standards (8)

| Standard | Path | Description |
|----------|------|-------------|
| Error Handling | `framework/cross-cutting/error-handling.md` | Error types, boundaries, retry patterns |
| Logging | `framework/cross-cutting/logging.md` | Structured logging, levels, correlation |
| Configuration | `framework/cross-cutting/configuration.md` | 12-factor config, secrets separation |
| Observability | `framework/cross-cutting/observability.md` | Logs, metrics, traces, SLIs/SLOs |
| Testing | `framework/cross-cutting/testing.md` | Test pyramid, tiers, quality thresholds |
| API Design | `framework/cross-cutting/api-design.md` | REST, GraphQL, gRPC patterns |
| Dependency Management | `framework/cross-cutting/dependency-management.md` | Lock files, auditing, SBOM |
| Documentation | `framework/cross-cutting/documentation.md` | Divio system, code docs, ADRs |

## Team Standards

| Standard | Path | Description |
|----------|------|-------------|
| Team Core | `team/core.md` | Team-specific overrides and extensions |
| Team Python | `team/stacks/python.md` | Team Python stack customizations |

## Totals

- **Framework core**: 2
- **Quality & Security**: 4
- **Stack standards**: 21
- **Cross-cutting standards**: 8
- **Team standards**: 2
- **Total**: 37
