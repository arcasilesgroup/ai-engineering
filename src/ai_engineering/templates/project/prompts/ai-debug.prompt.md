---
name: ai-debug
description: "Use when investigating unexpected behavior, test failures, runtime errors, or regressions. Systematic 4-phase diagnosis: symptom analysis, reproduction, root cause, solution."
effort: max
argument-hint: "[error description or file:line]"
mode: agent
---



# Debug

## Purpose

Systematic debugging skill. Four phases, always in order. NEVER fix symptoms -- always find and fix the root cause. After 2 failed fix attempts, escalate to the user.

## When to Use

- Test failures (expected vs actual mismatch)
- Runtime errors (exceptions, crashes, hangs)
- Regressions (worked before, broken now)
- Unexpected behavior (no error, but wrong result)

## Process

### Phase 1: Symptom Analysis (WHAT, WHEN, WHERE)

Gather facts before forming hypotheses:

1. **WHAT**: exact error message, stack trace, log output
2. **WHEN**: always? intermittent? after a specific change? under load?
3. **WHERE**: which file, function, line? which test? which environment?
4. **SINCE WHEN**: `git log --oneline -20` -- what changed recently?

Output: symptom report with all facts classified as KNOWN or SUSPECTED.

### Phase 2: Reproduction (MINIMAL REPRO)

Make the bug reproducible with the smallest possible case:

1. Run the failing test or reproduce the error
2. If not reproducible: document exact conditions and STOP (cannot debug what cannot be reproduced)
3. Strip to minimal repro: remove unrelated code, simplify inputs, isolate the component
4. Confirm: the minimal repro fails consistently

Output: exact command to reproduce the failure.

### Phase 3: Root Cause (WHY)

Apply the 5 Whys to move from symptom to cause:

1. **Why** does it fail? -> [immediate cause]
2. **Why** does that happen? -> [deeper cause]
3. **Why** does that happen? -> [root cause]
   (Continue until you reach a cause you can fix directly)

**Techniques** (use as appropriate):
- **Binary search**: comment out code, add assertions to narrow the location
- **Git bisect**: `git bisect start HEAD <known-good>` to find the breaking commit
- **Print tracing**: add targeted print/log statements at decision points
- **Diff analysis**: `git diff <known-good>..HEAD -- <file>` to see what changed
- **Assumption check**: list every assumption the code makes, verify each one

**Classification**: identify the root cause category:
- Logic error (wrong condition, off-by-one, missing case)
- State corruption (mutation, shared state, race condition)
- Contract violation (caller sends wrong type, missing field)
- Environment (missing dependency, wrong version, config)
- Data (unexpected input, encoding, edge case)

Output: root cause statement (1-2 sentences, specific and testable).

### Phase 4: Solution Design (FIX + REGRESSION TEST)

1. **Design the fix**: minimal change that addresses the root cause
   - Fix the ROOT CAUSE, not the symptom
   - One logical change only
   - If the fix is large, the root cause analysis may be wrong -- revisit Phase 3
2. **Write regression test**: a test that fails without the fix and passes with it
3. **Apply the fix**
4. **Verify**: regression test passes AND all existing tests pass
5. **Check for siblings**: does the same bug pattern exist elsewhere? (`grep` for similar code)

## Escalation Protocol

| Attempt | Action |
|---------|--------|
| 1st fix fails | Try a different approach (not the same thing again) |
| 2nd fix fails | STOP. Escalate to user with: symptom, repro, root cause analysis, 2 approaches tried |

Never retry the same approach. Never loop silently.

## 5 Whys Example

```
Symptom: test_parse_config_handles_empty fails with KeyError
Why 1: config["database"] raises KeyError
Why 2: parse_config returns empty dict when file is empty
Why 3: the YAML parser returns None for empty files, not empty dict
Root cause: missing None -> {} coercion after yaml.safe_load()
Fix: add `config = yaml.safe_load(f) or {}` instead of `config = yaml.safe_load(f)`
```

## Common Mistakes

- Fixing the symptom (add a try/except) instead of the root cause
- Not writing a regression test for the fix
- Guessing without reproducing first
- Changing multiple things at once (change one thing, verify, repeat)
- Retrying the same approach that already failed
- Not checking for sibling bugs (same pattern elsewhere)

## Integration

- **Called by**: `/ai-dispatch` (debug tasks), `ai-build agent` (when tests fail), user directly
- **Calls**: test runners (to reproduce), `/ai-test` (regression test)
- **Transitions to**: `ai-build` (fix implementation), `/ai-commit` (after verified fix)

$ARGUMENTS

---

# Handler: C++ Build Resolver

## Purpose

Resolves C++ compilation errors, linker failures, and static analysis warnings across CMake-based projects. Covers the full diagnostic chain from `cmake --build` through `clang-tidy` and `cppcheck`, including template instantiation errors, linker symbol resolution, and CMake configuration issues. Targets C++17 and later with CMake 3.20+ as the build system.

## Activation

Activate this handler when:

- The project contains `CMakeLists.txt` at the repository root or in the target directory
- Source files have `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, or `.hxx` extensions
- Build errors reference compiler messages from `g++`, `clang++`, or `cl.exe`
- The user reports issues with `cmake --build`, `make`, or `ninja`

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify compiler and CMake versions
cmake --version
g++ --version 2>/dev/null || clang++ --version 2>/dev/null

# 2. Configure the project (generate build system)
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON 2>&1

# 3. Build all targets
cmake --build build 2>&1

# 4. Run clang-tidy on changed files (requires compile_commands.json)
if [ -f "build/compile_commands.json" ]; then
    clang-tidy -p build src/*.cpp 2>&1
fi

# 5. Run cppcheck for additional static analysis
cppcheck --enable=all --suppress=missingInclude --project=build/compile_commands.json 2>&1

# 6. Run tests (if CTest is configured)
cd build && ctest --output-on-failure 2>&1

# 7. For verbose build output (shows exact compiler commands)
cmake --build build --verbose 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined reference to 'X'` | The symbol `X` is declared (header) but not defined (source), or the object file / library containing the definition is not linked. | Verify the source file with the definition is included in the CMake target. Add `target_link_libraries()` for external libraries. Check for missing `extern` or mismatched function signatures. |
| `multiple definition of 'X'` | The symbol `X` is defined in more than one translation unit, usually because a function or variable is defined in a header without `inline` or `static`. | Add `inline` to function definitions in headers. Use `static` for file-local variables in headers. Move definitions to a `.cpp` file and keep only declarations in the header. |
| `incomplete type 'X'` | Using a forward-declared type in a context that requires the full definition (sizeof, member access, inheritance). | Include the header that contains the full class definition. Check for circular includes. Use forward declarations only for pointers and references. |
| `no matching function for call to 'X'` | No overload of function `X` matches the argument types provided. | Check argument types, count, and const-qualification. Look for implicit conversion issues. Verify template argument deduction. |
| `template argument deduction/substitution failed` | The compiler cannot deduce template parameters from the function arguments, or substitution produces an invalid type. | Provide explicit template arguments: `func<Type>(args)`. Check that the argument types satisfy the template constraints. Verify SFINAE conditions. |
| `CMake Error at CMakeLists.txt:N` | CMake configuration error: missing package, wrong variable, syntax error. | Read the full error message. Common: `find_package(X REQUIRED)` fails because `X` is not installed. Install the dependency or set `X_DIR` to its location. |
| `expected ';' before 'X'` | Syntax error, usually a missing semicolon after a class definition, missing closing brace, or wrong include order. | Check the line above the error for a missing semicolon. Verify class definitions end with `};`. Check for macro expansion issues. |
| `use of undeclared identifier 'X'` | Variable or function `X` is not declared in the current scope. Missing include, namespace, or typo. | Add the correct `#include`. Use the full namespace path or add a `using` declaration. Check spelling. |
| `cannot convert 'X' to 'Y'` | Implicit conversion between incompatible types. | Use explicit casts (`static_cast<Y>(x)`) only if semantically correct. For smart pointers, use `std::dynamic_pointer_cast` or `std::static_pointer_cast`. |
| `redefinition of 'X'` | A class, struct, or function is defined more than once in the same translation unit. | Add `#pragma once` or include guards (`#ifndef X_H / #define X_H / #endif`) to all headers. |
| `'X' is not a member of 'std'` | Using a standard library feature without the correct include or with the wrong C++ standard version. | Add the required `#include` (e.g., `<string>`, `<vector>`, `<algorithm>`). Verify the C++ standard is set correctly (`CMAKE_CXX_STANDARD`). |
| `static assertion failed` | A `static_assert` condition evaluated to false at compile time. | Read the assertion message. Fix the type or value that violates the compile-time check. |
| `'X' was not declared in this scope` | The name `X` is not visible in the current scope. Common with templates in dependent base classes. | For dependent names in templates, use `this->X` or `Base::X`. For other cases, check includes and namespace scope. |
| `ld: library not found for -lX` | The linker cannot find library `X`. Not installed or not on the library search path. | Install the library. Add its path with `link_directories()` or set `CMAKE_PREFIX_PATH`. Use `find_library()` in CMake. |

