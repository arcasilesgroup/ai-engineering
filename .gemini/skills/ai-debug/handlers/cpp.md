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
