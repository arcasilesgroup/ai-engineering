        <!-- source: java overrides v1 (spec-133 D-133-12) -->

        # Java — Build Conventions

        Authoritative reference for the `ai-build` agent when generating
        java code.

        ## Toolchain

        - **Build / dependency**: Maven (`pom.xml`) or Gradle (`build.gradle`/`build.gradle.kts`)
        - **Lint / format**: stack-canonical linter (see `tdd_harness.md`)
        - **Type checker**: enabled where the stack supports it

        ## Patterns

        - Use `Result<T>` patterns where idiomatic; exceptions for *exceptional* flow only.
- Spring beans: prefer constructor injection; never `@Autowired` field injection.
- Dependency: pin to specific versions; avoid version ranges.