## CMake Troubleshooting

```bash
# Show all CMake variables
cmake -B build -LA 2>&1

# Show CMake cache variables with help strings
cmake -B build -LAH 2>&1 | grep -A1 "CMAKE_CXX"

# Set the C++ standard explicitly
cmake -B build -DCMAKE_CXX_STANDARD=20 -DCMAKE_CXX_STANDARD_REQUIRED=ON

# Specify the compiler explicitly
cmake -B build -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang

# Enable verbose Makefile output
cmake -B build -DCMAKE_VERBOSE_MAKEFILE=ON

# Find where CMake looks for packages
cmake --system-information 2>&1 | grep CMAKE_PREFIX_PATH

# Debug find_package failures
cmake -B build -DCMAKE_FIND_DEBUG_MODE=ON 2>&1

# List all targets in the project
cmake --build build --target help

# Clean and reconfigure from scratch
rm -rf build/
cmake -B build -DCMAKE_BUILD_TYPE=Debug 2>&1

# Generate compile_commands.json for IDE and clang-tidy
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Check the effective compiler flags
cmake --build build --verbose 2>&1 | head -5
```

## Linker Troubleshooting

```bash
# List symbols in an object file
nm -C build/CMakeFiles/target.dir/src/file.cpp.o 2>/dev/null | head -20

# List symbols in a library
nm -C /path/to/library.a 2>/dev/null | head -20

# Check shared library dependencies
ldd build/target 2>/dev/null || otool -L build/target 2>/dev/null

# Find which library provides a symbol
# Linux:
nm -C /usr/lib/*.so 2>/dev/null | grep "symbol_name"
# macOS:
nm -C /usr/lib/*.dylib 2>/dev/null | grep "symbol_name"

# Verify the linker search path
ld --verbose 2>&1 | grep SEARCH_DIR | tr ';' '\n'

# Check for ODR violations (One Definition Rule)
# Build with sanitizers
cmake -B build -DCMAKE_CXX_FLAGS="-fsanitize=undefined" -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=undefined"
```

## Include and Dependency Troubleshooting

```bash
# Show the include search path
g++ -v -E - < /dev/null 2>&1 | grep "include"
# or
clang++ -v -E - < /dev/null 2>&1 | grep "include"

# Find a header file on the system
find /usr/include /usr/local/include -name "header.h" 2>/dev/null

# Show preprocessor output (resolve macro issues)
g++ -E -P src/file.cpp -I build/ 2>&1 | head -50

# Check which file includes what (dependency graph)
g++ -M src/file.cpp -I include/ 2>&1

# Install common dependencies (Ubuntu/Debian)
# apt-get install libboost-all-dev libssl-dev pkg-config

# Install common dependencies (macOS)
# brew install boost openssl pkg-config

# Use pkg-config to find library flags
pkg-config --cflags --libs openssl 2>/dev/null
```

## Hard Rules

- **NEVER** add `#pragma GCC diagnostic ignored` or `#pragma clang diagnostic ignored` to suppress warnings. Fix the code.
- **NEVER** use `reinterpret_cast` to bypass type errors. Use `static_cast` or `dynamic_cast` with proper error handling.
- **NEVER** use C-style casts `(Type)value` in C++ code. Use the appropriate C++ cast.
- **NEVER** disable compiler warnings with `-w` or `-Wno-*` flags to make the build pass. Fix the warnings.
- **NEVER** add `// NOLINT` or `// NOLINTNEXTLINE` comments to bypass clang-tidy. Fix the code.
- **ALWAYS** use `#pragma once` or include guards in all header files.
- **ALWAYS** set `CMAKE_CXX_STANDARD` explicitly in CMakeLists.txt rather than relying on compiler defaults.
- **ALWAYS** enable `-Wall -Wextra -Wpedantic` for all targets during development.
- **ALWAYS** generate `compile_commands.json` for tooling support.

## Stop Conditions

- The error requires installing system-level dependencies (libraries, toolchains) that the agent cannot install. Escalate with the exact package name and installation command.
- The error involves ABI incompatibility between libraries compiled with different compiler versions or flags. Document the mismatch and escalate.
- Two fix attempts have failed for the same error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | cmake --build build | clang-tidy | ctest
```

---

# Handler: Go Build Resolver

## Purpose

Resolves Go compilation errors, module dependency failures, and static analysis warnings. Covers the full diagnostic chain from `go build` through `go vet`, `staticcheck`, and `golangci-lint`, including module resolution with `go mod verify` and `go mod tidy`. Targets Go 1.21+ projects using Go modules.

## Activation

Activate this handler when:

- The project contains `go.mod` at the repository root or in the target directory
- Source files have the `.go` extension
- Build errors reference Go compiler messages (e.g., `cannot use`, `undefined`, `imported and not used`)
- The user reports issues with `go build`, `go test`, or `go run`

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Go installation and version
go version

# 2. Verify module integrity
go mod verify

# 3. Ensure dependencies are consistent
go mod tidy -diff   # Go 1.21+; shows what would change without modifying files

# 4. Compile all packages (fast feedback, no binary output)
go build ./...

# 5. Run the Go vet suite (catches suspicious constructs)
go vet ./...

# 6. Run staticcheck (if installed)
staticcheck ./...

# 7. Run golangci-lint (if installed and .golangci.yml exists)
golangci-lint run ./...

# 8. Run tests to confirm behavioral correctness
go test -count=1 -race ./...
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `undefined: X` | Symbol `X` not declared in the current package or not exported from the imported package. | Check spelling and capitalization. Exported symbols start with uppercase. Verify the correct package is imported. |
| `cannot use X (type T1) as type T2` | Type mismatch in assignment, function argument, or return value. | Cast explicitly if safe (`T2(X)`), or change the variable/parameter declaration to match. For interfaces, ensure `T1` implements `T2`. |
| `import cycle not allowed` | Package A imports B which imports A (directly or transitively). | Extract shared types into a third package that both can import. Use `go list -f '{{.Imports}}' ./pkg/...` to trace the cycle. |
| `cannot find package "X"` | Module not downloaded, wrong import path, or missing `go.mod` require. | Run `go mod tidy`. If the package is external, run `go get X@latest`. Verify the import path matches the module path exactly. |
| `X declared but not used` | Local variable or import is declared but never referenced. | Remove the unused variable or import. Use `_` for intentionally discarded values. For imports used only for side effects, use `import _ "pkg"`. |
| `multiple-value X() in single-value context` | Calling a function that returns (T, error) but only capturing one value. | Capture both values: `val, err := X()`. Handle the error explicitly. |
| `cannot use X (type T) as type S in map key` | Struct used as map key contains fields that are not comparable (slices, maps, functions). | Remove non-comparable fields from the key struct, or use a string/int derived key instead. |
| `invalid type assertion: X.(T)` | The interface value does not hold type T, or X is not an interface. | Use the comma-ok pattern: `v, ok := X.(T)`. Verify X is declared as an interface type. |
| `too many arguments in call to X` | Function called with more arguments than its signature accepts. | Check the function signature. Common cause: API changed in a dependency update. Run `go doc pkg.X`. |
| `cannot assign to X` | Attempting to assign to an unexported field, a map value field, or a constant. | For map struct values, assign the entire struct: `m[k] = newStruct`. For unexported fields, use the package's setter methods. |
| `missing return at end of function` | Not all code paths return a value in a function with a declared return type. | Add the missing return statement. Check that all branches of if/switch/select return. |
| `init function must have no arguments and no return values` | `init()` declared with parameters or return type. | Remove all parameters and return types from `func init()`. |

## Module Troubleshooting

```bash
# Why is a specific module required?
go mod why -m github.com/example/pkg

