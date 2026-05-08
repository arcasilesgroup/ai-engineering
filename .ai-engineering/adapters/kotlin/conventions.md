<!-- source: contexts/languages/kotlin.md @ affdef6d3235a65039813845a467340fa4f70803 -->

# Kotlin — Build Conventions

Authoritative reference for the `ai-build` agent when generating
Kotlin code. Distilled from `contexts/languages/kotlin.md` plus
`contexts/frameworks/android.md`.

## Toolchain

- **Kotlin version**: 2.0+. Pin in `gradle/libs.versions.toml`.
- **JVM target**: 17 (or 21 once stable across the build chain).
- **Build**: Gradle Kotlin DSL (`build.gradle.kts`); never legacy
  Groovy build files in new repos.
- **Linter**: `ktlint` for style; `detekt` for code quality.
- **Formatter**: `ktlintFormat` (Gradle task) — verified in CI with
  `ktlintCheck`.

## Project layout (Android)

```
settings.gradle.kts
build.gradle.kts
gradle/libs.versions.toml
app/
  build.gradle.kts
  src/main/kotlin/com/example/markets/...
  src/test/kotlin/com/example/markets/...
  src/androidTest/kotlin/com/example/markets/...
```

- One Gradle module per logical unit. Domain modules are pure-Kotlin
  (no Android dependencies).
- Version catalogue in `libs.versions.toml` so plugin / library
  versions are managed centrally.

## Naming

| Element | Convention | Example |
|---|---|---|
| Packages | lowercase | `com.example.markets` |
| Classes / interfaces / objects | UpperCamelCase | `MarketRepository` |
| Functions / properties / parameters | lowerCamelCase | `fetchMarket` |
| Constants (top-level / companion) | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Type parameters | single uppercase letter or descriptive | `T`, `Out` |

## Null safety

- Non-nullable by default. `?` only when the value can legitimately
  be absent.
- `!!` (force unwrap) is forbidden in new code; allowed with a
  justifying comment.
- Use `?.let { ... }`, `?:` (Elvis), and safe casts (`as?`).

## Data classes

- `data class` for immutable models — auto-generated `equals`,
  `hashCode`, `toString`, `copy`, destructuring.
- Properties are `val` by default; `var` only when mutation is
  intentional.

## Sealed classes & enums

- `sealed class` (or `sealed interface` in Kotlin 1.5+) for state
  machines. Pair with `when` expressions for exhaustive checks.
- `enum class` for closed sets of constants without payload.

## Coroutines

- `suspend` functions for async operations.
- `viewModelScope.launch` / `lifecycleScope.launch` in Android.
- `withContext(Dispatchers.IO)` to switch dispatchers; never block
  the main thread.
- Structured concurrency: every `launch` / `async` is bound to a
  scope that owns its lifecycle.

## Extension functions

- Use to extend types you don't own (stdlib, Android SDK).
- Don't shadow members; the compiler resolves to members first.
- Keep extensions in a `<Type>Ext.kt` file or in the consumer's
  package, not scattered.

## Quality gate (pre-commit)

1. `./gradlew ktlintCheck`
2. `./gradlew detekt`
3. `./gradlew test` — see `tdd_harness.md`
4. `./gradlew dependencyCheckAnalyze` (OWASP) in CI
