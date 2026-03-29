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