# Pin a dependency to a specific version
go get github.com/example/pkg@v1.2.3

# Replace a module with a local copy (development only)
# Add to go.mod: replace github.com/example/pkg => ../local-pkg

# Clear the module cache (last resort)
go clean -modcache

# List all direct and indirect dependencies
go list -m all

# Check for available updates
go list -m -u all

# Verify checksums match go.sum
go mod verify

# Download all dependencies without building
go mod download

# Visualize the dependency graph
go mod graph | head -30

# Find why a specific version was selected
go mod graph | grep "example/pkg"
```

## Build Cache Troubleshooting

```bash
# Clear the build cache (resolves stale object issues)
go clean -cache

# Clear test cache only
go clean -testcache

# Rebuild everything from scratch
go build -a ./...

# Check GOPATH and GOROOT
go env GOPATH GOROOT GOMODCACHE

# Verify CGO is configured correctly (if using C bindings)
go env CGO_ENABLED CC CXX
```

## Hard Rules

- **NEVER** add `//nolint` directives to suppress linter findings. Fix the code or refactor to satisfy the linter.
- **NEVER** add `//go:nosplit`, `//go:noescape`, or other compiler directives to work around build errors.
- **NEVER** use `replace` directives in `go.mod` for production code. They are for local development only and must be removed before commit.
- **NEVER** vendor dependencies without explicit user approval (`go mod vendor`).
- **ALWAYS** handle errors explicitly. Do not discard errors with `_`.
- **ALWAYS** run `go mod tidy` after adding or removing imports.
- **ALWAYS** use `go vet ./...` as part of the verification cycle after a fix.

## Stop Conditions

- The build error requires changes to a third-party dependency that the team does not control. Escalate with the module path and version.
- The error involves CGO or platform-specific build constraints that cannot be reproduced in the current environment. Document the constraint and escalate.
- Two fix attempts have failed for the same error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | go build ./... | go vet ./... | go test -race ./...
```

---

# Handler: Java Build Resolver

## Purpose

Resolves Java compilation errors, build tool failures, and static analysis warnings across both Maven and Gradle projects. Covers dependency resolution, annotation processing, and framework-specific diagnostics for Spring Boot. Detects the build tool automatically from project files and applies the corresponding diagnostic sequence. Targets Java 17+ with either Maven or Gradle.

## Activation

Activate this handler when:

- The project contains `pom.xml` (Maven) or `build.gradle`/`build.gradle.kts` (Gradle)
- Source files have the `.java` extension
- Build errors reference `javac` messages (e.g., `cannot find symbol`, `incompatible types`)
- The user reports issues with `./mvnw compile`, `./gradlew build`, or IDE build

## Diagnostic Sequence (Phase 2 -- Reproduction)

### Build Tool Detection

```bash
# Detect the build tool
if [ -f "pom.xml" ]; then
    echo "BUILD_TOOL=maven"
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
    echo "BUILD_TOOL=gradle"
else
    echo "BUILD_TOOL=unknown -- check subdirectories"
fi

# Verify Java version
java -version 2>&1
javac -version 2>&1
```

### Maven Diagnostic Sequence

```bash
# 1. Verify Maven wrapper and version
./mvnw --version

# 2. Resolve dependencies (download and verify)
./mvnw dependency:resolve 2>&1

# 3. Compile main sources
./mvnw compile 2>&1

# 4. Compile test sources
./mvnw test-compile 2>&1

# 5. Run checkstyle (if configured)
./mvnw checkstyle:check 2>&1

# 6. Run SpotBugs (if configured)
./mvnw spotbugs:check 2>&1

# 7. Run full test suite
./mvnw test 2>&1

# 8. Full build with all phases
./mvnw verify 2>&1
```

### Gradle Diagnostic Sequence

```bash
# 1. Verify Gradle wrapper and version
./gradlew --version

# 2. Compile main sources
./gradlew compileJava 2>&1

# 3. Compile test sources
./gradlew compileTestJava 2>&1

# 4. Run checkstyle (if configured)
./gradlew checkstyleMain 2>&1

# 5. Run SpotBugs (if configured)
./gradlew spotbugsMain 2>&1

# 6. Run full test suite
./gradlew test 2>&1

# 7. Full build
./gradlew build 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot find symbol: variable/method/class X` | The class, method, or variable `X` is not declared, not imported, or not on the classpath. | Add the missing import. Verify the dependency is declared in `pom.xml` or `build.gradle`. Check spelling and package path. Check for typos in method names. |
| `variable X might not have been initialized` | A local variable is used before being assigned a value on all code paths. | Initialize the variable at declaration, or ensure all branches (if/else, try/catch) assign a value before use. |
| `non-static method X cannot be referenced from a static context` | Calling an instance method from a `static` method or block without an object instance. | Create an instance and call the method on it, or make the method `static` if it does not depend on instance state. |
| `annotation processing failed` | An annotation processor (Lombok, MapStruct, Dagger, etc.) failed during compilation. | Check the annotation processor output. Verify the processor version is compatible with the Java version. Clean and rebuild. |
| `Source option N is no longer supported. Use N or later.` | The `--source` or `--release` flag specifies a Java version that the compiler no longer supports. | Update `<maven.compiler.source>` and `<maven.compiler.target>` in `pom.xml`, or `sourceCompatibility`/`targetCompatibility` in `build.gradle` to a supported version. |
| `incompatible types: X cannot be converted to Y` | Type mismatch in assignment, return, or argument. | Cast explicitly if safe, use conversion methods, or change the type declaration. For generics, check type parameter bounds. |
| `unreported exception X; must be caught or declared to be thrown` | A checked exception is thrown but not handled or declared in the method signature. | Add `throws X` to the method signature, or wrap in a try-catch block. |
| `package X does not exist` | The package is not on the classpath. Missing dependency or wrong import. | Add the dependency to `pom.xml` or `build.gradle`. Verify the import statement matches the actual package structure. |
| `duplicate class: X` | Two source files define the same fully-qualified class name. | Remove or rename the duplicate. Check for conflicting dependencies with `mvn dependency:tree` or `gradle dependencies`. |
| `class X is public, should be declared in a file named X.java` | The public class name does not match the filename. | Rename the file to match the public class name, or rename the class. |
| `method does not override or implement a method from a supertype` | `@Override` annotation on a method that does not exist in the parent class or interface. | Check the parent class/interface for the correct method signature. Verify parameter types and return type match exactly. |
| `cannot access X: class file for X not found` | A transitive dependency is missing from the classpath. | Add the missing dependency explicitly, or check that the parent dependency includes it transitively. |

## Maven Troubleshooting

```bash
# Show the full dependency tree
./mvnw dependency:tree

# Show dependency tree filtered to a specific artifact
./mvnw dependency:tree -Dincludes=groupId:artifactId

# Analyze unused and undeclared dependencies
./mvnw dependency:analyze

# Force re-download of all dependencies
./mvnw dependency:purge-local-repository
./mvnw dependency:resolve

# Show effective POM (resolved inheritance and profiles)
./mvnw help:effective-pom

# Show active profiles
./mvnw help:active-profiles

# Debug dependency conflicts
./mvnw enforcer:enforce 2>&1

# Run a specific test class
./mvnw test -Dtest=ClassName

# Skip tests during build (diagnosis only, do not commit with this)
./mvnw compile -DskipTests

# Clear local Maven cache for a specific artifact
rm -rf ~/.m2/repository/com/example/artifact-name

# Check for dependency updates
./mvnw versions:display-dependency-updates
```

## Gradle Troubleshooting

```bash
# Show the full dependency tree
./gradlew dependencies --configuration compileClasspath

# Show dependency insight for a specific library
./gradlew dependencyInsight --dependency library-name --configuration compileClasspath

# Force refresh of cached dependencies
./gradlew build --refresh-dependencies

# Show build scan for detailed analysis
./gradlew build --scan

# List all tasks
./gradlew tasks --all

# Run with debug output
./gradlew build --debug 2>&1 | tail -100

# Clean Gradle caches
rm -rf .gradle/
rm -rf ~/.gradle/caches/
./gradlew clean build

