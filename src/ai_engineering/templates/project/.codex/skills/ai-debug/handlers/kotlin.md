# Handler: Kotlin Build Resolver

## Purpose

Resolves Kotlin compilation errors, Gradle build failures, and static analysis warnings from detekt and ktlint. Covers the full diagnostic chain from `./gradlew build` through dependency resolution, annotation processing (kapt/KSP), and Kotlin-specific language errors including coroutine misuse, smart cast failures, and sealed class exhaustiveness. Targets Kotlin 1.9+ with Gradle as the build system.

## Activation

Activate this handler when:

- The project contains `build.gradle.kts` or `build.gradle` with Kotlin plugins
- Source files have the `.kt` or `.kts` extension
- Build errors reference Kotlin compiler messages (e.g., `Smart cast to X is impossible`, `Unresolved reference`)
- The user reports issues with `./gradlew build`, `./gradlew compileKotlin`, or IntelliJ build

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Gradle wrapper and Kotlin version
./gradlew --version
./gradlew kotlinCompilerVersion 2>/dev/null || echo "Check build.gradle.kts for kotlin version"

# 2. Clean build artifacts (resolves stale class file issues)
./gradlew clean

# 3. Compile all source sets
./gradlew compileKotlin compileTestKotlin 2>&1

# 4. Full build with tests
./gradlew build 2>&1

# 5. Run detekt static analysis (if configured)
./gradlew detekt 2>&1

# 6. Run ktlint format check (if configured)
./gradlew ktlintCheck 2>&1

# 7. Check dependency tree for conflicts
./gradlew dependencies --configuration compileClasspath 2>&1

# 8. Run tests with full stack traces
./gradlew test --stacktrace 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `Smart cast to X is impossible because Y is a mutable property` | A `var` property could be changed between the null check and its use, so the compiler cannot guarantee the smart cast is safe. | Use `val` instead of `var`, or use `let` scope function: `y?.let { /* use it */ }`. Alternatively, capture in a local `val`: `val local = y ?: return`. |
| `'when' expression must be exhaustive` | A `when` expression on a sealed class/interface or enum does not cover all possible subtypes or values. | Add the missing branches. For sealed classes, add a branch for each subtype. Avoid `else` on sealed types to preserve compile-time exhaustiveness checking. |
| `Suspend function X should be called only from a coroutine or another suspend function` | A `suspend` function is called from a non-suspend context (regular function, callback, or Java interop). | Wrap the call in a coroutine builder: `runBlocking {}` (blocking), `launch {}` or `async {}` (non-blocking). For Android, use `viewModelScope.launch {}` or `lifecycleScope.launch {}`. |
| `Unresolved reference: X` | Symbol `X` is not found. Missing import, dependency not declared, or typo. | Add the import statement. Verify the dependency is in `build.gradle.kts`. Check spelling and package path. Run `./gradlew dependencies` to verify resolution. |
| `Type mismatch: inferred type is X but Y was expected` | Return type, assignment, or argument does not match the declared type. | Cast explicitly (`as Y`), convert (`.toY()`), or change the declaration. For nullability: use `!!` only with invariant proof, prefer `?:` or `?.let`. |
| `Overload resolution ambiguity` | Multiple functions match the call signature and the compiler cannot choose. | Add explicit type arguments, use named parameters, or cast the argument to disambiguate. |
| `Platform declaration clash` | Two declarations map to the same JVM signature (e.g., `fun getX()` and `val x` both produce `getX()`). | Use `@JvmName("alternativeName")` to change the JVM name of one declaration. |
| `Cannot access X: it is private/internal in Y` | Visibility modifier prevents access to the member from the current scope. | Change the visibility of the target member if appropriate, or access through a public API. For `internal`, ensure the caller is in the same module. |
| `None of the following functions can be called with the arguments supplied` | No overload matches the given argument types or count. | Check the function signature. Verify argument types, order, and nullability. Use named arguments for clarity. |
| `Conflicting declarations` | Two declarations with the same name in the same scope. | Rename one of the conflicting declarations, or move one to a different package. |
| `Classifier X does not have a companion object` | Calling a static-like member on a class that has no `companion object`. | Add a `companion object` block to the class, or change the call to use an instance. |
| `Val cannot be reassigned` | Attempting to assign a new value to a `val` (immutable) property. | Change to `var` if mutation is intended, or restructure to compute the value once. |

