# Framework Java/Kotlin Stack Standards

## Update Metadata

- Rationale: establish Java and Kotlin patterns for backend services, Android apps, and enterprise systems.
- Expected gain: consistent JVM code quality, dependency management, and testing standards.
- Potential impact: JVM projects get enforceable build, lint, and security patterns.

## Stack Scope

- Primary languages: Java 21+ (LTS), Kotlin 2.0+.
- Supporting formats: YAML, JSON, XML, Markdown.
- Toolchain baseline: Gradle (preferred) or Maven, JDK via SDKMAN.
- Distribution: JAR, container image, native image (GraalVM).

## Required Tooling

- Build: Gradle 8+ (Kotlin DSL preferred) or Maven 3.9+.
- Lint: `checkstyle` (Java), `detekt` (Kotlin), `ktlint` (Kotlin formatting).
- Format: `google-java-format` (Java), `ktlint --format` (Kotlin).
- Type checking: built-in (compiler). Kotlin null-safety by default.
- Test runner: JUnit 5 + Gradle Test.
- Dependency vulnerability scan: `dependency-check` (OWASP), `trivy`.
- Security SAST: `semgrep` (Java/Kotlin rules), `gitleaks` (secret detection).

## Minimum Gate Set

- Pre-commit: format check, lint check, `gitleaks`.
- Pre-push: `semgrep`, dependency-check, `./gradlew test`, `./gradlew build`.

## Quality Baseline

- All public APIs documented with Javadoc (Java) or KDoc (Kotlin).
- Test coverage target: per `standards/framework/quality/core.md`.
- Null-safety: prefer Kotlin; in Java use `@Nullable`/`@NonNull` annotations.
- No suppression annotations (`@SuppressWarnings`) without documented justification.

## Code Patterns

- **Error handling**: custom exception hierarchies extending `RuntimeException`. Kotlin `Result<T>` for functional error handling.
- **Dependency injection**: Spring Boot (preferred) or Dagger/Hilt (Android).
- **Serialization**: Jackson (JSON), kotlinx.serialization (Kotlin multiplatform).
- **HTTP**: Spring WebFlux or Spring MVC. Ktor for Kotlin-native services.
- **Logging**: SLF4J + Logback. Structured JSON logging in production.
- **Concurrency**: Kotlin coroutines (preferred), Java virtual threads (Java 21+).
- **Small focused methods**: <50 lines, single responsibility.
- **Project layout**: standard Gradle/Maven directory structure (`src/main/java`, `src/test/java`).

## Testing Patterns

- Unit tests: JUnit 5, `@Test` annotation. Kotlin: `kotest` as alternative.
- Integration tests: `@SpringBootTest` for Spring, `testcontainers` for dependencies.
- Mocking: Mockito (Java), MockK (Kotlin).
- Naming: `test_<unit>_<scenario>_<expected>` or `should <behavior> when <condition>`.
- AAA pattern: Arrange-Act-Assert. One assertion per test method when practical.

## Update Contract

This file is framework-managed and may be updated by framework releases.