# Check for dependency updates (requires plugin)
./gradlew dependencyUpdates
```

## Spring Boot Troubleshooting

```bash
# Verify Spring Boot auto-configuration report
./mvnw spring-boot:run --debug 2>&1 | grep "CONDITIONS EVALUATION REPORT" -A 50
# or
java -jar target/app.jar --debug 2>&1 | grep "CONDITIONS EVALUATION REPORT" -A 50

# Common Spring Boot build errors:

# 1. Bean definition conflicts
#    Error: "Consider renaming one of the beans or enabling overriding"
#    Fix: Check for duplicate @Component/@Service/@Repository annotations
#         or add spring.main.allow-bean-definition-overriding=true (last resort)

# 2. Missing @Autowired candidate
#    Error: "No qualifying bean of type X"
#    Fix: Add @Component/@Service annotation to the implementing class
#         Verify component scan base package covers the class

# 3. Circular dependency
#    Error: "The dependencies of some of the beans form a cycle"
#    Fix: Use @Lazy on one injection point, or restructure to break the cycle
#         Avoid using spring.main.allow-circular-references=true

# 4. Property not found
#    Error: "Could not resolve placeholder 'X'"
#    Fix: Add the property to application.yml/application.properties
#         Check active profile: spring.profiles.active

# Check active profiles and loaded configuration
./mvnw spring-boot:run 2>&1 | head -20

# Verify the classpath
./mvnw dependency:build-classpath
```

## Annotation Processor Troubleshooting

```bash
# Lombok issues
# Verify Lombok version matches Java version
./mvnw dependency:tree -Dincludes=org.projectlombok:lombok
# Ensure annotationProcessor is configured
# Maven: <annotationProcessorPaths> in maven-compiler-plugin
# Gradle: annotationProcessor 'org.projectlombok:lombok:X.Y.Z'

# MapStruct issues
# Verify MapStruct processor is on the annotation processor path
./mvnw dependency:tree -Dincludes=org.mapstruct
# Check generated sources
find target/generated-sources -name "*.java" | head -20

# Clean generated sources and rebuild
./mvnw clean compile
```

## Hard Rules

- **NEVER** add `@SuppressWarnings("unchecked")` to bypass generic type safety. Fix the generics.
- **NEVER** add `@SuppressWarnings("deprecation")` without migrating off the deprecated API first.
- **NEVER** catch `Exception` or `Throwable` generically to hide errors. Catch the specific exception type.
- **NEVER** use `-DskipTests` or `-Dmaven.test.skip=true` as a permanent solution. Tests must pass.
- **NEVER** use `--add-opens` or `--add-exports` JVM flags to suppress module access errors without understanding the root cause.
- **ALWAYS** run `./mvnw verify` or `./gradlew build` (including tests) as the final verification step.
- **ALWAYS** check both Maven and Gradle configurations in polyglot projects.
- **ALWAYS** verify the Java version matches the project's `sourceCompatibility`/`maven.compiler.source`.

## Stop Conditions

- The error requires upgrading the Java version (e.g., project uses Java 17 features but build environment has Java 11). Escalate with version requirements.
- The error is in a third-party annotation processor generating incorrect code. Document the processor, version, and error, then escalate.
- Two fix attempts have failed for the same error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | ./mvnw verify | checkstyle | spotbugs | tests
```

---

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

---

# Handler: Python Build Resolver

## Purpose

Resolves Python import errors, package installation failures, type checking violations, and linting issues. Covers the full diagnostic chain from `pip check` through `mypy`, `ruff check`, and import isolation analysis. Focuses on module resolution, virtual environment integrity, and dependency conflict resolution. Targets Python 3.10+ with pip or uv as the package manager.

## Activation

Activate this handler when:

- The project contains `pyproject.toml`, `setup.py`, `setup.cfg`, or `requirements.txt`
- Source files have the `.py` extension
- Errors reference `ModuleNotFoundError`, `ImportError`, `SyntaxError`, or `IndentationError`
- The user reports issues with `pip install`, `python -m`, `mypy`, or `ruff`
- Type checking or linting failures block the build pipeline

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Python version and environment
python --version
which python
echo $VIRTUAL_ENV

# 2. Verify virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "WARNING: No virtual environment active"
    # Check for common venv locations
    ls -d .venv venv .env env 2>/dev/null
fi

# 3. Check for dependency conflicts
pip check 2>&1

# 4. List installed packages with versions
pip list --format=columns 2>&1

# 5. Verify the project is installed in development mode
pip show $(basename $(pwd)) 2>/dev/null || echo "Project not installed as package"

# 6. Run ruff linter
ruff check . 2>&1

# 7. Run ruff formatter check
ruff format --check . 2>&1

# 8. Run mypy type checker (if configured)
mypy . 2>&1

# 9. Run the test suite to confirm behavioral correctness
python -m pytest --tb=short 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'X'` | The module `X` is not installed in the active Python environment, or the package name differs from the import name. | Install the package: `pip install X`. If the package name differs (e.g., `pip install Pillow` for `import PIL`), check PyPI for the correct package name. Verify the virtual environment is active. |
| `ImportError: cannot import name 'Y' from 'X'` | The symbol `Y` does not exist in module `X`. Version mismatch (API changed), typo, or circular import. | Check the installed version: `pip show X`. Verify the symbol exists in that version's API. Check for circular imports by examining the import chain. |
| `SyntaxError: invalid syntax` | Python syntax error. Common causes: missing colon, unmatched parentheses, Python 2 syntax in Python 3, f-string issues in older Python versions. | Read the exact line and character position. Check for match/case syntax (3.10+), walrus operator (3.8+), or type union syntax `X \| Y` (3.10+). Verify the Python version supports the syntax used. |
| `IndentationError: unexpected indent` | Inconsistent use of tabs and spaces, or wrong indentation level. | Configure the editor to use 4 spaces (PEP 8). Run `ruff format` to auto-fix. Check for mixed tabs and spaces: `python -tt script.py`. |
| `pip dependency conflict: X requires Y==1.0, but you have Y==2.0` | Two installed packages require incompatible versions of the same dependency. | Run `pip check` to see all conflicts. Use `pip install X --dry-run` to preview resolution. Consider pinning compatible versions in `pyproject.toml`. Use `pip install --force-reinstall X` as last resort. |
| `ModuleNotFoundError: No module named 'X.Y'` | Submodule `Y` does not exist in package `X`, or `X` is a namespace package without proper `__init__.py`. | Verify the submodule exists in the installed package: `python -c "import X; print(X.__path__)"`. Check for missing `__init__.py` in local packages. |
| `ImportError: attempted relative import with no known parent package` | A relative import (`from .module import X`) is used in a script that is run directly instead of as a module. | Run as a module: `python -m package.module` instead of `python package/module.py`. Ensure the package has `__init__.py`. |
| `AttributeError: module 'X' has no attribute 'Y'` | The attribute `Y` was removed or renamed in a newer version of `X`, or a local file shadows the installed module. | Check for local files named `X.py` that shadow the installed module. Verify the installed version: `pip show X`. Check the migration guide for API changes. |
| `TypeError: X() got an unexpected keyword argument 'Y'` | Function signature changed between versions, or wrong function is being called. | Check the function signature in the installed version: `python -c "import X; help(X.func)"`. Pin the dependency version if needed. |
| `ValueError: attempted relative import beyond top-level package` | Relative import goes above the package root. | Restructure imports to stay within the package boundary. Use absolute imports instead. |

## Virtual Environment Troubleshooting

```bash
# Check if a virtual environment is active
echo "VIRTUAL_ENV=$VIRTUAL_ENV"
which python
python -c "import sys; print(sys.prefix); print(sys.executable)"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Verify packages are installed in the venv, not globally
pip list --path $(python -c "import site; print(site.getusersitepackages())") 2>/dev/null

# Check for system Python contamination
python -c "import sys; print([p for p in sys.path if 'site-packages' in p])"

# Recreate the virtual environment from scratch
deactivate 2>/dev/null
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # or: pip install -r requirements.txt

# Using uv (faster alternative)
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Check for PATH issues (wrong Python binary)
which -a python python3
```

## Import Resolution Troubleshooting

```bash
# Trace the import chain for a specific module
python -v -c "import X" 2>&1 | tail -20

# Find where a module is loaded from
python -c "import X; print(X.__file__)"