## Gradle Troubleshooting

```bash
# Show the full dependency tree for the compile classpath
./gradlew dependencies --configuration compileClasspath

# Show dependency insight for a specific library
./gradlew dependencyInsight --dependency library-name --configuration compileClasspath

# Force refresh of cached dependencies
./gradlew build --refresh-dependencies

# Run with debug logging for detailed failure info
./gradlew build --debug 2>&1 | tail -100

# Show the Gradle build scan (requires plugin)
./gradlew build --scan

# List all available tasks
./gradlew tasks --all

# Check for dependency version conflicts
./gradlew buildEnvironment

# Verify Gradle wrapper integrity
./gradlew wrapper --gradle-version=8.5 --distribution-type=all

# Clear Gradle caches (last resort)
rm -rf ~/.gradle/caches/
rm -rf .gradle/
./gradlew clean build
```

## Annotation Processing Troubleshooting

```bash
# For kapt issues (Dagger, Room, Moshi, etc.)
./gradlew kaptGenerateStubsKotlin 2>&1
./gradlew kaptKotlin 2>&1

# For KSP issues (newer annotation processors)
./gradlew kspKotlin 2>&1

# Verify generated sources exist
find build/generated -name "*.kt" -o -name "*.java" | head -20

# Common kapt fix: rebuild generated sources
./gradlew clean kaptKotlin

# Check kapt configuration
./gradlew dependencies --configuration kapt
```

## Compiler Flags Section

```kotlin
// build.gradle.kts -- useful compiler flags for debugging

kotlin {
    compilerOptions {
        // Treat all warnings as errors
        allWarningsAsErrors.set(true)

        // Enable progressive mode (latest language features)
        progressiveMode.set(true)

        // Opt-in to experimental APIs
        optIn.addAll(
            "kotlin.RequiresOptIn",
            "kotlinx.coroutines.ExperimentalCoroutinesApi"
        )

        // JVM target
        jvmTarget.set(JvmTarget.JVM_17)

        // Enable verbose compiler output for debugging
        freeCompilerArgs.addAll(
            "-Xverbose",
            "-Xprint-reified-type-parameters"
        )
    }
}
```

```bash
# Run compiler with verbose output
./gradlew compileKotlin -Pkotlin.compiler.execution.strategy=in-process --info 2>&1

# Check which Kotlin compiler version is used
./gradlew compileKotlin --info 2>&1 | grep "Kotlin Compiler version"

# Dump compiler IR (advanced debugging)
./gradlew compileKotlin -Pkotlin.compiler.args="-Xdump-ir" 2>&1
```

## Hard Rules

- **NEVER** add `@Suppress("UNCHECKED_CAST")` or `@Suppress("DEPRECATION")` to bypass warnings. Fix the type safety issue or migrate off the deprecated API.
- **NEVER** use `!!` (non-null assertion) without proving the invariant in a comment. Prefer `?.`, `?:`, or `requireNotNull()` with a message.
- **NEVER** add `@file:Suppress("detekt:...")` or `@Suppress("ktlint:...")` to silence static analysis. Fix the code.
- **NEVER** use `runBlocking` in production Android code (causes ANR). Use structured concurrency with appropriate scope.
- **ALWAYS** use sealed classes/interfaces with exhaustive `when` (no `else` branch) for type-safe dispatch.
- **ALWAYS** run `./gradlew detekt ktlintCheck` after fixes when these tools are configured.
- **ALWAYS** verify that annotation processors (kapt/KSP) regenerate correctly after code changes.

## Stop Conditions

- The error is caused by a Gradle plugin version incompatibility that requires upgrading the build system. Escalate with the plugin name and version conflict.
- The error involves kapt/KSP annotation processing failures in generated code that the team does not control. Document the annotation processor and escalate.
- Two fix attempts have failed for the same error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | ./gradlew build | ./gradlew detekt | ./gradlew test
```