# Check for local files shadowing installed packages
find . -name "X.py" -not -path "./.venv/*" -not -path "./venv/*"

# List the Python path (import search order)
python -c "import sys; print('\n'.join(sys.path))"

# Verify package entry points
pip show -f X | head -20

# Check for circular imports (trace the import order)
python -c "
import sys
original_import = __builtins__.__import__
def tracing_import(name, *args, **kwargs):
    print(f'Importing: {name}')
    return original_import(name, *args, **kwargs)
__builtins__.__import__ = tracing_import
import your_module
" 2>&1 | head -30

# Verify editable install is working
pip show -e $(basename $(pwd)) 2>/dev/null
```

## Type Checking Troubleshooting

```bash
# Run mypy with verbose output
mypy --verbose . 2>&1

# Check mypy configuration
mypy --config-file pyproject.toml --warn-unused-configs . 2>&1

# Run mypy on a single file
mypy path/to/file.py 2>&1

# Show mypy's understanding of a type
mypy --show-error-codes --show-column-numbers path/to/file.py 2>&1

# Install type stubs for third-party packages
mypy --install-types . 2>&1

# Use reveal_type() for debugging (remove before commit)
# Add to code: reveal_type(variable)  then run mypy
```

## Hard Rules

- **NEVER** install packages to the system Python. Always use a virtual environment.
- **NEVER** add `# type: ignore` comments to bypass mypy errors. Fix the type annotation or refactor the code.
- **NEVER** add `# noqa` comments to bypass ruff findings. Fix the code.
- **NEVER** use `sys.path.insert()` or `sys.path.append()` hacks to fix import errors. Fix the package structure.
- **NEVER** use `pip install --break-system-packages` or `--user` as a workaround for environment issues.
- **ALWAYS** use a virtual environment (`.venv` by convention).
- **ALWAYS** run `pip check` after installing or upgrading packages to verify consistency.
- **ALWAYS** verify the correct Python version is active before diagnosing import errors.
- **ALWAYS** check for local file shadowing before concluding a package is not installed.

## Stop Conditions

- The error requires a Python version upgrade that affects the entire project (e.g., Python 3.12 syntax used in a 3.10 project). Escalate with the version requirement.
- The dependency conflict is unresolvable with the current version constraints (two packages require mutually exclusive versions of a third). Document the conflict tree and escalate.
- Two fix attempts have failed for the same import or type error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | ruff check | ruff format --check | mypy | pytest
```

---

# Handler: PyTorch Runtime Error Resolver

## Purpose

Resolves PyTorch runtime errors including tensor shape mismatches, device placement conflicts, CUDA out-of-memory failures, autograd graph issues, and DataLoader collation problems. This handler addresses runtime errors, not Python compilation or import errors (use `python-build.md` for those). Focuses on the numerical and computational aspects specific to deep learning: shape algebra, memory management, gradient flow, and device consistency. Targets PyTorch 2.0+ with CUDA 11.8+.

## Activation

Activate this handler when:

- The project imports `torch`, `torchvision`, `torchaudio`, or `torch.nn`
- Runtime errors reference `RuntimeError` with tensor-specific messages (shapes, devices, dtypes)
- The user reports CUDA OOM, gradient errors, or DataLoader failures
- Model training produces `NaN` or `Inf` values, or loss does not decrease

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify PyTorch installation and CUDA availability
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'cuDNN version: {torch.backends.cudnn.version()}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
else:
    print('Running on CPU only')
"

# 2. Check for basic tensor operations
python -c "
import torch
x = torch.randn(2, 3)
y = torch.randn(3, 4)
z = x @ y
print(f'Basic matmul OK: {x.shape} @ {y.shape} = {z.shape}')
"

# 3. Verify model can be instantiated (adjust import to match project)
python -c "
import sys; sys.path.insert(0, '.')
# from model import YourModel
# model = YourModel()
# print(f'Model parameters: {sum(p.numel() for p in model.parameters()):,}')
print('Uncomment model import to test instantiation')
"

# 4. Test with minimal batch size
python -c "
import torch
# Replace with actual model and data shape
batch_size = 2
x = torch.randn(batch_size, 3, 224, 224)
print(f'Test tensor shape: {x.shape}')
print(f'Test tensor device: {x.device}')
print(f'Test tensor dtype: {x.dtype}')
"

# 5. Check GPU memory status (if CUDA available)
python -c "
import torch
if torch.cuda.is_available():
    print(f'Memory allocated: {torch.cuda.memory_allocated() / 1e6:.1f} MB')
    print(f'Memory reserved: {torch.cuda.memory_reserved() / 1e6:.1f} MB')
    print(f'Max memory allocated: {torch.cuda.max_memory_allocated() / 1e6:.1f} MB')
"

# 6. Run the failing training/inference script with batch_size=2
# python train.py --batch-size 2 --epochs 1 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `RuntimeError: mat1 and mat2 shapes cannot be multiplied (AxB and CxD)` | Matrix multiplication where the inner dimensions do not match (B != C). Common when the linear layer input size does not match the flattened feature map. | Print shapes before the operation: `print(x.shape)`. Calculate the correct input size: for Conv2d output going into Linear, the size is `channels * height * width` after all convolutions and pooling. Use `x.view(x.size(0), -1)` to flatten. |
| `RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu` | A tensor or model parameter is on a different device than the input. Common when forgetting to move the model or data to GPU. | Move the model: `model.to(device)`. Move the data: `x = x.to(device)`. Define `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')` once and use consistently. Check that all tensors in loss computation are on the same device. |
| `torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate X MiB` | GPU memory exhausted. Batch size too large, model too large, or memory leak from accumulated gradients/tensors. | Reduce batch size. Use `torch.cuda.empty_cache()`. Enable gradient checkpointing: `model.gradient_checkpointing_enable()`. Use mixed precision: `torch.cuda.amp.autocast()`. Use `with torch.no_grad():` during evaluation. Check for tensors not detached in logging. |
| `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn` | Calling `.backward()` on a tensor that was created without gradient tracking (detached or created with `requires_grad=False`). | Ensure the computation graph is connected. Do not detach intermediate results. Check that model parameters have `requires_grad=True`. Verify loss is computed from model output, not from detached copies. |
| `RuntimeError: one of the variables needed for gradient computation has been modified by an inplace operation` | An in-place operation (e.g., `x += 1`, `x.relu_()`, `x[0] = val`) modified a tensor needed for backward pass gradient computation. | Replace in-place operations with out-of-place equivalents: `x = x + 1` instead of `x += 1`. Use `F.relu(x)` instead of `x.relu_()`. Clone before modifying: `x = x.clone()`. |
| `RuntimeError: default_collate: batch must contain tensors, numpy arrays, numbers, dicts or lists; found <class 'X'>` | The DataLoader's default collate function cannot handle a custom data type returned by the Dataset's `__getitem__`. | Implement a custom `collate_fn` that handles the data type. Convert to tensors in `__getitem__`. For variable-length sequences, pad in the collate function. |
| `RuntimeError: Trying to backward through the graph a second time` | Calling `.backward()` twice on the same computation graph without `retain_graph=True`. Common in GANs and multi-loss training. | Add `retain_graph=True` to the first `.backward()` call if a second backward is needed. Alternatively, restructure to avoid reusing the graph. For most cases, detach intermediate results. |
| `IndexError: index out of range in self (Embedding)` | An input index to `nn.Embedding` exceeds `num_embeddings - 1`, or a negative index is passed. | Check the vocabulary size matches `num_embeddings`. Verify tokenizer output range: `assert input_ids.max() < embedding.num_embeddings`. Check for padding token index. Print `input_ids.min()` and `input_ids.max()` before the embedding layer. |
| `RuntimeError: expected scalar type Float but found Double` | Tensor dtype mismatch. NumPy defaults to float64 (Double), PyTorch expects float32 (Float). | Convert tensors: `x = x.float()` or `x = x.to(torch.float32)`. When creating from NumPy: `torch.from_numpy(arr).float()`. Set NumPy default: `arr = arr.astype(np.float32)`. |
| `RuntimeError: Given groups=1, weight of size [X], expected input[Y] to have Z channels` | Conv2d input channels do not match the layer's `in_channels` parameter. | Verify input shape is `(batch, channels, height, width)`. Check that the channel dimension matches `in_channels`. For grayscale images, use `in_channels=1`. For RGB, use `in_channels=3`. |
| `ValueError: optimizer got an empty parameter list` | `model.parameters()` returned an empty iterator. Model has no trainable parameters or was not properly defined. | Verify `nn.Module` subclass registers parameters via `nn.Linear`, `nn.Conv2d`, etc. (not plain tensors). Use `nn.Parameter()` for custom parameters. Check that `self.layers = nn.ModuleList([...])` is used, not a plain Python list. |
| `RuntimeError: stack expects each tensor to be equal size, but got [X] at entry 0 and [Y] at entry 1` | DataLoader is trying to batch tensors of different sizes (variable-length sequences, different image sizes). | Implement a custom `collate_fn` with padding. Use `torch.nn.utils.rnn.pad_sequence()` for sequences. Resize images to a consistent size in the transform pipeline. |

## Shape Debugging Section

```python
# Add shape debugging hooks to a model
def register_shape_hooks(model):
    """Print input and output shapes for every layer."""
    def hook_fn(module, input, output, name=""):
        input_shapes = [x.shape if isinstance(x, torch.Tensor) else type(x) for x in input]
        output_shape = output.shape if isinstance(output, torch.Tensor) else type(output)
        print(f"{name:40s} | input: {input_shapes} | output: {output_shape}")

    for name, layer in model.named_modules():
        layer.register_forward_hook(lambda m, i, o, n=name: hook_fn(m, i, o, n))

# Usage:
# register_shape_hooks(model)
# output = model(sample_input)  # prints all shapes
```

```python
# Manual shape tracing through a forward pass
def trace_shapes(model, x):
    """Step through the forward pass printing shapes."""
    print(f"{'Layer':40s} | {'Output Shape':20s} | {'Params':>10s}")
    print("-" * 75)
    for name, layer in model.named_children():
        x = layer(x)
        params = sum(p.numel() for p in layer.parameters())
        print(f"{name:40s} | {str(x.shape):20s} | {params:>10,}")
    return x
```

```bash
# Quick shape check from command line
python -c "
import torch
from model import YourModel  # adjust import

model = YourModel()
x = torch.randn(2, 3, 224, 224)  # adjust shape

# Trace through the model
try:
    with torch.no_grad():
        output = model(x)
    print(f'Input:  {x.shape}')
    print(f'Output: {output.shape}')
except RuntimeError as e:
    print(f'Shape error: {e}')
    # Print all named module dimensions
    for name, param in model.named_parameters():
        print(f'  {name}: {param.shape}')
"
```

## Memory Debugging Section

```python
# Monitor GPU memory during training
def print_memory_stats(tag=""):
    """Print current GPU memory usage."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        max_alloc = torch.cuda.max_memory_allocated() / 1e9
        print(f"[{tag}] Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB | Peak: {max_alloc:.2f} GB")
```

```python
# Find the largest tensors in GPU memory
def find_large_tensors(min_size_mb=1):
    """List all tensors on GPU larger than min_size_mb."""
    import gc
    gc.collect()
    torch.cuda.empty_cache()

    tensors = []
    for obj in gc.get_objects():
        try:
            if torch.is_tensor(obj) and obj.is_cuda:
                size_mb = obj.element_size() * obj.nelement() / 1e6
                if size_mb >= min_size_mb:
                    tensors.append((size_mb, obj.shape, obj.dtype, obj.device))
        except Exception:
            pass

    tensors.sort(reverse=True)
    for size, shape, dtype, device in tensors[:20]:
        print(f"  {size:8.1f} MB | {str(shape):30s} | {dtype} | {device}")
```

```bash
# Memory reduction strategies (apply in order)
python -c "
strategies = [
    '1. Reduce batch_size (halve it)',
    '2. Use torch.cuda.amp.autocast() for mixed precision (FP16)',
    '3. Use gradient accumulation (effective_batch = batch * accum_steps)',
    '4. Enable gradient checkpointing (trades compute for memory)',
    '5. Use torch.utils.checkpoint.checkpoint() for specific layers',
    '6. Move to CPU for evaluation: model.eval(); torch.no_grad()',
    '7. Clear cache between steps: torch.cuda.empty_cache()',
    '8. Use DataLoader with pin_memory=True and num_workers>0',
    '9. Reduce model size (fewer layers, smaller hidden dimensions)',
    '10. Use DeepSpeed ZeRO or FSDP for multi-GPU memory sharing',
]
for s in strategies:
    print(s)
"
```

## Gradient Debugging Section

```python
# Check gradient flow through the model
def check_gradient_flow(model):
    """Verify gradients are flowing to all parameters."""
    for name, param in model.named_parameters():
        if param.requires_grad:
            if param.grad is None:
                print(f"  NO GRAD:  {name}")
            elif param.grad.abs().max() == 0:
                print(f"  ZERO GRAD: {name} (vanishing gradient)")
            elif torch.isnan(param.grad).any():
                print(f"  NaN GRAD:  {name} (exploding gradient)")
            elif torch.isinf(param.grad).any():
                print(f"  Inf GRAD:  {name} (exploding gradient)")
            else:
                print(f"  OK:        {name} | grad norm: {param.grad.norm():.6f}")
```

```python
# Detect NaN/Inf in forward pass
torch.autograd.set_detect_anomaly(True)  # Enable anomaly detection (slow, debug only)

# Check for NaN in loss
def safe_backward(loss):
    """Check loss before backward pass."""
    if torch.isnan(loss):
        raise ValueError(f"NaN loss detected: {loss.item()}")
    if torch.isinf(loss):
        raise ValueError(f"Inf loss detected: {loss.item()}")
    loss.backward()
```

## Hard Rules

- **ALWAYS** test with `batch_size=2` first before increasing. This catches shape errors with minimal resource usage. Use 2 (not 1) to expose batch dimension bugs.
- **NEVER** use `.item()` inside a training loop on a tensor that is part of the computation graph. Detach first: `loss.detach().item()`.
- **NEVER** store tensors in Python lists across training steps without detaching. This prevents garbage collection and causes memory leaks: `losses.append(loss.detach().cpu())`.
- **NEVER** use `torch.autograd.set_detect_anomaly(True)` in production. It is for debugging only and severely impacts performance.
- **NEVER** silence shape errors by reshaping without understanding the semantics. A wrong reshape produces silent bugs in model accuracy.
- **ALWAYS** set `model.eval()` and use `with torch.no_grad():` during validation and inference.
- **ALWAYS** verify device consistency before matrix operations: `assert x.device == weight.device`.
- **ALWAYS** check `requires_grad` state when gradients are missing: `print([(n, p.requires_grad) for n, p in model.named_parameters()])`.

## Stop Conditions

- The error requires CUDA driver or hardware changes that cannot be resolved in software (driver version mismatch, GPU hardware fault). Escalate with the CUDA version and GPU model.
- The error is a numerical instability (NaN/Inf) that persists after learning rate reduction, gradient clipping, and batch normalization. Document the training configuration and escalate.
- Two fix attempts have failed for the same runtime error. Provide the root cause analysis, shape traces, and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>
  Shapes: <input_shape> -> <expected_shape> (was <actual_shape>)

[FIXED] <file>:<line> -- <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | python train.py --batch-size 2 --epochs 1 | no shape errors | no device errors
```

---

# Handler: Rust Build Resolver

## Purpose

Resolves Rust compilation errors with special emphasis on borrow checker diagnostics, lifetime analysis, and trait bound failures. Covers the full diagnostic chain from `cargo check` through `cargo clippy`, `cargo fmt`, dependency auditing with `cargo-audit`, and duplicate detection with `cargo tree`. Targets Rust 2021 edition and later using Cargo workspaces.

## Activation

Activate this handler when:

- The project contains `Cargo.toml` at the repository root or in a workspace member
- Source files have the `.rs` extension
- Build errors reference Rust compiler codes (e.g., `E0382`, `E0277`, `E0106`)
- The user reports issues with `cargo build`, `cargo test`, or `cargo run`

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Rust toolchain
rustc --version && cargo --version

# 2. Check compilation without producing binaries (fastest feedback)
cargo check 2>&1

# 3. Run clippy for lint-level diagnostics
cargo clippy --all-targets --all-features -- -D warnings 2>&1

# 4. Verify formatting compliance
cargo fmt --all --check 2>&1

# 5. Check for duplicate dependency versions
cargo tree --duplicates 2>&1

# 6. Audit dependencies for known vulnerabilities (if cargo-audit installed)
cargo audit 2>&1

# 7. Run the full test suite
cargo test --all-targets --all-features 2>&1

# 8. For workspace projects, check all members
cargo check --workspace 2>&1
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot borrow X as mutable because it is also borrowed as immutable` | Simultaneous mutable and immutable borrows of the same value within overlapping scopes. | Restructure code so the immutable borrow ends before the mutable borrow begins. Clone the value if shared ownership is needed, or use `RefCell<T>` for interior mutability. |
| `X does not live long enough` | A reference outlives the data it points to. The borrowed value is dropped while still referenced. | Extend the lifetime of the owned value, return owned data instead of references, or use `Arc<T>` / `Rc<T>` for shared ownership. |
| `cannot move out of X which is behind a shared reference` | Attempting to take ownership of data behind `&T` (a shared reference does not permit moves). | Clone the value, use `&mut T` if mutation is needed, or restructure to avoid moving out of the reference. |
| `mismatched types: expected X, found Y` | Function return type, variable assignment, or argument does not match the expected type. | Convert explicitly (`.into()`, `as`, `From::from`). For enum variants, ensure all arms return the same type. For `Result`/`Option`, use `?` or `map`. |
| `the trait X is not implemented for Y` | A generic bound or function signature requires trait `X` but type `Y` does not implement it. | Implement the trait for `Y`, use a type that already implements it, or add `#[derive(X)]` if it is a derivable trait. |
| `unresolved import X` | The module path is wrong, the item is not public, or the crate is not in `Cargo.toml`. | Verify the import path. Check `pub` visibility. Add the crate to `[dependencies]` in `Cargo.toml` and run `cargo check`. |
| `lifetime may not live long enough` | A lifetime annotation is missing or incorrect, causing the compiler to infer conflicting lifetimes. | Add explicit lifetime annotations. Ensure input and output lifetimes are correctly related. Consider returning owned data. |
| `future cannot be sent between threads safely (not Send)` | An async function holds a non-Send type (e.g., `Rc`, `RefCell`, raw pointer) across an `.await` point. | Replace `Rc` with `Arc`, `RefCell` with `Mutex` or `RwLock`. Restructure so non-Send values do not span `.await` points. |
| `value used after move` (E0382) | A value was moved (ownership transferred) and then used again. | Clone before the move, use references instead, or restructure to avoid reuse after move. |
| `type annotations needed` (E0282) | The compiler cannot infer the type and needs explicit annotation. | Add type annotations to the variable, use turbofish syntax (`func::<Type>()`), or annotate the closure parameters. |
| `no method named X found for type Y` | Method does not exist on the type, or the trait providing it is not in scope. | Bring the trait into scope with `use`. Check that `Y` is the correct type (not a reference or wrapper). |
| `this function takes N arguments but M were supplied` | Argument count mismatch in function call. | Check the function signature. Common after refactoring when parameters were added or removed. |

## Borrow Checker Examples

### Simultaneous mutable and immutable borrow

```rust
// BROKEN: immutable borrow `first` still alive when `v` is mutably borrowed
let mut v = vec![1, 2, 3];
let first = &v[0];       // immutable borrow starts
v.push(4);                // mutable borrow -- conflict
println!("{first}");      // immutable borrow used here

// FIXED: end the immutable borrow before mutating
let mut v = vec![1, 2, 3];
let first = v[0];         // copy the value (i32 is Copy)
v.push(4);                // no conflict
println!("{first}");
```

### Value does not live long enough

```rust
// BROKEN: `s` is dropped at end of block, but reference escapes
fn dangling() -> &str {
    let s = String::from("hello");
    &s  // s dropped here, reference is dangling
}

// FIXED: return owned data
fn not_dangling() -> String {
    let s = String::from("hello");
    s  // ownership transferred to caller
}
```

### Cannot move out of shared reference

```rust
// BROKEN: trying to move `name` out of a shared reference
struct User { name: String }

fn get_name(user: &User) -> String {
    user.name  // cannot move out of &User
}

// FIXED: clone or return a reference
fn get_name(user: &User) -> String {
    user.name.clone()
}

// ALTERNATIVE: return a reference with proper lifetime
fn get_name(user: &User) -> &str {
    &user.name
}
```

### Async not Send

```rust
// BROKEN: Rc is not Send, held across .await
use std::rc::Rc;

async fn process() {
    let data = Rc::new(vec![1, 2, 3]);
    some_async_call().await;  // Rc held across await
    println!("{:?}", data);
}

// FIXED: use Arc instead of Rc
use std::sync::Arc;

async fn process() {
    let data = Arc::new(vec![1, 2, 3]);
    some_async_call().await;
    println!("{:?}", data);
}
```

## Dependency Troubleshooting

```bash
# Show the full dependency tree
cargo tree

# Find why a specific crate is included
cargo tree --invert --package some-crate

# List duplicate dependency versions
cargo tree --duplicates

# Update dependencies within semver constraints
cargo update

# Update a specific dependency
cargo update --package some-crate

# Check for yanked crates
cargo install --locked cargo-audit && cargo audit

# Clean build artifacts (resolves stale compilation issues)
cargo clean

# Rebuild with verbose output for linker diagnostics
cargo build --verbose 2>&1
```

## Feature Flag Troubleshooting

```bash
# List all available features for a dependency
cargo metadata --format-version=1 | jq '.packages[] | select(.name == "some-crate") | .features'

# Build with a specific feature enabled
cargo check --features "feature-name"

# Build with all features enabled
cargo check --all-features

# Build with no default features
cargo check --no-default-features
```

## Hard Rules

- **NEVER** use `unsafe` blocks to bypass borrow checker errors. The borrow checker is correct. Restructure the code.
- **NEVER** add `.unwrap()` to silence `Result` or `Option` errors. Use `?`, `match`, `unwrap_or`, `unwrap_or_else`, or `expect` with a descriptive message.
- **NEVER** add `#[allow(clippy::...)]` or `#[allow(unused)]` to suppress warnings. Fix the code or refactor.
- **NEVER** use `mem::transmute` or `mem::forget` to work around ownership issues.
- **ALWAYS** propagate errors with `?` in library code. Reserve `expect()` for cases with a clear invariant message.
- **ALWAYS** run `cargo clippy` after fixes, not just `cargo check`.
- **ALWAYS** verify that `cargo fmt --check` passes after edits.

## Stop Conditions

- The error requires `unsafe` code to resolve (FFI boundary, raw pointer manipulation). Escalate with the exact safety requirement.
- The error involves a compiler bug or ICE (Internal Compiler Error). Report the rustc version and escalate.
- Two fix attempts have failed for the same borrow checker error. Provide the ownership diagram and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | cargo check | cargo clippy | cargo test
```

---

# Handler: TypeScript Build Resolver

## Purpose

Resolves TypeScript compilation errors, Node.js module resolution failures, and linting issues. Covers the full diagnostic chain from `tsc --noEmit` through `npm run build`, ESLint, and module bundler diagnostics. Handles strict mode violations, generic type constraints, React/JSX type errors, and Node.js module interop (ESM/CJS). Targets TypeScript 5.0+ with Node.js 18+.

## Activation

Activate this handler when:

- The project contains `tsconfig.json` or `tsconfig.*.json`
- Source files have `.ts`, `.tsx`, `.mts`, or `.cts` extensions
- Build errors reference TypeScript diagnostics (e.g., `TS2322`, `TS7006`, `TS2307`)
- The user reports issues with `tsc`, `npm run build`, `next build`, or bundler output

## Diagnostic Sequence (Phase 2 -- Reproduction)

Run these commands in order. Stop at the first failure and diagnose before continuing.

```bash
# 1. Verify Node.js and TypeScript versions
node --version
npx tsc --version

# 2. Verify dependencies are installed
if [ -f "package-lock.json" ]; then
    npm ci 2>&1
elif [ -f "pnpm-lock.yaml" ]; then
    pnpm install --frozen-lockfile 2>&1
elif [ -f "yarn.lock" ]; then
    yarn install --frozen-lockfile 2>&1
elif [ -f "bun.lockb" ] || [ -f "bun.lock" ]; then
    bun install --frozen-lockfile 2>&1
fi

# 3. Run TypeScript compiler in check mode (no output files)
npx tsc --noEmit 2>&1

# 4. Run the project build script
npm run build 2>&1

# 5. Run ESLint (if configured)
npx eslint . 2>&1

# 6. Run tests
npm test 2>&1

# 7. Check for type coverage (if type-coverage is installed)
npx type-coverage 2>/dev/null
```

## Error Table (Phase 3 -- Root Cause)

| Error | Cause | Fix |
|-------|-------|-----|
| `Parameter 'X' implicitly has an 'any' type. (TS7006)` | The parameter has no type annotation and TypeScript cannot infer it (strict mode enabled via `noImplicitAny`). | Add an explicit type annotation: `(x: string)`. For event handlers, use the specific event type: `(e: React.ChangeEvent<HTMLInputElement>)`. |
| `Object is possibly 'undefined'. (TS2532)` | Accessing a property on a value that could be `undefined` (strict null checks enabled). | Add a null check: `if (obj) { obj.prop }`. Use optional chaining: `obj?.prop`. Use nullish coalescing: `obj ?? fallback`. For definite cases, use non-null assertion `obj!.prop` only with proof. |
| `Cannot find module 'X' or its corresponding type declarations. (TS2307)` | The module is not installed, has no type definitions, or the module resolution strategy cannot find it. | Install the package: `npm install X`. Install types: `npm install -D @types/X`. Check `moduleResolution` in tsconfig.json. For local modules, verify the path and file extension. |
| `Type 'X' is not assignable to type 'Y'. (TS2322)` | Type mismatch in assignment, return value, or property. | Narrow the type with type guards, adjust the type declaration, or use a union type. Check for missing properties in object literals. Do NOT cast with `as` unless type narrowing is impossible. |
| `Generic type 'X' requires N type argument(s). (TS2314)` | A generic type is used without providing the required type parameters. | Add type arguments: `Array<string>`, `Map<string, number>`. Check the generic definition for required vs optional type parameters. |
| `React Hook 'X' is called conditionally. (react-hooks/rules-of-hooks)` | A React hook is called inside an if statement, loop, or after an early return. | Move the hook call to the top level of the component, before any conditional logic. Use the hook unconditionally and handle the condition in the callback or effect body. |
| `Property 'X' does not exist on type 'Y'. (TS2339)` | Accessing a property that is not declared on the type. Common with DOM elements, API responses, or union types. | Add the property to the type definition, use a type guard to narrow the union, or extend the interface. For DOM elements, use the specific element type (`HTMLInputElement`). |
| `Argument of type 'X' is not assignable to parameter of type 'Y'. (TS2345)` | Function argument type does not match the parameter type. | Convert the argument, update the function signature, or use a type guard before the call. Check for literal type vs string type mismatches. |
| `Type 'X' is not assignable to type 'never'. (TS2322)` | TypeScript inferred an empty array or unreachable code path as type `never`. | Provide explicit type annotation for arrays: `const arr: string[] = []`. For switch/if exhaustiveness, add the missing case. |
| `Module 'X' has no exported member 'Y'. (TS2305)` | The named export `Y` does not exist in module `X`. Version change, renamed export, or wrong import syntax. | Check the module's exports: review `index.ts` or `index.d.ts`. Verify the installed version matches the expected API. Use `import X from` for default exports vs `import { Y } from` for named exports. |
| `JSX element type 'X' does not have any construct or call signatures. (TS2604)` | A value is used as a JSX component but TypeScript does not recognize it as a valid component type. | Ensure the component returns `JSX.Element` or `React.ReactNode`. Check that the import is correct (default vs named). Verify the component is a function or class component. |
| `'X' refers to a value, but is being used as a type here. (TS2749)` | Using a runtime value where a type is expected (e.g., `typeof` missing). | Use `typeof X` to get the type of a value. For class instances, use the class name directly as a type. For enums, use `typeof MyEnum[keyof typeof MyEnum]` for the value type. |
| `Cannot use namespace 'X' as a type. (TS2709)` | Importing a namespace as if it were a type, often with incorrect import syntax. | Use `import type { X } from 'module'` for type imports. Check if the module uses `export =` vs `export default`. |

## Cache Recovery Section

```bash
# Clear TypeScript build cache
rm -rf tsconfig.tsbuildinfo
rm -rf .tsbuildinfo

# Clear node_modules and reinstall
rm -rf node_modules
rm -rf .next           # Next.js cache
rm -rf dist            # Build output
rm -rf .turbo          # Turborepo cache
npm ci                 # or pnpm install --frozen-lockfile

# Clear npm cache
npm cache clean --force

# Clear pnpm cache
pnpm store prune

# Regenerate lockfile (caution: may change dependency versions)
# rm package-lock.json && npm install

# Clear ESLint cache
rm -rf .eslintcache

# Clear Jest cache
npx jest --clearCache

# Verify TypeScript can find all project files
npx tsc --listFiles --noEmit 2>&1 | head -30

# Check which tsconfig is being used
npx tsc --showConfig 2>&1

# Verify module resolution for a specific import
npx tsc --traceResolution 2>&1 | grep "module-name" | head -10
```

## Module Resolution Troubleshooting

```bash
# Check the module resolution strategy
npx tsc --showConfig 2>&1 | grep -A2 "moduleResolution"

# Trace how TypeScript resolves a specific module
npx tsc --traceResolution 2>&1 | grep "X" | head -20

# Verify path aliases are configured correctly
# Check tsconfig.json "paths" and "baseUrl"
cat tsconfig.json | grep -A10 '"paths"'

# For ESM/CJS interop issues, check package.json "type" field
cat package.json | grep '"type"'

# Verify @types packages are installed
npm ls @types/ 2>&1

# Check for duplicate type definitions
npm ls | grep @types | sort

# For monorepo module resolution
npx tsc --listFiles 2>&1 | grep "node_modules" | sort -u | head -20
```

## tsconfig Troubleshooting

```bash
# Show the effective tsconfig (with extends resolved)
npx tsc --showConfig 2>&1

# Verify strict mode settings
npx tsc --showConfig 2>&1 | grep -E "strict|noImplicit|null"

# Common tsconfig fixes for build errors:

# 1. Missing file extensions in imports (ESM)
#    Set: "moduleResolution": "bundler" or "node16"

# 2. Cannot find module for path aliases
#    Set: "baseUrl": "." and "paths": { "@/*": ["src/*"] }
#    ALSO configure the bundler (webpack/vite alias)

# 3. JSX not recognized
#    Set: "jsx": "react-jsx" (React 17+) or "jsx": "react" (React 16)

# 4. Declaration files not found
#    Set: "typeRoots": ["./node_modules/@types", "./types"]

# 5. Files not included in compilation
#    Check: "include" and "exclude" patterns in tsconfig.json
```

## Hard Rules

- **NEVER** use `as any` to silence type errors. Fix the types.
- **NEVER** add `@ts-ignore` or `@ts-expect-error` without a paired regression test that proves the suppression is necessary and temporary.
- **NEVER** relax `strict` mode or disable `strictNullChecks`, `noImplicitAny`, or other strict flags in tsconfig.json.
- **NEVER** add `eslint-disable` comments to bypass linting rules. Fix the code.
- **NEVER** use `// @ts-nocheck` to suppress all type checking in a file.
- **ALWAYS** use explicit type annotations for function parameters and return types in public API surfaces.
- **ALWAYS** run `npx tsc --noEmit` as the primary type check, not just the bundler build.
- **ALWAYS** verify that the TypeScript version and tsconfig settings are compatible.
- **ALWAYS** install `@types/*` packages as devDependencies, not dependencies.

## Stop Conditions

- The error requires downgrading TypeScript or relaxing strict mode to resolve a fundamental type incompatibility with a third-party library. Escalate with the library name and version.
- The error is in a `.d.ts` declaration file from a third-party package that the team does not control. Document the type definition bug and escalate.
- Two fix attempts have failed for the same type error. Provide the root cause analysis and both attempted approaches to the user.

## Output Format

```
[FIXED] <file>:<line> -- <TS error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

[FIXED] <file>:<line> -- <TS error code> <error summary>
  Root cause: <1-sentence explanation>
  Fix: <1-sentence description of change>

Build Status: PASS | tsc --noEmit | eslint | npm test
```
